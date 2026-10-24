from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse, FileResponse
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from .models import SolicitudAnalisis
from apps.analisis.models import RegistroAnalisis
from apps.cultivos.models import Cultivo
from apps.ia_recomendaciones.models import ConfiguracionGlobal
from datetime import datetime
import json
import io

# =========================================================================
# VISTAS LABORATORISTA (PRESERVADAS Y MEJORADAS)
# =========================================================================

@login_required(login_url='login')
def solicitudes_pendientes(request):
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'LABORATORISTA':
        return redirect('home')
        
    solicitudes = SolicitudAnalisis.objects.filter(estado='PENDIENTE').order_by('-fecha_solicitud')
    return render(request, 'laboratorista/solicitudes_pendientes.html', {'solicitudes': solicitudes})

@login_required(login_url='login')
def solicitudes_asignadas(request):
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'LABORATORISTA':
        return redirect('home')
        
    solicitudes = SolicitudAnalisis.objects.filter(laboratorista_asignado=request.user, estado__in=['ASIGNADA', 'EN_PROCESO']).order_by('-fecha_solicitud')
    return render(request, 'laboratorista/mis_solicitudes.html', {'solicitudes': solicitudes})

@login_required(login_url='login')
def aceptar_solicitud(request, solicitud_id):
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'LABORATORISTA':
        return JsonResponse({'error': 'No autorizado'}, status=403)
        
    if request.method == 'POST':
        solicitud = get_object_or_404(SolicitudAnalisis, id=solicitud_id, estado='PENDIENTE')
        fecha_visita = request.POST.get('fecha_visita')
        
        if not fecha_visita:
            return JsonResponse({'error': 'La fecha de visita es obligatoria'}, status=400)
            
        solicitud.laboratorista_asignado = request.user
        solicitud.estado = 'ASIGNADA'
        solicitud.fecha_visita = fecha_visita
        solicitud.save()
        
        # Enviar correo al agricultor
        if solicitud.agricultor.email:
            try:
                context = {
                    'nombre_agricultor': solicitud.agricultor.get_full_name() or solicitud.agricultor.username,
                    'nombre_finca': solicitud.terreno.nombre,
                    'estado': 'ASIGNADA',
                    'nombre_laboratorista': request.user.get_full_name() or request.user.username,
                    'fecha_visita': fecha_visita,
                }
                html_message = render_to_string('emails/notificacion_solicitud.html', context)
                plain_message = strip_tags(html_message)
                
                send_mail(
                    subject='Tu solicitud ha sido ACEPTADA - TierSystem',
                    message=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[solicitud.agricultor.email],
                    html_message=html_message,
                    fail_silently=True,
                )
            except Exception as e:
                print(f"Error enviando correo: {e}")
        
        return JsonResponse({'mensaje': 'Solicitud aceptada y asignada correctamente.'})
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)

@login_required(login_url='login')
def rechazar_solicitud(request, solicitud_id):
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'LABORATORISTA':
        return JsonResponse({'error': 'No autorizado'}, status=403)
        
    if request.method == 'POST':
        solicitud = get_object_or_404(SolicitudAnalisis, id=solicitud_id, estado='PENDIENTE')
        solicitud.estado = 'RECHAZADA'
        solicitud.save()
        
        # Enviar correo al agricultor
        if solicitud.agricultor.email:
            try:
                context = {
                    'nombre_agricultor': solicitud.agricultor.get_full_name() or solicitud.agricultor.username,
                    'nombre_finca': solicitud.terreno.nombre,
                    'estado': 'RECHAZADA',
                    'nombre_laboratorista': request.user.get_full_name() or request.user.username,
                }
                html_message = render_to_string('emails/notificacion_solicitud.html', context)
                plain_message = strip_tags(html_message)
                
                send_mail(
                    subject='Actualización de tu solicitud - TierSystem',
                    message=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[solicitud.agricultor.email],
                    html_message=html_message,
                    fail_silently=True,
                )
            except Exception as e:
                print(f"Error enviando correo: {e}")
        
        return JsonResponse({'mensaje': 'Solicitud rechazada.'})
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)


# =========================================================================
# VISTAS DEL MÓDULO AGRICULTOR (COMPLETO)
# =========================================================================

@login_required(login_url='login')
def mis_solicitudes_agricultor(request):
    """
    US-0010: Consulta de solicitudes creadas por el agricultor con su estado actual.
    """
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'AGRICULTOR':
        return redirect('home')
        
    solicitudes = SolicitudAnalisis.objects.filter(agricultor=request.user).select_related('terreno', 'analisis_resultado').order_by('-fecha_solicitud')
    from apps.terrenos.models import Terreno
    terrenos = Terreno.objects.filter(agricultor=request.user)
    
    # Lista de cultivos para el selector
    cultivos = Cultivo.objects.filter(activo=True).order_by('nombre')
    
    context = {
        'solicitudes': solicitudes,
        'terrenos': terrenos,
        'cultivos': cultivos
    }
    return render(request, 'agricultor/solicitudes.html', context)

@login_required(login_url='login')
def crear_solicitud(request):
    """
    US-0009: Crear solicitud de análisis.
    Regla de negocio: Solo puede haber UNA solicitud activa a la vez (PENDIENTE, ASIGNADA, EN_PROCESO).
    """
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'AGRICULTOR':
        return JsonResponse({'error': 'No autorizado'}, status=403)
        
    if request.method == 'POST':
        # Validar si ya tiene una solicitud activa
        solicitud_activa = SolicitudAnalisis.objects.filter(
            agricultor=request.user, 
            estado__in=['PENDIENTE', 'ASIGNADA', 'EN_PROCESO']
        ).first()
        
        if solicitud_activa:
            return JsonResponse({
                'error': f'Ya tienes una solicitud activa (#{solicitud_activa.id} - {solicitud_activa.get_estado_display()}). Debes esperar a que finalice o cancelarla antes de crear otra.'
            }, status=400)

        terreno_id = request.POST.get('terreno_id')
        cultivo_deseado = request.POST.get('cultivo_deseado')
        modalidad = request.POST.get('modalidad')
        notas = request.POST.get('notas', '').strip()
        
        if not (terreno_id and cultivo_deseado and modalidad):
            return JsonResponse({'error': 'Todos los campos marcados con (*) son obligatorios.'}, status=400)
            
        from apps.terrenos.models import Terreno
        try:
            terreno = Terreno.objects.get(id=terreno_id, agricultor=request.user)
            solicitud = SolicitudAnalisis(
                agricultor=request.user,
                terreno=terreno,
                modalidad=modalidad,
                notas_agricultor=notas,
                estado='PENDIENTE'
            )
            solicitud.cultivo_deseado = cultivo_deseado
            solicitud.save()
            return JsonResponse({
                'mensaje': f'Solicitud #{solicitud.id} creada exitosamente. Tu solicitud está en estado Pendiente para atención del Laboratorista.'
            })
        except Terreno.DoesNotExist:
            return JsonResponse({'error': 'El terreno seleccionado no es válido o no te pertenece.'}, status=400)
            
    return JsonResponse({'error': 'Método no permitido'}, status=405)

@login_required(login_url='login')
def cancelar_solicitud(request, solicitud_id):
    """
    US-0010: El agricultor puede cancelar una solicitud ÚNICAMENTE si está en estado PENDIENTE.
    """
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'AGRICULTOR':
        return JsonResponse({'error': 'No autorizado'}, status=403)
        
    if request.method == 'POST':
        try:
            solicitud = SolicitudAnalisis.objects.get(id=solicitud_id, agricultor=request.user)
            if solicitud.estado == 'PENDIENTE':
                solicitud.estado = 'CANCELADA'
                solicitud.save()
                return JsonResponse({'mensaje': 'Solicitud cancelada correctamente.'})
            else:
                return JsonResponse({
                    'error': f'No es posible cancelar la solicitud porque ya está en estado {solicitud.get_estado_display()}. Solo se pueden cancelar solicitudes en estado Pendiente.'
                }, status=400)
        except SolicitudAnalisis.DoesNotExist:
            return JsonResponse({'error': 'Solicitud no encontrada.'}, status=404)
            
    return JsonResponse({'error': 'Método no permitido'}, status=405)

def _evaluar_parametros_agronomicos(analisis_obj, cultivo_nombre):
    """
    Función utilitaria que calcula el estado de los 7 parámetros,
    rangos ideales, barras porcentuales y recomendaciones específicas.
    """
    # Buscar cultivo en catálogo maestro
    if hasattr(cultivo_nombre, 'nombre'):
        cultivo_ideal = cultivo_nombre
    elif cultivo_nombre:
        cultivo_ideal = Cultivo.objects.filter(nombre__icontains=str(cultivo_nombre)).first()
    else:
        cultivo_ideal = Cultivo.objects.first()

    if not cultivo_ideal:
        cultivo_ideal = Cultivo.objects.first() # Fallback

    # Valores ideales convertidos estrictamente a float para evitar TypeError con Decimal
    c_ideal = {
        'ph_min': float(getattr(cultivo_ideal, 'ph_min', 5.8) or 5.8),
        'ph_max': float(getattr(cultivo_ideal, 'ph_max', 7.0) or 7.0),
        'n_min': float(getattr(cultivo_ideal, 'nitrogeno_min', 30.0) or 30.0),
        'n_max': float(getattr(cultivo_ideal, 'nitrogeno_max', 50.0) or 50.0),
        'p_min': float(getattr(cultivo_ideal, 'fosforo_min', 20.0) or 20.0),
        'p_max': float(getattr(cultivo_ideal, 'fosforo_max', 40.0) or 40.0),
        'k_min': float(getattr(cultivo_ideal, 'potasio_min', 100.0) or 100.0),
        'k_max': float(getattr(cultivo_ideal, 'potasio_max', 180.0) or 180.0),
        'hum_min': float(getattr(cultivo_ideal, 'humedad_min', 50.0) or 50.0),
        'hum_max': float(getattr(cultivo_ideal, 'humedad_max', 70.0) or 70.0),
        'ce_min': float(getattr(cultivo_ideal, 'conductividad_min', 0.5) or 0.5),
        'ce_max': float(getattr(cultivo_ideal, 'conductividad_max', 1.5) or 1.5),
        'temp_min': float(getattr(cultivo_ideal, 'temperatura_min', 18.0) or 18.0),
        'temp_max': float(getattr(cultivo_ideal, 'temperatura_max', 30.0) or 30.0),
    }

    medidos = {
        'ph': float(analisis_obj.ph or 0),
        'n': float(analisis_obj.nitrogeno or 0),
        'p': float(analisis_obj.fosforo or 0),
        'k': float(analisis_obj.potasio or 0),
        'hum': float(analisis_obj.humedad or 0),
        'ce': float(analisis_obj.conductividad or 0),
        'temp': float(analisis_obj.temperatura or 0),
    }

    params = []
    recomendaciones = []
    optimos_count = 0

    # Evaluador por parámetro
    def procesar(nombre, med, v_min, v_max, unidad, escala_max, consejo_def, consejo_exc, ganancia_def, ganancia_exc):
        nonlocal optimos_count
        med = float(med or 0)
        v_min = float(v_min or 0)
        v_max = float(v_max or 0)
        diff_range = v_max - v_min
        if med < v_min:
            estado = 'Deficiente'
            clase_estado = 'pill-amber'
            barra_clase = 'bar-amber'
            pct = max(10, min(100, int((med / max(v_max, 1.0)) * 80)))
            recomendaciones.append({
                'parametro': nombre,
                'tipo': 'Deficiente',
                'icono': 'ti-alert-triangle',
                'color': 'amber',
                'detalle': f"{nombre} ({med} {unidad} → ideal {v_min}–{v_max} {unidad})",
                'accion': consejo_def,
                'mejora': ganancia_def
            })
        elif med > v_max:
            estado = 'Excesivo'
            clase_estado = 'pill-red'
            barra_clase = 'bar-red'
            pct = 95
            recomendaciones.append({
                'parametro': nombre,
                'tipo': 'Excesivo',
                'icono': 'ti-alert-circle',
                'color': 'red',
                'detalle': f"{nombre} ({med} {unidad} → ideal {v_min}–{v_max} {unidad})",
                'accion': consejo_exc,
                'mejora': ganancia_exc
            })
        else:
            estado = 'Óptimo'
            clase_estado = 'pill-green'
            barra_clase = 'bar-green'
            pct = max(20, min(100, int(((med - v_min) / (diff_range if diff_range > 0 else 1.0)) * 40 + 50)))
            optimos_count += 1


        params.append({
            'nombre': nombre,
            'medido': med,
            'unidad': unidad,
            'ideal': f"{v_min} – {v_max}",
            'estado': estado,
            'clase_estado': clase_estado,
            'barra_clase': barra_clase,
            'barra_pct': pct
        })

    procesar('pH', medidos['ph'], c_ideal['ph_min'], c_ideal['ph_max'], '', 14.0,
             f"Aplicar enmienda con cal agrícola (carbonato de calcio) para elevar el pH a nivel neutro.",
             f"Aplicar materia orgánica compostada o sulfato de hierro para reducir la alcalinidad.",
             "+10%", "+8%")

    procesar('Nitrógeno (N)', medidos['n'], c_ideal['n_min'], c_ideal['n_max'], 'mg/kg', 100.0,
             f"Aplicar abono nitrogenado (urea o sulfato de amonio) para nutrir la masa vegetativa.",
             f"Suspender fertilizantes nitrogenados y aplicar lavados para evitar fitotoxicidad.",
             "+9%", "+7%")

    procesar('Fósforo (P)', medidos['p'], c_ideal['p_min'], c_ideal['p_max'], 'mg/kg', 80.0,
             f"Incorporar fertilizante fosfatado (DAP o roca fosfórica) para estimular el enraizamiento.",
             f"Reducir aportes fosfatados en las próximas abonadas.",
             "+8%", "+5%")

    procesar('Potasio (K)', medidos['k'], c_ideal['k_min'], c_ideal['k_max'], 'mg/kg', 300.0,
             f"Aplicar cloruro o sulfato de potasio para mejorar el llenado y resistencia a sequía.",
             f"Disminuir fertilizantes potásicos en la solución del suelo.",
             "+7%", "+5%")

    procesar('Humedad', medidos['hum'], c_ideal['hum_min'], c_ideal['hum_max'], '%', 100.0,
             f"Incrementar la frecuencia de riego o aplicar acolchado vegetal (mulching) para retener humedad.",
             f"Reducir el riego y mejorar zanjas de drenaje del suelo para evitar encharcamientos.",
             "+6%", "+6%")

    procesar('Conductividad (CE)', medidos['ce'], c_ideal['ce_min'], c_ideal['ce_max'], 'dS/m', 5.0,
             f"Suelo con muy baja salinidad mineral; asegurar un plan de fertilización equilibrado.",
             f"Exceso de sales en el suelo; realizar lavados con agua de buena calidad y drenar.",
             "+5%", "+8%")

    procesar('Temperatura', medidos['temp'], c_ideal['temp_min'], c_ideal['temp_max'], '°C', 50.0,
             f"Temperatura edáfica fría; considerar coberturas plásticas o acolchado.",
             f"Temperatura edáfica elevada; implementar sombra parcial o coberturas vivas.",
             "+4%", "+4%")

    # Compatibilidad calculada
    compatibilidad_calculada = int((optimos_count / 7.0) * 60 + 35)
    
    # Extraer diagnóstico de IA si existe
    diag_ia = {}
    if analisis_obj.diagnostico_ia:
        try:
            diag_ia = json.loads(analisis_obj.diagnostico_ia)
        except Exception:
            diag_ia = {}

    if diag_ia.get('recomendaciones'):
        # Extraer porcentaje si la IA devolvió uno
        primera_rec = diag_ia['recomendaciones'][0]
        if 'compatibilidad' in primera_rec:
            try:
                compatibilidad_calculada = int(primera_rec['compatibilidad'])
            except Exception:
                pass

    nivel_compatibilidad = "ALTA" if compatibilidad_calculada >= 75 else ("MEDIA" if compatibilidad_calculada >= 50 else "BAJA")
    color_compatibilidad = "green" if compatibilidad_calculada >= 75 else ("amber" if compatibilidad_calculada >= 50 else "red")

    # Cultivos alternativos sugeridos
    cultivos_alternativos = [
        {"nombre": "Yuca", "variedad": "Manihot esculenta · Tubérculo", "compatibilidad": 91, "icono": "fa-carrot", "color": "green"},
        {"nombre": "Plátano", "variedad": "Musa paradisiaca · Frutal", "compatibilidad": 87, "icono": "fa-tree", "color": "green"},
        {"nombre": "Cacao", "variedad": "Theobroma cacao · Grano", "compatibilidad": 81, "icono": "fa-seedling", "color": "green"},
        {"nombre": "Tomate", "variedad": "Solanum lycopersicum · Hortaliza", "compatibilidad": 68, "icono": "fa-apple-whole", "color": "amber"}
    ]

    return {
        'parametros': params,
        'recomendaciones': recomendaciones,
        'compatibilidad': compatibilidad_calculada,
        'nivel_compatibilidad': nivel_compatibilidad,
        'color_compatibilidad': color_compatibilidad,
        'cultivos_alternativos': cultivos_alternativos,
        'consejo_general': diag_ia.get('consejo_general', '')
    }

@login_required(login_url='login')
def resultado_detalle_agricultor(request, solicitud_id):
    """
    US-0028, US-0029, US-0030: Pantalla de resultado completo de análisis del Agricultor.
    """
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'AGRICULTOR':
        return redirect('home')
        
    solicitud = get_object_or_404(SolicitudAnalisis, id=solicitud_id, agricultor=request.user)
    
    if not hasattr(solicitud, 'analisis_resultado'):
        return render(request, 'agricultor/resultado_detalle.html', {
            'solicitud': solicitud,
            'analisis_pendiente': True
        })
        
    analisis = solicitud.analisis_resultado
    evaluacion = _evaluar_parametros_agronomicos(analisis, solicitud.cultivo_deseado)
    
    context = {
        'solicitud': solicitud,
        'analisis': analisis,
        'evaluacion': evaluacion,
        'analisis_pendiente': False
    }
    return render(request, 'agricultor/resultado_detalle.html', context)

@login_required(login_url='login')
def historial_analisis_agricultor(request):
    """
    US-0011, US-0012: Historial completo de análisis con opción de selección para comparar y exportar.
    """
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'AGRICULTOR':
        return redirect('home')
        
    solicitudes = SolicitudAnalisis.objects.filter(
        agricultor=request.user,
        estado='COMPLETADA'
    ).select_related('analisis_resultado', 'terreno', 'laboratorista_asignado').order_by('-fecha_solicitud')
    
    # Evaluar cada análisis para mostrar badge de compatibilidad
    historial_lista = []
    for s in solicitudes:
        if hasattr(s, 'analisis_resultado'):
            eval_data = _evaluar_parametros_agronomicos(s.analisis_resultado, s.cultivo_deseado)
            historial_lista.append({
                'solicitud': s,
                'analisis': s.analisis_resultado,
                'compatibilidad': eval_data['compatibilidad'],
                'color': eval_data['color_compatibilidad'],
                'nivel': eval_data['nivel_compatibilidad']
            })

    omitidas = sum(1 for s in solicitudes if not hasattr(s, 'analisis_resultado'))

    return render(request, 'agricultor/historial.html', {
        'historial_lista': historial_lista,
        'solicitudes': solicitudes,
        'total_analisis': len(historial_lista),
        'solicitudes_sin_analisis': omitidas
    })

@login_required(login_url='login')
def comparar_analisis_agricultor(request):
    """
    US-0011 E4: Comparar dos análisis del historial del agricultor parámetro por parámetro.
    """
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'AGRICULTOR':
        return redirect('home')
        
    id1 = request.GET.get('id1')
    id2 = request.GET.get('id2')
    
    solicitudes_disponibles = SolicitudAnalisis.objects.filter(
        agricultor=request.user,
        estado='COMPLETADA'
    ).select_related('analisis_resultado', 'terreno').order_by('-fecha_solicitud')
    
    if len(solicitudes_disponibles) < 2:
        return render(request, 'agricultor/comparar.html', {
            'insuficientes': True,
            'solicitudes': solicitudes_disponibles
        })
        
    # Si no se pasan IDs, tomamos los 2 más recientes
    if not id1 or not id2:
        id1 = solicitudes_disponibles[0].id
        id2 = solicitudes_disponibles[1].id
        
    s1 = get_object_or_404(SolicitudAnalisis, id=id1, agricultor=request.user)
    s2 = get_object_or_404(SolicitudAnalisis, id=id2, agricultor=request.user)

    if not hasattr(s1, 'analisis_resultado') or not hasattr(s2, 'analisis_resultado'):
        return render(request, 'agricultor/comparar.html', {
            'insuficientes': True,
            'solicitudes': solicitudes_disponibles,
            'error_msg': 'Una de las solicitudes seleccionadas no tiene análisis completado.'
        })

    a1 = s1.analisis_resultado
    a2 = s2.analisis_resultado
    
    ev1 = _evaluar_parametros_agronomicos(a1, s1.cultivo_deseado)
    ev2 = _evaluar_parametros_agronomicos(a2, s2.cultivo_deseado)
    
    # Armar comparación fila por fila
    comparacion_filas = []
    for p1 in ev1['parametros']:
        # Buscar mismo parámetro en ev2
        p2 = next((item for item in ev2['parametros'] if item['nombre'] == p1['nombre']), None)
        if p2:
            diff = round(p1['medido'] - p2['medido'], 2)
            if diff > 0:
                tendencia = f"↑ +{diff} {p1['unidad']}"
                tendencia_clase = "text-green-600 dark:text-green-400"
            elif diff < 0:
                tendencia = f"↓ {diff} {p1['unidad']}"
                tendencia_clase = "text-amber-600 dark:text-amber-400"
            else:
                tendencia = f"= 0 {p1['unidad']}"
                tendencia_clase = "text-gray-500"
                
            comparacion_filas.append({
                'parametro': p1['nombre'],
                'unidad': p1['unidad'],
                'ideal': p1['ideal'],
                'val1': p1['medido'],
                'estado1': p1['estado'],
                'clase1': p1['clase_estado'],
                'val2': p2['medido'],
                'estado2': p2['estado'],
                'clase2': p2['clase_estado'],
                'tendencia': tendencia,
                'tendencia_clase': tendencia_clase
            })
            
    diff_compat = ev1['compatibilidad'] - ev2['compatibilidad']
    
    context = {
        'insuficientes': False,
        'solicitudes': solicitudes_disponibles,
        's1': s1,
        's2': s2,
        'ev1': ev1,
        'ev2': ev2,
        'diff_compat': diff_compat,
        'comparacion_filas': comparacion_filas
    }
    return render(request, 'agricultor/comparar.html', context)


# =========================================================================
# EXPORTACIONES PDF Y EXCEL (US-0012)
# =========================================================================

@login_required(login_url='login')
def exportar_historial_pdf(request):
    """
    US-0012: Exporta el historial de análisis del agricultor a PDF.
    """
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'AGRICULTOR':
        return redirect('home')
        
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    
    solicitudes = SolicitudAnalisis.objects.filter(
        agricultor=request.user,
        estado='COMPLETADA'
    ).select_related('analisis_resultado', 'terreno', 'laboratorista_asignado').order_by('-fecha_solicitud')
    
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    
    # Encabezado
    p.setFillColor(colors.HexColor('#0a4d3c'))
    p.rect(0, 730, 612, 62, fill=True, stroke=False)
    
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(40, 755, "TierSystem — Historial de Análisis de Suelo")
    p.setFont("Helvetica", 10)
    p.drawString(40, 740, f"Agricultor: {request.user.get_full_name() or request.user.username} | Fecha de emisión: {datetime.now().strftime('%d/%m/%Y')}")
    
    # Contenido
    y = 700
    p.setFillColor(colors.HexColor('#1f2937'))
    p.setFont("Helvetica-Bold", 11)
    p.drawString(40, y, "Listado de Muestreos y Diagnósticos Finalizados:")
    
    y -= 25
    p.setFont("Helvetica-Bold", 9)
    p.setFillColor(colors.HexColor('#4b5563'))
    p.drawString(40, y, "ID")
    p.drawString(70, y, "Fecha")
    p.drawString(140, y, "Finca / Terreno")
    p.drawString(250, y, "Cultivo")
    p.drawString(340, y, "pH")
    p.drawString(380, y, "N")
    p.drawString(410, y, "P")
    p.drawString(440, y, "K")
    p.drawString(480, y, "Compat.")
    
    p.setStrokeColor(colors.HexColor('#d1d5db'))
    p.setLineWidth(1)
    p.line(40, y - 5, 570, y - 5)
    
    y -= 20
    p.setFont("Helvetica", 9)
    p.setFillColor(colors.HexColor('#111827'))
    
    for s in solicitudes:
        if not hasattr(s, 'analisis_resultado'):
            continue
        if y < 60:
            p.showPage()
            y = 730
            p.setFont("Helvetica", 9)
            
        a = s.analisis_resultado
        ev = _evaluar_parametros_agronomicos(a, s.cultivo_deseado)
        
        p.drawString(40, y, f"#{s.id}")
        p.drawString(70, y, s.fecha_solicitud.strftime('%d/%m/%Y'))
        p.drawString(140, y, str(s.terreno.nombre)[:18])
        p.drawString(250, y, str(s.cultivo_deseado)[:14])
        p.drawString(340, y, str(a.ph))
        p.drawString(380, y, str(a.nitrogeno))
        p.drawString(410, y, str(a.fosforo))
        p.drawString(440, y, str(a.potasio))
        p.drawString(480, y, f"{ev['compatibilidad']}%")
        
        y -= 18
        
    p.showPage()
    p.save()
    buffer.seek(0)
    
    return FileResponse(buffer, as_attachment=True, filename=f"historial_suelos_{request.user.username}.pdf")

@login_required(login_url='login')
def exportar_historial_excel(request):
    """
    US-0012: Exporta el historial a archivo Excel (.xlsx).
    """
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'AGRICULTOR':
        return redirect('home')
        
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    
    solicitudes = SolicitudAnalisis.objects.filter(
        agricultor=request.user,
        estado='COMPLETADA'
    ).select_related('analisis_resultado', 'terreno', 'laboratorista_asignado').order_by('-fecha_solicitud')
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Historial TierSystem"
    
    # Título
    ws.merge_cells('A1:K1')
    ws['A1'] = f"TIERSYSTEM - REPORTE DE ANÁLISIS DE SUELO: {request.user.get_full_name() or request.user.username}"
    ws['A1'].font = Font(name='Arial', size=14, bold=True, color='FFFFFF')
    ws['A1'].fill = PatternFill(start_color='0A4D3C', end_color='0A4D3C', fill_type='solid')
    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
    
    # Encabezados
    headers = ["ID", "Fecha Muestreo", "Finca", "Área (ha)", "Cultivo", "pH", "Nitrógeno (mg/kg)", "Fósforo (mg/kg)", "Potasio (mg/kg)", "Humedad (%)", "Compatibilidad %"]
    ws.append([]) # Fila vacía
    ws.append(headers)
    
    for cell in ws[3]:
        cell.font = Font(bold=True, color='FFFFFF')
        cell.fill = PatternFill(start_color='10B981', end_color='10B981', fill_type='solid')
        cell.alignment = Alignment(horizontal='center')
        
    for s in solicitudes:
        if not hasattr(s, 'analisis_resultado'):
            continue
        a = s.analisis_resultado
        ev = _evaluar_parametros_agronomicos(a, s.cultivo_deseado)
        ws.append([
            f"#{s.id}",
            s.fecha_solicitud.strftime('%d/%m/%Y'),
            s.terreno.nombre,
            float(s.terreno.hectareas),
            s.cultivo_deseado,
            float(a.ph),
            float(a.nitrogeno),
            float(a.fosforo),
            float(a.potasio),
            float(a.humedad),
            f"{ev['compatibilidad']}%"
        ])
        
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    response = HttpResponse(buffer.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="historial_analisis_{request.user.username}.xlsx"'
    return response

@login_required(login_url='login')
def exportar_analisis_individual_pdf(request, solicitud_id):
    """
    US-0012: Exporta la ficha técnica y certificado de un análisis individual.
    """
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'AGRICULTOR':
        return redirect('home')
        
    solicitud = get_object_or_404(SolicitudAnalisis, id=solicitud_id, agricultor=request.user)
    if not hasattr(solicitud, 'analisis_resultado'):
        return redirect('solicitudes_agricultor:mis_solicitudes')
        
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    
    a = solicitud.analisis_resultado
    ev = _evaluar_parametros_agronomicos(a, solicitud.cultivo_deseado)
    
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    
    # Encabezado
    p.setFillColor(colors.HexColor('#0a4d3c'))
    p.rect(0, 720, 612, 72, fill=True, stroke=False)
    
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(40, 755, "TierSystem — Ficha Técnica de Análisis de Suelo")
    p.setFont("Helvetica", 9)
    p.drawString(40, 735, f"SENA La Angostura · Centro Agroindustrial del Huila")
    
    # Resumen
    p.setFillColor(colors.HexColor('#111827'))
    p.setFont("Helvetica-Bold", 12)
    p.drawString(40, 690, f"Solicitud #{solicitud.id} — Cultivo Objetivo: {solicitud.cultivo_deseado}")
    
    p.setFont("Helvetica", 10)
    p.drawString(40, 670, f"Agricultor: {request.user.get_full_name() or request.user.username} | Finca: {solicitud.terreno.nombre} ({solicitud.terreno.hectareas} ha)")
    p.drawString(40, 655, f"Fecha: {solicitud.fecha_solicitud.strftime('%d/%m/%Y')} | Compatibilidad Calculada: {ev['compatibilidad']}% ({ev['nivel_compatibilidad']})")
    
    # Tabla Parámetros
    y = 620
    p.setFont("Helvetica-Bold", 10)
    p.drawString(40, y, "Parámetro")
    p.drawString(160, y, "Valor Medido")
    p.drawString(260, y, "Rango Ideal")
    p.drawString(380, y, "Estado Agronómico")
    
    p.setStrokeColor(colors.HexColor('#9ca3af'))
    p.line(40, y-5, 550, y-5)
    
    y -= 20
    p.setFont("Helvetica", 9)
    for pr in ev['parametros']:
        p.drawString(40, y, pr['nombre'])
        p.drawString(160, y, f"{pr['medido']} {pr['unidad']}")
        p.drawString(260, y, f"{pr['ideal']} {pr['unidad']}")
        p.drawString(380, y, pr['estado'])
        y -= 16
        
    # Recomendaciones
    y -= 15
    p.setFont("Helvetica-Bold", 11)
    p.drawString(40, y, "Recomendaciones Agronómicas de Manejo:")
    y -= 18
    p.setFont("Helvetica", 9)
    for rec in ev['recomendaciones']:
        p.drawString(40, y, f"• {rec['parametro']} ({rec['tipo']}): {rec['accion']} [Mejora: {rec['mejora']}]")
        y -= 16
        
    # Pie de página
    p.setFont("Helvetica-Oblique", 8)
    p.setFillColor(colors.HexColor('#6b7280'))
    p.drawString(40, 40, "Este informe fue generado por el sistema TierSystem basado en sensores de suelo calibrados.")
    
    p.showPage()
    p.save()
    buffer.seek(0)
    
    return FileResponse(buffer, as_attachment=True, filename=f"reporte_analisis_{solicitud.id}.pdf")

@login_required(login_url='login')
def exportar_analisis_individual_excel(request, solicitud_id):
    """
    US-0012: Exporta la ficha técnica de un análisis individual en formato Excel (.xlsx).
    """
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'AGRICULTOR':
        return redirect('home')

    solicitud = get_object_or_404(SolicitudAnalisis, id=solicitud_id, agricultor=request.user)
    if not hasattr(solicitud, 'analisis_resultado'):
        return redirect('solicitudes_agricultor:mis_solicitudes')

    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment

    a = solicitud.analisis_resultado
    ev = _evaluar_parametros_agronomicos(a, solicitud.cultivo_deseado)

    wb = Workbook()

    # ─── Hoja 1: Parámetros ───────────────────────────────────────────────────
    ws_params = wb.active
    ws_params.title = "Parametros"

    # Título principal
    ws_params.merge_cells('A1:I1')
    ws_params['A1'] = "TIERSYSTEM - FICHA TECNICA ANALISIS DE SUELO"
    ws_params['A1'].font = Font(name='Arial', size=14, bold=True, color='FFFFFF')
    ws_params['A1'].fill = PatternFill(start_color='0A4D3C', end_color='0A4D3C', fill_type='solid')
    ws_params['A1'].alignment = Alignment(horizontal='center', vertical='center')

    # Metadatos
    lab_nombre = str(solicitud.laboratorista_asignado) if solicitud.laboratorista_asignado else 'N/A'
    metadata = [
        ("ID Solicitud", f"#{solicitud.id}"),
        ("Agricultor", solicitud.agricultor.get_full_name() or solicitud.agricultor.username),
        ("Finca", solicitud.terreno.nombre),
        ("Hectáreas", f"{solicitud.terreno.hectareas} ha"),
        ("Cultivo Objetivo", solicitud.cultivo_deseado),
        ("Fecha Muestreo", solicitud.fecha_solicitud.strftime('%d/%m/%Y')),
        ("Laboratorista", lab_nombre),
        ("Compatibilidad %", f"{ev['compatibilidad']}% ({ev['nivel_compatibilidad']})"),
    ]
    for label, value in metadata:
        ws_params.append([label, value])

    ws_params.append([])  # separador

    # Encabezados de tabla de parámetros
    param_headers = ["Parametro", "Valor Medido", "Unidad", "Rango Ideal", "Estado Agronomico"]
    ws_params.append(param_headers)
    header_row = ws_params.max_row
    for cell in ws_params[header_row]:
        cell.font = Font(bold=True, color='FFFFFF')
        cell.fill = PatternFill(start_color='10B981', end_color='10B981', fill_type='solid')
        cell.alignment = Alignment(horizontal='center')

    # Filas de parámetros
    for pr in ev['parametros']:
        ws_params.append([
            pr['nombre'],
            pr['medido'],
            pr['unidad'],
            pr['ideal'],
            pr['estado'],
        ])

    # ─── Hoja 2: Recomendaciones ──────────────────────────────────────────────
    ws_recs = wb.create_sheet(title="Recomendaciones")

    rec_headers = ["Parametro", "Tipo", "Detalle", "Accion Sugerida", "Mejora Estimada"]
    ws_recs.append(rec_headers)
    for cell in ws_recs[1]:
        cell.font = Font(bold=True, color='FFFFFF')
        cell.fill = PatternFill(start_color='10B981', end_color='10B981', fill_type='solid')
        cell.alignment = Alignment(horizontal='center')

    if ev['recomendaciones']:
        for rec in ev['recomendaciones']:
            ws_recs.append([
                rec['parametro'],
                rec['tipo'],
                rec['detalle'],
                rec['accion'],
                rec['mejora'],
            ])
    else:
        ws_recs.append(["Todos los parametros en rango optimo", "", "", "", ""])

    # ─── Respuesta HTTP ───────────────────────────────────────────────────────
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    response = HttpResponse(
        buffer.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="reporte_analisis_{solicitud.id}.xlsx"'
    return response
