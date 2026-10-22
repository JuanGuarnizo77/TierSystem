from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta, date
from io import StringIO
import unicodedata

from django.core.management import call_command

from .models import PrecioMercado, Comprador, ProductoMercado
from apps.sipsa.models import CultivoSipsa, PrecioSemanal, PrediccionPrecio




def _normalizar_tendencia(valor):
    mapping = {
        'sube': 'Alza',
        'alza': 'Alza',
        'baja': 'Baja',
        'estable': 'Estable',
    }
    return mapping.get(str(valor or '').strip().lower(), valor or 'Estable')


def _build_datos_cultivo_from_db(pm):
    """Convierte un objeto PrecioMercado en el formato de dict usado por las vistas."""
    return {
        "precio_promedio": float(pm.precio_promedio),
        "precio_local": float(pm.precio_local) if pm.precio_local is not None else float(pm.precio_promedio),
        "unidad": pm.unidad,
        "tendencia": _normalizar_tendencia(pm.tendencia),
        "variacion": f"{pm.variacion_porcentaje:+.0f}%",
        "fuente": pm.fuente,
        # El modelo PrecioMercado no almacena historial mensual; se genera desde PrecioSemanal en las vistas
        "historial": [{"mes": "Ref.", "precio": float(pm.precio_promedio)}],
        "compradores": [],  # se rellena abajo con compradores de BD
    }


def _get_compradores_for_cultivo(cultivo_key):
    """Devuelve la lista de compradores (dict) para un cultivo dado, preferiendo BD."""
    qs = Comprador.objects.filter(activo=True, cultivos_interes__icontains=cultivo_key)
    if qs.exists():
        compradores = []
        for c in qs:
            compradores.append({
                "nombre": c.nombre,
                "tipo": c.tipo,
                "municipio": c.municipio,
                "contacto": c.contacto,
                "precio": c.precio_referencia or "",
                "email": c.email,
                "whatsapp": c.whatsapp,
                "sitio_web": c.sitio_web,
            })
        return compradores
    return []


def _normalizar_texto(s):
    """Quita tildes y convierte a minúsculas para comparación flexible."""
    return ''.join(
        c for c in unicodedata.normalize('NFD', s)
        if unicodedata.category(c) != 'Mn'
    ).lower()


def _resolver_cultivo_key(nombre):
    solicitado_raw = (nombre or '').strip()
    if not solicitado_raw:
        # Use the first available PrecioMercado or a safe default
        pm_first = PrecioMercado.objects.order_by('cultivo_nombre').first()
        return pm_first.cultivo_nombre if pm_first else ''
    solicitado = _normalizar_texto(solicitado_raw)
    # Try exact match first
    pm_exact = PrecioMercado.objects.filter(cultivo_nombre__iexact=solicitado_raw).first()
    if pm_exact:
        return pm_exact.cultivo_nombre
    # Try normalised substring match across DB entries
    for pm in PrecioMercado.objects.order_by('cultivo_nombre'):
        k_norm = _normalizar_texto(pm.cultivo_nombre)
        if k_norm in solicitado or solicitado in k_norm:
            return pm.cultivo_nombre
    # Fallback: return the raw name as supplied
    return solicitado_raw


def _datos_cultivo(cultivo_key):
    if PrecioMercado.objects.exists():
        pm = PrecioMercado.objects.filter(cultivo_nombre=cultivo_key).first()
        if pm is None:
            pm = PrecioMercado.objects.filter(cultivo_nombre__icontains=cultivo_key).first()
        if pm is not None:
            return _build_datos_cultivo_from_db(pm)
    # No data available in DB
    return {
        "precio_promedio": 0,
        "precio_local": 0,
        "unidad": "kg",
        "tendencia": "Estable",
        "variacion": "0%",
        "fuente": "Sin datos",
        "historial": [],
        "compradores": [],
    }


def _listado_precios_tabla():
    precios = []
    if PrecioMercado.objects.exists():
        for pm in PrecioMercado.objects.order_by('cultivo_nombre'):
            precios.append({
                "cultivo": pm.cultivo_nombre,
                "precio": f"${float(pm.precio_promedio):,.0f} / {pm.unidad}",
                "tendencia": _normalizar_tendencia(pm.tendencia),
                "mercado": pm.region or "Huila",
            })
    return precios


TENDENCIA_MAP = {
    'SUBE': 'Alza', 'BAJA': 'Baja', 'ESTABLE': 'Estable',
    'Alza': 'Alza', 'Baja': 'Baja', 'Estable': 'Estable',
}


def _construir_historial_sipsa(cultivo):
    """Builds price history from PrecioSemanal records using readable date ranges."""
    import datetime as _dt
    precios = PrecioSemanal.objects.filter(cultivo=cultivo).order_by('fecha_semana')[:8]
    return [
        {
            'mes': (
                f"{p.fecha_semana.strftime('%d %b').lstrip('0')} – "
                f"{(p.fecha_semana + _dt.timedelta(days=6)).strftime('%d %b').lstrip('0')}"
            ),
            'precio': float(p.precio_kg),
        }
        for p in precios
    ]


def _obtener_compradores_sipsa(cultivo):
    """Returns buyers for a CultivoSipsa object, preferring DB over static dict."""
    qs = Comprador.objects.filter(activo=True, cultivos_interes__icontains=cultivo.nombre)
    if qs.exists():
        return [
            {
                'nombre': c.nombre,
                'tipo': c.tipo,
                'municipio': c.municipio,
                'contacto': c.contacto,
                'precio': c.precio_referencia or '',
                'email': c.email,
                'whatsapp': c.whatsapp,
                'sitio_web': c.sitio_web,
            }
            for c in qs
        ]
    return []


@login_required(login_url='login')
def precios_sipsa(request):
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'AGRICULTOR':
        return redirect('home')

    cultivo_key = _resolver_cultivo_key(request.GET.get('cultivo', 'Maíz Amarillo'))
    datos_cultivo = dict(_datos_cultivo(cultivo_key))
    datos_cultivo["compradores"] = _get_compradores_for_cultivo(cultivo_key)
    datos_cultivo["tendencia"] = _normalizar_tendencia(datos_cultivo.get("tendencia"))

    # cultivos_disponibles from CultivoSipsa catalogue — not passed to template
    hace_24h = timezone.now() - timedelta(hours=24)
    hace_72h = timezone.now() - timedelta(hours=72)

    pm_mas_reciente = PrecioMercado.objects.order_by('-ultima_actualizacion').first()
    ultima_actualizacion_global = None

    if pm_mas_reciente and pm_mas_reciente.ultima_actualizacion:
        ts = pm_mas_reciente.ultima_actualizacion
        dias_desde = (timezone.now() - ts).days
        ultima_actualizacion_global = timezone.localtime(ts).strftime("%d/%m/%Y %H:%M")

        if ts >= hace_24h:
            estado_conexion = 'online'
            mensaje_conexion = f"Precios actualizados al {ultima_actualizacion_global} desde SIPSA/DANE."
        elif ts >= hace_72h:
            estado_conexion = 'reciente'
            mensaje_conexion = f"Precios con {dias_desde} día(s) de antigüedad. Se recomienda actualizar."
        else:
            estado_conexion = 'desactualizado'
            mensaje_conexion = f"Precios con más de 72h de antigüedad ({dias_desde} días). Mostrando datos de referencia."
    else:
        estado_conexion = 'desactualizado'
        mensaje_conexion = "Sin datos recientes. Mostrando precios de referencia regional almacenados."

    # --- Build precios_tabla from CultivoSipsa catalogue (unified with Reportes SIPSA/DANE) ---
    precios_tabla = []
    cultivos_sipsa = CultivoSipsa.objects.filter(activo=True).order_by('nombre')

    for cultivo in cultivos_sipsa:
        # Prefer live PrecioSemanal data
        precio_semanal = PrecioSemanal.objects.filter(cultivo=cultivo).order_by('-fecha_semana').first()
        # Also check PrecioMercado via FK
        pm_fk = PrecioMercado.objects.filter(cultivo=cultivo).order_by('-ultima_actualizacion').first()
        # Fall back to PrecioMercado by name if FK not populated yet
        if pm_fk is None:
            pm_fk = PrecioMercado.objects.filter(cultivo_nombre=cultivo.nombre).first()
        # Static fallback dict
        datos_est = {}

        # Determine best price source
        if precio_semanal:
            precio_promedio = float(precio_semanal.precio_kg)
            precio_local = float(precio_semanal.precio_local) if precio_semanal.precio_local else round(precio_promedio * 0.97, 0)
            fuente = precio_semanal.fuente or 'SIPSA / DANE'
            ultima_act = timezone.localtime(precio_semanal.fecha_registro).strftime('%d/%m/%Y') if precio_semanal.fecha_registro else '—'
            dias_desde = (timezone.now().date() - precio_semanal.fecha_semana).days
        elif pm_fk:
            precio_promedio = float(pm_fk.precio_promedio)
            precio_local = float(pm_fk.precio_local) if pm_fk.precio_local else precio_promedio
            fuente = pm_fk.fuente or 'SIPSA / DANE'
            ultima_act = timezone.localtime(pm_fk.ultima_actualizacion).strftime('%d/%m/%Y') if pm_fk.ultima_actualizacion else '—'
            dias_desde = (timezone.now() - pm_fk.ultima_actualizacion).days if pm_fk.ultima_actualizacion else None
        elif datos_est:
            precio_promedio = datos_est.get('precio_promedio', 0)
            precio_local = datos_est.get('precio_local', precio_promedio)
            fuente = datos_est.get('fuente', 'SIPSA / DANE')
            ultima_act = '—'
            dias_desde = None
        else:
            # No data source available — skip to avoid rendering a misleading $0 / kg row
            continue

        # Get real prediction from PrediccionPrecio
        pred = None
        try:
            pred = cultivo.prediccion  # OneToOne reverse accessor
        except Exception:
            pass

        if pred:
            tendencia = TENDENCIA_MAP.get(pred.tendencia_predicha, pred.tendencia_predicha)
            variacion_pct = round(pred.variacion_estimada_pct, 1)
            confianza = round(pred.confianza_pct, 0)
            detalle_pred = (
                f"Confianza: {confianza:.0f}% | Precio estimado: ${float(pred.precio_estimado):,.0f} / {cultivo.unidad}"
                if pred.precio_estimado
                else f"Confianza: {confianza:.0f}%"
            )
        elif pm_fk:
            tendencia = _normalizar_tendencia(pm_fk.tendencia)
            variacion_pct = pm_fk.variacion_porcentaje
            confianza = None
            detalle_pred = ''
        elif datos_est:
            tendencia = _normalizar_tendencia(datos_est.get('tendencia', 'Estable'))
            raw_var = str(datos_est.get('variacion', '0%')).replace('%', '').replace('+', '')
            try:
                variacion_pct = float(raw_var)
            except ValueError:
                variacion_pct = 0.0
            confianza = None
            detalle_pred = ''
        else:
            tendencia = 'Estable'
            variacion_pct = 0.0
            confianza = None
            detalle_pred = ''

        # Build price history preferring PrecioSemanal
        historial = _construir_historial_sipsa(cultivo)
        if not historial:
            historial = datos_est.get('historial', [{'mes': 'Ref.', 'precio': precio_promedio}])

        precios_tabla.append({
            'cultivo': cultivo.nombre,
            'precio_promedio': precio_promedio,
            'precio_local': precio_local,
            'unidad': cultivo.unidad or 'kg',
            'tendencia': tendencia,
            'variacion_porcentaje': variacion_pct,
            'confianza': confianza,
            'detalle_prediccion': detalle_pred,
            'fuente': fuente,
            'ultima_actualizacion': ultima_act,
            'dias_desde_actualizacion': dias_desde,
            'compradores': _obtener_compradores_sipsa(cultivo),
            'historial': historial,
        })

    precios_historial = [item["precio"] for item in datos_cultivo.get("historial", [])]
    max_precio = max(precios_historial) if precios_historial else 1

    historial_con_porcentajes = []
    for h in datos_cultivo.get("historial", []):
        pct = int((h["precio"] / max_precio) * 100) if max_precio else 30
        historial_con_porcentajes.append({
            "mes": h["mes"],
            "precio": h["precio"],
            "pct": max(30, pct)
        })

    precio_reg = float(datos_cultivo.get("precio_promedio") or 0)
    precio_loc = float(datos_cultivo.get("precio_local") or 0)
    max_comp = max(precio_reg, precio_loc, 1)
    pct_loc = int((precio_loc / max_comp) * 90)
    pct_reg = int((precio_reg / max_comp) * 90)

    context = {
        'cultivo_actual': cultivo_key,
        'datos': datos_cultivo,
        'precios': _listado_precios_tabla(),
        'precios_tabla': precios_tabla,

        'historial_grafica': historial_con_porcentajes,
        'pct_local': pct_loc,
        'pct_regional': pct_reg,
        'max_precio_historico': max_precio,
        'estado_conexion': estado_conexion,
        'mensaje_conexion': mensaje_conexion,
        'ultima_actualizacion_global': ultima_actualizacion_global,
        'fecha_hoy': datetime.now().strftime("%d/%m/%Y")
    }
    return render(request, 'agricultor/precios_sipsa.html', context)


@login_required(login_url='login')
def actualizar_precios_view(request):
    """Dispara el comando actualizar_precios vía POST y devuelve JSON con el resultado."""
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'AGRICULTOR':
        return JsonResponse({'error': 'No autorizado'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    out = StringIO()
    try:
        call_command('actualizar_precios', stdout=out)
        return JsonResponse({'status': 'ok', 'output': out.getvalue()})
    except Exception as exc:
        return JsonResponse({'status': 'error', 'message': str(exc)}, status=500)


@login_required(login_url='login')
def api_datos_cultivo_mercado(request, cultivo_nombre):
    """
    Retorna JSON con los precios, tendencia, gráfica y compradores para actualización AJAX.
    """
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'AGRICULTOR':
        return JsonResponse({'error': 'No autorizado'}, status=403)

    cultivo_key = _resolver_cultivo_key(cultivo_nombre)
    datos = dict(_datos_cultivo(cultivo_key))
    datos["tendencia"] = _normalizar_tendencia(datos.get("tendencia"))
    compradores = _get_compradores_for_cultivo(cultivo_key)

    precios_historial = [item["precio"] for item in datos["historial"]]
    max_precio = max(precios_historial) if precios_historial else 1

    historial = []
    for h in datos["historial"]:
        historial.append({
            "mes": h["mes"],
            "precio": h["precio"],
            "pct": max(30, int((h["precio"] / max_precio) * 100))
        })

    return JsonResponse({
        'estado': 'ok',
        'cultivo': cultivo_key,
        'precio_promedio': datos["precio_promedio"],
        'precio_local': datos["precio_local"],
        'unidad': datos["unidad"],
        'tendencia': datos["tendencia"],
        'variacion': datos["variacion"],
        'fuente': datos["fuente"],
        'historial': historial,
        'max_precio': max_precio,
        'compradores': compradores,
    })


@login_required(login_url='login')
def listado_productos(request):
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'AGRICULTOR':
        return redirect('home')

    productos = ProductoMercado.objects.filter(activo=True).select_related('vendedor').order_by('-fecha_publicacion')
    return render(request, 'agricultor/mercado.html', {'productos': productos})


@login_required(login_url='login')
def mi_tienda(request):
    """
    Vista de 'Mi Tienda' del agricultor en el mercado.
    Muestra los productos que el agricultor ha publicado para la venta.
    """
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'AGRICULTOR':
        return redirect('home')

    productos = ProductoMercado.objects.filter(vendedor=request.user, activo=True).order_by('-fecha_publicacion')

    context = {
        'productos': productos,
    }
    return render(request, 'agricultor/mi_tienda.html', context)


@login_required(login_url='login')
def agregar_producto(request):
    """Agrega un nuevo producto a la tienda del agricultor."""
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'AGRICULTOR':
        return JsonResponse({'error': 'No autorizado'}, status=403)

    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        precio = request.POST.get('precio', '').strip()
        cantidad = request.POST.get('cantidad', '').strip()
        unidad = request.POST.get('unidad', 'kg').strip()

        if not nombre or not precio or not cantidad:
            return JsonResponse({'error': 'Todos los campos son obligatorios.'}, status=400)

        try:
            ProductoMercado.objects.create(
                vendedor=request.user,
                nombre=nombre,
                precio=precio,
                cantidad_disponible=int(cantidad),
                unidad_medida=unidad,
            )
            return JsonResponse({'mensaje': f'Producto "{nombre}" publicado exitosamente.'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Método no permitido'}, status=405)


@login_required(login_url='login')
def eliminar_producto(request, producto_id):
    """Elimina (desactiva) un producto de la tienda del agricultor."""
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'AGRICULTOR':
        return JsonResponse({'error': 'No autorizado'}, status=403)

    if request.method == 'POST':
        from django.shortcuts import get_object_or_404
        producto = get_object_or_404(ProductoMercado, id=producto_id, vendedor=request.user)
        producto.activo = False
        producto.save()
        return JsonResponse({'mensaje': f'Producto "{producto.nombre}" eliminado del mercado.'})

    return JsonResponse({'error': 'Método no permitido'}, status=405)
