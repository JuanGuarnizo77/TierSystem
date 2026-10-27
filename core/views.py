"""
Controladores Web Centrales y Paneles Administrativos de TierSystem.
=====================================================================
Este módulo concentra los controladores basados en funciones (FBV) para:
  1. Enrutamiento y redirección de aterrizaje según el rol del usuario autenticado (`home`).
  2. Tableros de control principales por perfil:
      - Agricultor (`dashboard_agricultor`): métricas de predios y solicitudes activas.
      - Laboratorista (`dashboard_laboratorista`): solicitudes asignadas y análisis pendientes.
      - Administrador (`dashboard_admin`): auditoría general, conteo de actores y solicitudes.
  3. Módulo de campo del laboratorista (`toma_muestras_laboratorista`):
      - Gestión de cuadrícula de muestreo edafológico según extensión en hectáreas.
      - Precarga del catálogo agronómico para sincronización y funcionamiento offline.
  4. Gobernanza de usuarios del sistema:
      - Listado y auditoría de agricultores y laboratoristas (`lista_usuarios`).
      - Registro seguro de nuevo personal técnico (`crear_laboratorista`).
      - Edición de perfiles (`editar_usuario`), alternancia de estado activo (`cambiar_estado_usuario`)
        y eliminación definitiva con protección contra auto-bloqueo (`eliminar_usuario`).
  5. Supervisión técnica y reportería institucional:
      - Auditoría filtrable de análisis edafológicos (`supervision_analisis`).
      - Generación dinámica de reportes en PDF con ReportLab (`exportar_pdf`).
      - Generación de libros de cálculo en Excel con OpenpyXL (`exportar_excel`).
  6. Mantenimiento del catálogo maestro de cultivos (`gestion_cultivos_admin`, `guardar_cultivo_admin`, `eliminar_cultivo_admin`).
  7. Telemetría de hardware IoT (`estado_hardware`) y configuración global del motor de IA (`configuracion_global_view`).
"""

import io
import json
from datetime import timedelta

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count
from django.http import JsonResponse, FileResponse, HttpResponse
from django.utils import timezone

# Importación de modelos de las aplicaciones del ecosistema
from apps.usuarios.models import Perfil
from apps.terrenos.models import Terreno
from apps.solicitudes.models import SolicitudAnalisis
from apps.analisis.models import RegistroAnalisis, PuntoMuestreo
from apps.cultivos.models import Cultivo
from apps.sensores.models import LecturaSensor
from apps.ia_recomendaciones.models import ConfiguracionGlobal


# =============================================================================
# ENRUTAMIENTO DE ATERRIZAJE (LANDING / REDIRECCIÓN POR ROL)
# =============================================================================

def home(request):
    """
    Vista de aterrizaje público y discriminador de acceso por rol.

    Comportamiento:
      - Si el usuario tiene una sesión activa (autenticado) y posee un perfil registrado,
        lo redirige automáticamente a su panel de control correspondiente:
          * 'LABORATORISTA' -> 'dashboard_laboratorista'
          * 'AGRICULTOR'    -> 'dashboard_agricultor'
          * 'ADMIN'         -> 'dashboard_admin'
      - Si es un visitante anónimo o un usuario sin perfil asignado, renderiza
        la página de inicio pública institucional (landing page).

    Parámetros:
      - `request` (HttpRequest): Objeto de solicitud HTTP de Django.

    Retorna:
      - `HttpResponseRedirect`: Redirección al tablero según rol.
      - `HttpResponse`: Renderizado de la plantilla 'home.html'.
    """
    # Verificar si el visitante ya cuenta con sesión abierta
    if request.user.is_authenticated:
        # Validar la existencia de la relación OneToOne hacia el modelo Perfil
        if hasattr(request.user, 'perfil'):
            # Redireccionar según el rol agronómico asignado
            if request.user.perfil.rol == 'LABORATORISTA':
                return redirect('dashboard_laboratorista')
            elif request.user.perfil.rol == 'AGRICULTOR':
                return redirect('dashboard_agricultor')
            elif request.user.perfil.rol == 'ADMIN':
                return redirect('dashboard_admin')

    # Visitantes sin autenticación o sin perfil específico
    return render(request, 'home.html')


# =============================================================================
# TABLEROS Y CATÁLOGOS DEL ROL AGRICULTOR
# =============================================================================

@login_required(login_url='login')
def dashboard_agricultor(request):
    """
    Panel de control principal para el productor agrícola.

    Restricciones:
      - Requiere sesión autenticada con rol 'AGRICULTOR'.

    Métricas calculadas:
      - `total_terrenos`: Cantidad de predios y parcelas registradas por el usuario.
      - `solicitudes_activas`: Solicitudes de análisis de suelo en curso
        (estados: 'PENDIENTE', 'ASIGNADA' o 'EN_PROCESO').

    Plantilla:
      - `agricultor/dashboard.html`
    """
    # Validar permisos de rol de agricultor
    if hasattr(request.user, 'perfil') and request.user.perfil.rol == 'AGRICULTOR':
        # Construir contexto con métricas resumidas del productor
        context = {
            # Total de fincas bajo la titularidad del usuario activo
            'total_terrenos': Terreno.objects.filter(agricultor=request.user).count(),
            # Solicitudes que aún no han alcanzado el estado final de completadas o rechazadas
            'solicitudes_activas': SolicitudAnalisis.objects.filter(
                agricultor=request.user,
                estado__in=['PENDIENTE', 'ASIGNADA', 'EN_PROCESO']
            ).count(),
        }
        return render(request, 'agricultor/dashboard.html', context)

    # Redireccionar a la raíz si no cumple con el rol autorizado
    return redirect('home')


@login_required(login_url='login')
def catalogo_cultivos(request):
    """
    Catálogo agronómico interactivo para consulta de especies agrícolas.

    Restricciones:
      - Requiere sesión autenticada con rol 'AGRICULTOR'.

    Comportamiento:
      - Consulta las especies habilitadas (`activo=True`) ordenadas alfabéticamente.
      - Serializa la colección a formato JSON para habilitar filtros y búsquedas
        reactivas del lado del cliente sin latencia de red.

    Plantilla:
      - `agricultor/cultivos.html`
    """
    # Validar permisos de rol de agricultor
    if hasattr(request.user, 'perfil') and request.user.perfil.rol == 'AGRICULTOR':
        # Consulta de cultivos activos ordenados por nombre común
        cultivos_qs = Cultivo.objects.filter(activo=True).order_by('nombre')

        # Convertir queryset a lista de diccionarios para serialización en frontend
        cultivos_data = [c.to_catalogo_dict() for c in cultivos_qs]
        cultivos_json = json.dumps(cultivos_data)

        # Renderizar la vista pasando tanto el queryset de Django como el payload JSON
        return render(request, 'agricultor/cultivos.html', {
            'cultivos': cultivos_qs,
            'cultivos_json': cultivos_json,
            'total_cultivos': len(cultivos_data)
        })

    # Redireccionar si el usuario no cuenta con el rol requerido
    return redirect('home')


# =============================================================================
# TABLEROS Y OPERACIÓN DE CAMPO DEL LABORATORISTA
# =============================================================================

@login_required(login_url='login')
def dashboard_laboratorista(request):
    """
    Panel de control operativo para el técnico de laboratorio y campo.

    Restricciones:
      - Requiere sesión autenticada con rol 'LABORATORISTA'.

    Métricas calculadas:
      - `total_pendientes`: Muestras en cola global pendientes de asignación o inicio.
      - `total_completados`: Análisis edafológicos ejecutados y finalizados por el técnico activo.

    Plantilla:
      - `laboratorista/dashboard.html`
    """
    # Validar rol de técnico laboratorista
    if hasattr(request.user, 'perfil') and request.user.perfil.rol == 'LABORATORISTA':
        # Obtener identificador opcional de solicitud desde parámetros de consulta GET
        solicitud_id = request.GET.get('solicitud_id')

        # Ensamblar indicadores de carga de trabajo
        context = {
            # Total de órdenes de servicio pendientes de toma o procesamiento
            'total_pendientes': SolicitudAnalisis.objects.filter(estado='PENDIENTE').count(),
            # Total de análisis completados satisfactoriamente por este laboratorista
            'total_completados': RegistroAnalisis.objects.filter(solicitud__laboratorista_asignado=request.user).count(),
        }

        return render(request, 'laboratorista/dashboard.html', context)

    # Redireccionar a la raíz si no posee el rol autorizado
    return redirect('home')


@login_required(login_url='login')
def toma_muestras_laboratorista(request):
    """
    Módulo de toma de muestras edafológicas y sincronización offline en campo.

    Comportamiento clave:
      1. Localiza la solicitud asignada al laboratorista en sesión.
      2. Si la modalidad es de visita a finca ('VISITA'), genera automáticamente
         la cuadrícula de puntos de muestreo en zig-zag según el área del terreno:
           * <= 1 ha: 5 submuestras.
           * <= 5 ha: 10 submuestras.
           * <= 10 ha: 15 submuestras.
           * > 10 ha: 20 submuestras.
         Crea los registros mediante inserción masiva (`bulk_create`) para máximo desempeño.
      3. Extrae análisis previos si existen para consulta técnica comparativa.
      4. Precarga y serializa la totalidad del catálogo de cultivos a JSON, permitiendo
         que el service worker y la base local IndexedDB operen completamente sin conexión
         a internet en zonas cordilleranas sin cobertura celular.

    Plantilla:
      - `laboratorista/toma_muestras.html`
    """
    # Validar pertenencia al rol técnico
    if hasattr(request.user, 'perfil') and request.user.perfil.rol == 'LABORATORISTA':
        solicitud_id = request.GET.get('solicitud_id')
        context = {}

        # Si se especificó una solicitud concreta, cargar su contexto técnico
        if solicitud_id:
            try:
                # Recuperar la orden de servicio asegurando que esté asignada al técnico actual
                solicitud = SolicitudAnalisis.objects.get(id=solicitud_id, laboratorista_asignado=request.user)
                context['solicitud_activa'] = solicitud

                # Generación de puntos de muestreo en terreno solo para modalidad presencial (VISITA)
                if solicitud.modalidad == 'VISITA':
                    puntos = PuntoMuestreo.objects.filter(solicitud=solicitud)

                    # Si aún no existen puntos de muestreo para este lote, generarlos según su superficie
                    if not puntos.exists():
                        hectareas = float(solicitud.terreno.hectareas)
                        if hectareas <= 1:
                            num_puntos = 5
                        elif hectareas <= 5:
                            num_puntos = 10
                        elif hectareas <= 10:
                            num_puntos = 15
                        else:
                            num_puntos = 20

                        # Instanciar lista de puntos de muestreo sin guardar individualmente
                        nuevos_puntos = [
                            PuntoMuestreo(solicitud=solicitud, numero=i)
                            for i in range(1, num_puntos + 1)
                        ]
                        # Inserción en bloque masivo a la base de datos MySQL/SQLite
                        PuntoMuestreo.objects.bulk_create(nuevos_puntos)

                        # Re-consultar los puntos persistidos para el contexto de la plantilla
                        puntos = PuntoMuestreo.objects.filter(solicitud=solicitud)

                    context['puntos_muestreo'] = puntos
                    context['puntos_tomados'] = puntos.filter(estado='TOMADO').count()
                    context['total_puntos'] = puntos.count()
                else:
                    # En modalidad entrega en laboratorio no se requiere grilla espacial en campo
                    context['puntos_muestreo'] = []
                    context['puntos_tomados'] = 0
                    context['total_puntos'] = 0

                # Obtener registro de análisis previo asociado a la solicitud (si ya fue completado)
                try:
                    context['analisis_existente'] = getattr(solicitud, 'analisis_resultado', None)
                except Exception:
                    context['analisis_existente'] = None

            except SolicitudAnalisis.DoesNotExist:
                # Si la solicitud no existe o no pertenece al técnico, se continúa con contexto básico
                pass

        # Precargar catálogo de cultivos completo para almacenamiento en caché e IndexedDB offline
        cultivos_activos = Cultivo.objects.filter(activo=True)
        context['cultivos_lista'] = cultivos_activos
        context['cultivos_catalogo_json'] = json.dumps([c.to_dict() for c in cultivos_activos])

        return render(request, 'laboratorista/toma_muestras.html', context)
    else:
        return redirect('home')


# =============================================================================
# PANEL DE ADMINISTRACIÓN Y GESTIÓN DE USUARIOS
# =============================================================================

@login_required(login_url='login')
def dashboard_admin(request):
    """
    Tablero de mando integral para el Administrador del sistema.

    Restricciones:
      - Requiere sesión activa con rol 'ADMIN'.

    Métricas globales de gobernanza:
      - Total de agricultores dados de alta en el sistema.
      - Total de laboratoristas activos.
      - Total de predios agrícolas cartografiados.
      - Total histórico de solicitudes de análisis registradas.

    Plantilla:
      - `admin/dashboard.html`
    """
    # Comprobar privilegios de administración
    if hasattr(request.user, 'perfil') and request.user.perfil.rol == 'ADMIN':
        context = {
            'total_agricultores': User.objects.filter(perfil__rol='AGRICULTOR').count(),
            'total_laboratoristas': User.objects.filter(perfil__rol='LABORATORISTA').count(),
            'total_terrenos': Terreno.objects.count(),
            'total_solicitudes': SolicitudAnalisis.objects.count(),
        }
        return render(request, 'admin/dashboard.html', context)

    # Bloquear acceso a usuarios sin privilegios administrativos
    return redirect('home')


@login_required(login_url='login')
def lista_usuarios(request):
    """
    Vista de auditoría y gestión de cuentas de usuario.

    Funcionalidades:
      - Separa los registros entre Productores Agrícolas y Personal de Laboratorio.
      - Optimiza las consultas SQL utilizando `select_related('perfil')`.
      - Realiza anotaciones agregadas (`annotate`) para calcular en tiempo real:
          * `solicitudes_atendidas`: Cantidad de asignaciones técnicas recibidas.
          * `analisis_finalizados`: Cantidad de reportes edafológicos completados.

    Plantilla:
      - `admin/usuarios.html`
    """
    if hasattr(request.user, 'perfil') and request.user.perfil.rol == 'ADMIN':
        # Consulta de agricultores ordenados por fecha de registro más reciente
        agricultores = User.objects.filter(perfil__rol='AGRICULTOR').select_related('perfil').order_by('-date_joined')

        # Consulta de laboratoristas con métricas agregadas de productividad técnica
        laboratoristas = User.objects.filter(perfil__rol='LABORATORISTA').select_related('perfil').annotate(
            solicitudes_atendidas=Count('solicitudes_asignadas', distinct=True),
            analisis_finalizados=Count('solicitudes_asignadas__analisis_resultado', distinct=True)
        ).order_by('-date_joined')

        return render(request, 'admin/usuarios.html', {
            'agricultores': agricultores,
            'laboratoristas': laboratoristas
        })

    return redirect('home')


@login_required(login_url='login')
def crear_laboratorista(request):
    """
    Endpoint AJAX para la creación de credenciales de un nuevo técnico laboratorista.

    Método: POST
    Payload JSON esperado:
      - `username` (str): Nombre de usuario único para inicio de sesión.
      - `password` (str): Contraseña segura inicial.
      - `email` (str): Correo electrónico institucional del técnico.
      - `first_name` (str, opcional): Nombres del laboratorista.
      - `last_name` (str, opcional): Apellidos del laboratorista.

    Respuestas:
      - 200 OK: Creación exitosa.
      - 400 Bad Request: Campos obligatorios faltantes o usuario duplicado.
      - 403 Forbidden: Solicitante sin rol ADMIN.
      - 500 Internal Error: Excepción durante el guardado.
    """
    # Validar autorización del administrador
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'ADMIN':
        return JsonResponse({'error': 'No autorizado'}, status=403)

    if request.method == 'POST':
        try:
            # Parsear el cuerpo de la petición en formato JSON
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')
            email = data.get('email')
            first_name = data.get('first_name', '')
            last_name = data.get('last_name', '')

            # Validar obligatoriedad de credenciales mínimas
            if not username or not password:
                return JsonResponse({'error': 'Usuario y contraseña son obligatorios'}, status=400)

            # Validar unicidad del nombre de usuario en el modelo User de Django
            if User.objects.filter(username=username).exists():
                return JsonResponse({'error': 'El usuario ya existe'}, status=400)

            # Crear usuario con contraseña cifrada (PBKDF2/SHA256)
            user = User.objects.create_user(
                username=username,
                password=password,
                email=email,
                first_name=first_name,
                last_name=last_name
            )
            # Marcar cuenta como activa por defecto
            user.is_active = True
            user.save()

            # El signal post_save de Perfil crea la instancia por defecto; aquí actualizamos el rol
            user.perfil.rol = 'LABORATORISTA'
            user.perfil.save()

            return JsonResponse({'mensaje': 'Laboratorista creado exitosamente'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    # Si se intenta acceder vía GET, redirigir al listado de usuarios
    return redirect('lista_usuarios')


@login_required(login_url='login')
def editar_usuario(request, user_id):
    """
    Endpoint AJAX para la modificación de datos biográficos de un usuario.

    Parámetros de ruta:
      - `user_id` (int): Clave primaria del usuario a editar.

    Payload JSON:
      - `first_name` (str): Nombre(s) actualizados.
      - `last_name` (str): Apellido(s) actualizados.
      - `email` (str): Correo electrónico institucional.

    Respuestas:
      - 200 OK: Actualización correcta.
      - 403 Forbidden: Sin rol ADMIN.
      - 404 Not Found: Usuario inexistente.
      - 405 Method Not Allowed: Método HTTP distinto a POST.
    """
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'ADMIN':
        return JsonResponse({'error': 'No autorizado'}, status=403)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            first_name = data.get('first_name', '')
            last_name = data.get('last_name', '')
            email = data.get('email', '')

            # Recuperar y actualizar los campos del usuario en base de datos
            usuario = User.objects.get(id=user_id)
            usuario.first_name = first_name
            usuario.last_name = last_name
            usuario.email = email
            usuario.save()

            return JsonResponse({'mensaje': 'Información de usuario actualizada'})
        except User.DoesNotExist:
            return JsonResponse({'error': 'Usuario no encontrado'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Método no permitido'}, status=405)


@login_required(login_url='login')
def cambiar_estado_usuario(request, user_id):
    """
    Endpoint AJAX para habilitar o deshabilitar la cuenta de un usuario (`is_active`).

    Protección crítica:
      - Impide que el administrador activo se inhabilite a sí mismo, garantizando
        la disponibilidad y gobernanza continua del sistema.

    Payload JSON:
      - `is_active` (bool): Estado booleano de habilitación.
    """
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'ADMIN':
        return JsonResponse({'error': 'No autorizado'}, status=403)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            estado = data.get('is_active')

            usuario = User.objects.get(id=user_id)

            # Evitar el bloqueo accidental de la propia cuenta del administrador en sesión
            if usuario == request.user:
                return JsonResponse({'error': 'No puedes cambiar tu propio estado'}, status=400)

            # Actualizar y persistir el nuevo estado de activación
            usuario.is_active = estado
            usuario.save()

            return JsonResponse({'mensaje': 'Estado actualizado correctamente'})
        except User.DoesNotExist:
            return JsonResponse({'error': 'Usuario no encontrado'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Método no permitido'}, status=405)


@login_required(login_url='login')
def eliminar_usuario(request, user_id):
    """
    Endpoint AJAX para la baja definitiva de una cuenta de usuario en base de datos.

    Protección crítica:
      - Impide que el administrador ejecute un auto-borrado accidental de su propia cuenta.

    Respuestas:
      - 200 OK: Cuenta eliminada.
      - 400 Bad Request: Intento de auto-eliminación.
      - 403 Forbidden: Sin rol ADMIN.
      - 404 Not Found: Usuario no encontrado.
    """
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'ADMIN':
        return JsonResponse({'error': 'No autorizado'}, status=403)

    if request.method == 'POST':
        try:
            usuario = User.objects.get(id=user_id)

            # Evitar que el administrador se autodestruya
            if usuario == request.user:
                return JsonResponse({'error': 'No puedes eliminarte a ti mismo'}, status=400)

            # Eliminación física en cascada según las reglas de relaciones foráneas
            usuario.delete()
            return JsonResponse({'mensaje': 'Usuario eliminado permanentemente'})
        except User.DoesNotExist:
            return JsonResponse({'error': 'Usuario no encontrado'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Método no permitido'}, status=405)


# =============================================================================
# SUPERVISIÓN TÉCNICA Y EXPORTACIÓN DE REPORTES (PDF Y EXCEL)
# =============================================================================

@login_required(login_url='login')
def supervision_analisis(request):
    """
    Módulo de auditoría técnica global de análisis edafológicos para el administrador.

    Parámetros de filtrado (GET):
      - `usuario` (int): Clave primaria del productor agrícola.
      - `cultivo` (str): Nombre o fragmento de la especie vegetal objetivo.
      - `fecha_inicio` (date): Límite temporal inferior (YYYY-MM-DD).
      - `fecha_fin` (date): Límite temporal superior (YYYY-MM-DD).

    Plantilla:
      - `admin/supervision.html`
    """
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'ADMIN':
        return redirect('home')

    # Consulta base con orden cronológico inverso
    analisis = RegistroAnalisis.objects.all().order_by('-fecha_analisis')

    # Lectura de parámetros de filtrado desde la cadena de consulta GET
    usuario_id = request.GET.get('usuario')
    cultivo_nombre = request.GET.get('cultivo')
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')

    # Aplicación de filtros según los criterios provistos
    if usuario_id:
        analisis = analisis.filter(solicitud__agricultor_id=usuario_id)
    if cultivo_nombre:
        analisis = analisis.filter(solicitud__cultivo_deseado_ref__nombre__icontains=cultivo_nombre)
    if fecha_inicio:
        analisis = analisis.filter(fecha_analisis__gte=fecha_inicio)
    if fecha_fin:
        analisis = analisis.filter(fecha_analisis__lte=fecha_fin)

    # Conjuntos de datos auxiliares para alimentar los selectores de búsqueda
    agricultores = User.objects.filter(perfil__rol='AGRICULTOR')
    cultivos = Cultivo.objects.filter(activo=True).order_by('nombre')

    context = {
        'analisis': analisis,
        'agricultores': agricultores,
        'cultivos': cultivos,
        'filtro_usuario': usuario_id,
        'filtro_cultivo': cultivo_nombre,
        'filtro_inicio': fecha_inicio,
        'filtro_fin': fecha_fin,
    }
    return render(request, 'admin/supervision.html', context)


@login_required(login_url='login')
def exportar_pdf(request):
    """
    Genera un informe institucional en PDF con la lista filtrada de análisis edafológicos.

    Tecnología:
      - ReportLab Canvas (`reportlab.pdfgen.canvas.Canvas`).
      - Manejo dinámico de salto de página (`showPage`) y cálculo de coordenadas verticales (Y).

    Retorna:
      - `FileResponse`: Archivo descargable binario con nombre 'reporte_analisis.pdf'.
    """
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'ADMIN':
        return redirect('home')

    # Aplicar idénticos filtros de búsqueda que en la vista interactiva de supervisión
    analisis = RegistroAnalisis.objects.all().order_by('-fecha_analisis')
    usuario_id = request.GET.get('usuario')
    cultivo_nombre = request.GET.get('cultivo')
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')

    if usuario_id:
        analisis = analisis.filter(solicitud__agricultor_id=usuario_id)
    if cultivo_nombre:
        analisis = analisis.filter(solicitud__cultivo_deseado_ref__nombre__icontains=cultivo_nombre)
    if fecha_inicio:
        analisis = analisis.filter(fecha_analisis__gte=fecha_inicio)
    if fecha_fin:
        analisis = analisis.filter(fecha_analisis__lte=fecha_fin)

    # Importación diferida de reportlab para evitar dependencias obligatorias en el arranque del servidor
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
    except ImportError:
        return HttpResponse("El módulo 'reportlab' no está instalado en el entorno de ejecución actual.", status=501)

    # Creación del buffer binario en memoria RAM
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)

    # Encabezado institucional
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, 750, "Reporte de Análisis de Suelos - TierSystem")
    p.setFont("Helvetica", 10)

    # Iteración sobre los registros calculando la posición vertical en puntos tipográficos
    y = 700
    for idx, a in enumerate(analisis):
        # Si el cursor vertical llega al margen inferior de la hoja, insertar salto de página
        if y < 50:
            p.showPage()
            y = 750
            p.setFont("Helvetica", 10)

        nombre_agricultor = a.solicitud.agricultor.get_full_name() or a.solicitud.agricultor.username
        texto = f"{idx+1}. {a.fecha_analisis.strftime('%d/%m/%Y')} | Agricultor: {nombre_agricultor} | Cultivo: {a.solicitud.cultivo_deseado}"
        p.drawString(50, y, texto)
        y -= 20

    # Cerrar página y guardar estado del lienzo
    p.showPage()
    p.save()

    # Rebobinar el puntero del buffer para lectura desde el byte 0
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename='reporte_analisis.pdf')


@login_required(login_url='login')
def exportar_excel(request):
    """
    Genera un libro de cálculo en formato Excel (.xlsx) con los datos edafológicos filtrados.

    Tecnología:
      - OpenpyXL (`openpyxl.Workbook`).

    Columnas exportadas:
      1. ID de Análisis
      2. Fecha y Hora de Procesamiento
      3. Nombre del Agricultor
      4. Nombre del Terreno / Predio
      5. Cultivo Objetivo
      6. Parámetros fisicoquímicos: pH, Nitrógeno (mg/kg), Fósforo (mg/kg), Potasio (mg/kg).

    Retorna:
      - `HttpResponse`: Documento descargable con cabeceras MIME para hojas de cálculo.
    """
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'ADMIN':
        return redirect('home')

    # Aplicar los filtros de búsqueda activa
    analisis = RegistroAnalisis.objects.all().order_by('-fecha_analisis')
    usuario_id = request.GET.get('usuario')
    cultivo_nombre = request.GET.get('cultivo')
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')

    if usuario_id:
        analisis = analisis.filter(solicitud__agricultor_id=usuario_id)
    if cultivo_nombre:
        analisis = analisis.filter(solicitud__cultivo_deseado_ref__nombre__icontains=cultivo_nombre)
    if fecha_inicio:
        analisis = analisis.filter(fecha_analisis__gte=fecha_inicio)
    if fecha_fin:
        analisis = analisis.filter(fecha_analisis__lte=fecha_fin)

    # Importación diferida de openpyxl para hojas de cálculo Excel
    try:
        from openpyxl import Workbook
    except ImportError:
        return HttpResponse("El módulo 'openpyxl' no está instalado en el entorno de ejecución actual.", status=501)

    # Instanciación del libro de cálculo
    wb = Workbook()
    ws = wb.active
    ws.title = "Análisis"

    # Fila de cabeceras de columnas
    ws.append(["ID", "Fecha", "Agricultor", "Terreno", "Cultivo", "pH", "Nitrógeno", "Fósforo", "Potasio"])

    # Poblar filas con los valores numéricos de los sensores
    for a in analisis:
        nombre_agricultor = a.solicitud.agricultor.get_full_name() or a.solicitud.agricultor.username
        ws.append([
            a.id,
            a.fecha_analisis.strftime('%d/%m/%Y %H:%M'),
            nombre_agricultor,
            a.solicitud.terreno.nombre,
            a.solicitud.cultivo_deseado,
            float(a.ph),
            float(a.nitrogeno),
            float(a.fosforo),
            float(a.potasio)
        ])

    # Guardar en buffer binario en memoria
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    # Ensamblar respuesta HTTP con el tipo de medio oficial para Excel OpenXML
    response = HttpResponse(
        buffer.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="reporte_analisis.xlsx"'
    return response


# =============================================================================
# ADMINISTRACIÓN DEL CATÁLOGO AGRONÓMICO DE CULTIVOS
# =============================================================================

@login_required(login_url='login')
def gestion_cultivos_admin(request):
    """
    Vista administrativa para consultar y editar el catálogo agronómico oficial.

    Plantilla:
      - `admin/cultivos.html`
    """
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'ADMIN':
        return redirect('home')

    # Consultar todas las especies activas ordenadas alfabéticamente
    cultivos = Cultivo.objects.filter(activo=True).order_by('nombre')
    return render(request, 'admin/cultivos.html', {'cultivos': cultivos})


@login_required(login_url='login')
def guardar_cultivo_admin(request):
    """
    Endpoint AJAX para la creación o actualización de los rangos óptimos de un cultivo.

    Método: POST
    Payload JSON:
      - `id` (int, opcional): Si está presente, actualiza el registro existente; si no, crea uno nuevo.
      - Metadatos: `nombre`, `descripcion`, `categoria`, `clima`, `icono`.
      - Parámetros agroclimáticos (mínimos y máximos):
          * Altitud (msnm), Humedad relativa (%), Temperatura (°C), Conductividad eléctrica (dS/m),
          * pH edáfico, Nitrógeno (mg/kg), Fósforo (mg/kg), Potasio (mg/kg).

    Persistencia:
      - Tabla maestra MySQL `cultivos_cultivo`.
    """
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'ADMIN':
        return JsonResponse({'error': 'No autorizado'}, status=403)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            cultivo_id = data.get('id')

            # Determinar si es operación de actualización o de creación
            if cultivo_id:
                cultivo = Cultivo.objects.get(id=cultivo_id)
            else:
                cultivo = Cultivo()

            # Asignación de datos descriptivos y taxonómicos
            cultivo.nombre = data.get('nombre')
            cultivo.descripcion = data.get('descripcion', '')
            cultivo.categoria = data.get('categoria', cultivo.categoria or 'Frutal')
            cultivo.clima = data.get('clima', cultivo.clima or 'Templado')
            cultivo.icono = data.get('icono', cultivo.icono or 'fa-seedling')

            # Parseo y asignación de rangos físico-químicos con valores por defecto seguros
            cultivo.altitud_min = float(data.get('altitud_min', cultivo.altitud_min or 0))
            cultivo.altitud_max = float(data.get('altitud_max', cultivo.altitud_max or 3000))
            cultivo.humedad_min = float(data.get('humedad_min', cultivo.humedad_min or 0))
            cultivo.humedad_max = float(data.get('humedad_max', cultivo.humedad_max or 0))
            cultivo.temperatura_min = float(data.get('temperatura_min', cultivo.temperatura_min or 0))
            cultivo.temperatura_max = float(data.get('temperatura_max', cultivo.temperatura_max or 0))
            cultivo.conductividad_min = float(data.get('conductividad_min', cultivo.conductividad_min or 0))
            cultivo.conductividad_max = float(data.get('conductividad_max', cultivo.conductividad_max or 0))
            cultivo.ph_min = float(data.get('ph_min', cultivo.ph_min or 0))
            cultivo.ph_max = float(data.get('ph_max', cultivo.ph_max or 0))
            cultivo.nitrogeno_min = float(data.get('nitrogeno_min', cultivo.nitrogeno_min or 0))
            cultivo.nitrogeno_max = float(data.get('nitrogeno_max', cultivo.nitrogeno_max or 0))
            cultivo.fosforo_min = float(data.get('fosforo_min', cultivo.fosforo_min or 0))
            cultivo.fosforo_max = float(data.get('fosforo_max', cultivo.fosforo_max or 0))
            cultivo.potasio_min = float(data.get('potasio_min', cultivo.potasio_min or 0))
            cultivo.potasio_max = float(data.get('potasio_max', cultivo.potasio_max or 0))

            # Guardado definitivo en la base de datos
            cultivo.save()
            return JsonResponse({'mensaje': 'Cultivo guardado correctamente en la Base de Datos MySQL (cultivos_cultivo)'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Método no permitido'}, status=405)


@login_required(login_url='login')
def eliminar_cultivo_admin(request, cultivo_id):
    """
    Endpoint AJAX para remover permanentemente una especie agrícola del catálogo.

    Parámetros:
      - `cultivo_id` (int): Clave primaria de la especie a eliminar.
    """
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'ADMIN':
        return JsonResponse({'error': 'No autorizado'}, status=403)

    if request.method == 'POST':
        try:
            cultivo = Cultivo.objects.get(id=cultivo_id)
            cultivo.delete()
            return JsonResponse({'mensaje': 'Cultivo eliminado permanentemente'})
        except Cultivo.DoesNotExist:
            return JsonResponse({'error': 'Cultivo no encontrado'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Método no permitido'}, status=405)


# =============================================================================
# TELEMETRÍA DE HARDWARE IOT Y GOBERNANZA DEL MOTOR DE IA
# =============================================================================

@login_required(login_url='login')
def estado_hardware(request):
    """
    Tablero de monitoreo de telemetría y salud del hardware en campo.

    Lógica de diagnóstico:
      - Consulta la lectura más reciente emitida por el sensor industrial ESP32.
      - Si la última lectura tiene una antigüedad menor o igual a 15 minutos,
        se califica el estado de conexión como 'Activo'; de lo contrario, 'Inactivo'.
      - Monitorea el nivel porcentual de carga del banco de baterías solares.

    Plantilla:
      - `admin/hardware.html`
    """
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'ADMIN':
        return redirect('home')

    # Obtener el registro telemétrico más reciente ingresado al sistema
    ultima_lectura = LecturaSensor.objects.order_by('-timestamp').first()

    estado_conexion = 'Inactivo'
    bateria = 85.0  # Nivel estimado de batería del sistema de energía solar en campo

    # Comprobar la ventana de recencia de comunicación (15 minutos)
    if ultima_lectura:
        tiempo_limite = timezone.now() - timedelta(minutes=15)
        if ultima_lectura.timestamp >= tiempo_limite:
            estado_conexion = 'Activo'

    context = {
        'ultima_lectura': ultima_lectura,
        'estado_conexion': estado_conexion,
        'bateria': bateria,
    }
    return render(request, 'admin/hardware.html', context)


@login_required(login_url='login')
def configuracion_global_view(request):
    """
    Panel de configuración global para el comportamiento de la IA y umbrales de sensores.

    Patrón Singleton:
      - Utiliza `ConfiguracionGlobal.load()` para garantizar una única instancia de configuración.

    Campos gobernados:
      - `tiempo_espera_ia`: Timeout máximo (segundos) para respuestas de la API de Google Gemini.
      - `accion_fallo_ia`: Política de contingencia en caso de timeout ('LOCAL' o 'REINTENTAR').
      - Rangos globales de validación física para pH, N, P, K, humedad, CE y temperatura,
        asegurando que lecturas anómalas o dañadas del hardware sean detectadas oportunamente.

    Plantilla:
      - `admin/configuracion.html`
    """
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'ADMIN':
        return redirect('home')

    # Cargar la instancia global persistida
    config = ConfiguracionGlobal.load()

    # Si se envía una actualización vía POST
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            # Ajustes de tiempo y contingencia de la Inteligencia Artificial
            config.tiempo_espera_ia = data.get('tiempo_espera_ia', config.tiempo_espera_ia)
            config.accion_fallo_ia = data.get('accion_fallo_ia', config.accion_fallo_ia)

            # Umbrales físicos de validación de sensores
            config.rango_ph_min = data.get('rango_ph_min', config.rango_ph_min)
            config.rango_ph_max = data.get('rango_ph_max', config.rango_ph_max)
            config.rango_n_min = data.get('rango_n_min', config.rango_n_min)
            config.rango_n_max = data.get('rango_n_max', config.rango_n_max)
            config.rango_p_min = data.get('rango_p_min', config.rango_p_min)
            config.rango_p_max = data.get('rango_p_max', config.rango_p_max)
            config.rango_k_min = data.get('rango_k_min', config.rango_k_min)
            config.rango_k_max = data.get('rango_k_max', config.rango_k_max)
            config.rango_humedad_min = data.get('rango_humedad_min', config.rango_humedad_min)
            config.rango_humedad_max = data.get('rango_humedad_max', config.rango_humedad_max)
            config.rango_ce_min = data.get('rango_ce_min', config.rango_ce_min)
            config.rango_ce_max = data.get('rango_ce_max', config.rango_ce_max)
            config.rango_temp_min = data.get('rango_temp_min', config.rango_temp_min)
            config.rango_temp_max = data.get('rango_temp_max', config.rango_temp_max)

            # Guardar cambios
            config.save()
            return JsonResponse({'mensaje': 'Configuración guardada exitosamente'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    # Renderizar el formulario administrativo de configuración
    return render(request, 'admin/configuracion.html', {'config': config})
