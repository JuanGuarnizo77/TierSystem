from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

def home(request):
    if request.user.is_authenticated:
        if hasattr(request.user, 'perfil'):
            if request.user.perfil.rol == 'LABORATORISTA':
                return redirect('dashboard_laboratorista')
            elif request.user.perfil.rol == 'AGRICULTOR':
                return redirect('dashboard_agricultor')
            elif request.user.perfil.rol == 'ADMIN':
                return redirect('dashboard_admin')
    return render(request, 'home.html')

@login_required(login_url='login')
def dashboard_agricultor(request):
    if hasattr(request.user, 'perfil') and request.user.perfil.rol == 'AGRICULTOR':
        from apps.terrenos.models import Terreno
        from apps.solicitudes.models import SolicitudAnalisis
        
        context = {
            'total_terrenos': Terreno.objects.filter(agricultor=request.user).count(),
            'solicitudes_activas': SolicitudAnalisis.objects.filter(agricultor=request.user).exclude(estado='COMPLETADA').count(),
        }
        return render(request, 'agricultor/dashboard.html', context)
    return redirect('home')

@login_required(login_url='login')
def catalogo_cultivos(request):
    if hasattr(request.user, 'perfil') and request.user.perfil.rol == 'AGRICULTOR':
        import json
        from .cultivos_data import CULTIVOS_HUILA
        
        # Enviamos la lista entera en formato JSON para que JS la ponga en tarjetas
        cultivos_json = json.dumps(CULTIVOS_HUILA)
        return render(request, 'agricultor/cultivos.html', {'cultivos_json': cultivos_json})
    return redirect('home')

@login_required(login_url='login')
def dashboard_laboratorista(request):
    if hasattr(request.user, 'perfil') and request.user.perfil.rol == 'LABORATORISTA':
        from apps.solicitudes.models import SolicitudAnalisis
        from apps.analisis.models import RegistroAnalisis
        
        solicitud_id = request.GET.get('solicitud_id')
        context = {
            'total_pendientes': SolicitudAnalisis.objects.filter(estado='PENDIENTE').count(),
            'total_completados': RegistroAnalisis.objects.filter(solicitud__laboratorista_asignado=request.user).count(),
        }
        
        if solicitud_id:
            try:
                solicitud = SolicitudAnalisis.objects.get(id=solicitud_id, laboratorista_asignado=request.user)
                context['solicitud_activa'] = solicitud
            except SolicitudAnalisis.DoesNotExist:
                pass
                
        return render(request, 'laboratorista/dashboard.html', context)
    else:
        return redirect('home')

@login_required(login_url='login')
def dashboard_admin(request):
    if hasattr(request.user, 'perfil') and request.user.perfil.rol == 'ADMIN':
        from django.contrib.auth.models import User
        from apps.terrenos.models import Terreno
        from apps.solicitudes.models import SolicitudAnalisis
        
        context = {
            'total_agricultores': User.objects.filter(perfil__rol='AGRICULTOR').count(),
            'total_laboratoristas': User.objects.filter(perfil__rol='LABORATORISTA').count(),
            'total_terrenos': Terreno.objects.count(),
            'total_solicitudes': SolicitudAnalisis.objects.count(),
        }
        return render(request, 'admin/dashboard.html', context)
    return redirect('home')

@login_required(login_url='login')
def lista_usuarios(request):
    if hasattr(request.user, 'perfil') and request.user.perfil.rol == 'ADMIN':
        from django.contrib.auth.models import User
        from django.db.models import Count
        
        agricultores = User.objects.filter(perfil__rol='AGRICULTOR').select_related('perfil').order_by('-date_joined')
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
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'ADMIN':
        from django.http import JsonResponse
        return JsonResponse({'error': 'No autorizado'}, status=403)
        
    if request.method == 'POST':
        from django.contrib.auth.models import User
        from apps.usuarios.models import Perfil
        from django.http import JsonResponse
        import json
        
        try:
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')
            email = data.get('email')
            first_name = data.get('first_name', '')
            last_name = data.get('last_name', '')
            
            if User.objects.filter(username=username).exists():
                return JsonResponse({'error': 'El usuario ya existe'}, status=400)
                
            user = User.objects.create_user(
                username=username,
                password=password,
                email=email,
                first_name=first_name,
                last_name=last_name
            )
            # Se agrega activo por defecto según la solicitud
            user.is_active = True
            user.save()
            
            # El signal 'crear_perfil_usuario' ya creó el Perfil por defecto, lo actualizamos.
            user.perfil.rol = 'LABORATORISTA'
            user.perfil.save()
            
            return JsonResponse({'mensaje': 'Laboratorista creado exitosamente'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
            
    return redirect('lista_usuarios')


@login_required(login_url='login')
def editar_usuario(request, user_id):
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'ADMIN':
        from django.http import JsonResponse
        return JsonResponse({'error': 'No autorizado'}, status=403)
        
    if request.method == 'POST':
        from django.contrib.auth.models import User
        from django.http import JsonResponse
        import json
        
        try:
            data = json.loads(request.body)
            first_name = data.get('first_name', '')
            last_name = data.get('last_name', '')
            email = data.get('email', '')
            
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
            
    from django.http import JsonResponse
    return JsonResponse({'error': 'Método no permitido'}, status=405)

@login_required(login_url='login')
def cambiar_estado_usuario(request, user_id):
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'ADMIN':
        from django.http import JsonResponse
        return JsonResponse({'error': 'No autorizado'}, status=403)
        
    if request.method == 'POST':
        from django.contrib.auth.models import User
        from django.http import JsonResponse
        import json
        
        try:
            data = json.loads(request.body)
            estado = data.get('is_active')
            
            usuario = User.objects.get(id=user_id)
            # Evitar que el admin se desactive a sí mismo
            if usuario == request.user:
                return JsonResponse({'error': 'No puedes cambiar tu propio estado'}, status=400)
                
            usuario.is_active = estado
            usuario.save()
            
            return JsonResponse({'mensaje': 'Estado actualizado correctamente'})
        except User.DoesNotExist:
            return JsonResponse({'error': 'Usuario no encontrado'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
            
    from django.http import JsonResponse
    return JsonResponse({'error': 'Método no permitido'}, status=405)

@login_required(login_url='login')
def eliminar_usuario(request, user_id):
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'ADMIN':
        from django.http import JsonResponse
        return JsonResponse({'error': 'No autorizado'}, status=403)
        
    if request.method == 'POST':
        from django.contrib.auth.models import User
        from django.http import JsonResponse
        
        try:
            usuario = User.objects.get(id=user_id)
            # Evitar que el admin se elimine a sí mismo
            if usuario == request.user:
                return JsonResponse({'error': 'No puedes eliminarte a ti mismo'}, status=400)
                
            usuario.delete()
            return JsonResponse({'mensaje': 'Usuario eliminado permanentemente'})
        except User.DoesNotExist:
            return JsonResponse({'error': 'Usuario no encontrado'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
            
    from django.http import JsonResponse
    return JsonResponse({'error': 'Método no permitido'}, status=405)

@login_required(login_url='login')
def supervision_analisis(request):
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'ADMIN':
        return redirect('home')
        
    from apps.analisis.models import RegistroAnalisis
    from apps.ia_recomendaciones.models import CultivoIdeal
    from django.contrib.auth.models import User
    
    analisis = RegistroAnalisis.objects.all().order_by('-fecha_analisis')
    
    # Filtros
    usuario_id = request.GET.get('usuario')
    cultivo_nombre = request.GET.get('cultivo')
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    
    if usuario_id:
        analisis = analisis.filter(solicitud__agricultor_id=usuario_id)
    if cultivo_nombre:
        analisis = analisis.filter(solicitud__cultivo_deseado__icontains=cultivo_nombre)
    if fecha_inicio:
        analisis = analisis.filter(fecha_analisis__gte=fecha_inicio)
    if fecha_fin:
        analisis = analisis.filter(fecha_analisis__lte=fecha_fin)
        
    agricultores = User.objects.filter(perfil__rol='AGRICULTOR')
    cultivos = CultivoIdeal.objects.all()
    
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
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'ADMIN':
        return redirect('home')
        
    import io
    from django.http import FileResponse
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from apps.analisis.models import RegistroAnalisis
    
    # Aplicar los mismos filtros que en la vista normal
    analisis = RegistroAnalisis.objects.all().order_by('-fecha_analisis')
    usuario_id = request.GET.get('usuario')
    cultivo_nombre = request.GET.get('cultivo')
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    
    if usuario_id:
        analisis = analisis.filter(solicitud__agricultor_id=usuario_id)
    if cultivo_nombre:
        analisis = analisis.filter(solicitud__cultivo_deseado__icontains=cultivo_nombre)
    if fecha_inicio:
        analisis = analisis.filter(fecha_analisis__gte=fecha_inicio)
    if fecha_fin:
        analisis = analisis.filter(fecha_analisis__lte=fecha_fin)

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, 750, "Reporte de Análisis de Suelos - TierSystem")
    p.setFont("Helvetica", 10)
    
    y = 700
    for idx, a in enumerate(analisis):
        if y < 50:
            p.showPage()
            y = 750
            p.setFont("Helvetica", 10)
            
        texto = f"{idx+1}. {a.fecha_analisis.strftime('%d/%m/%Y')} | Agricultor: {a.solicitud.agricultor.get_full_name() or a.solicitud.agricultor.username} | Cultivo: {a.solicitud.cultivo_deseado}"
        p.drawString(50, y, texto)
        y -= 20
        
    p.showPage()
    p.save()
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename='reporte_analisis.pdf')

@login_required(login_url='login')
def exportar_excel(request):
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'ADMIN':
        return redirect('home')
        
    import io
    from django.http import HttpResponse
    from openpyxl import Workbook
    from apps.analisis.models import RegistroAnalisis
    
    # Aplicar los mismos filtros
    analisis = RegistroAnalisis.objects.all().order_by('-fecha_analisis')
    usuario_id = request.GET.get('usuario')
    cultivo_nombre = request.GET.get('cultivo')
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    
    if usuario_id:
        analisis = analisis.filter(solicitud__agricultor_id=usuario_id)
    if cultivo_nombre:
        analisis = analisis.filter(solicitud__cultivo_deseado__icontains=cultivo_nombre)
    if fecha_inicio:
        analisis = analisis.filter(fecha_analisis__gte=fecha_inicio)
    if fecha_fin:
        analisis = analisis.filter(fecha_analisis__lte=fecha_fin)

    wb = Workbook()
    ws = wb.active
    ws.title = "Análisis"
    
    # Headers
    ws.append(["ID", "Fecha", "Agricultor", "Terreno", "Cultivo", "pH", "Nitrógeno", "Fósforo", "Potasio"])
    
    for a in analisis:
        ws.append([
            a.id,
            a.fecha_analisis.strftime('%d/%m/%Y %H:%M'),
            a.solicitud.agricultor.get_full_name() or a.solicitud.agricultor.username,
            a.solicitud.terreno.nombre,
            a.solicitud.cultivo_deseado,
            float(a.ph),
            float(a.nitrogeno),
            float(a.fosforo),
            float(a.potasio)
        ])
        
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    response = HttpResponse(buffer.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="reporte_analisis.xlsx"'
    return response

@login_required(login_url='login')
def gestion_cultivos_admin(request):
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'ADMIN':
        return redirect('home')
        
    from apps.ia_recomendaciones.models import CultivoIdeal
    cultivos = CultivoIdeal.objects.all().order_by('nombre')
    
    return render(request, 'admin/cultivos.html', {'cultivos': cultivos})

@login_required(login_url='login')
def guardar_cultivo_admin(request):
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'ADMIN':
        from django.http import JsonResponse
        return JsonResponse({'error': 'No autorizado'}, status=403)
        
    if request.method == 'POST':
        from django.http import JsonResponse
        from apps.ia_recomendaciones.models import CultivoIdeal
        import json
        
        try:
            data = json.loads(request.body)
            cultivo_id = data.get('id')
            
            # Crear o actualizar
            if cultivo_id:
                cultivo = CultivoIdeal.objects.get(id=cultivo_id)
            else:
                cultivo = CultivoIdeal()
                
            cultivo.nombre = data.get('nombre')
            cultivo.descripcion = data.get('descripcion', '')
            cultivo.humedad_min = float(data.get('humedad_min', 0))
            cultivo.humedad_max = float(data.get('humedad_max', 0))
            cultivo.temperatura_min = float(data.get('temperatura_min', 0))
            cultivo.temperatura_max = float(data.get('temperatura_max', 0))
            cultivo.conductividad_min = float(data.get('conductividad_min', 0))
            cultivo.conductividad_max = float(data.get('conductividad_max', 0))
            cultivo.ph_min = float(data.get('ph_min', 0))
            cultivo.ph_max = float(data.get('ph_max', 0))
            cultivo.nitrogeno_min = float(data.get('nitrogeno_min', 0))
            cultivo.nitrogeno_max = float(data.get('nitrogeno_max', 0))
            cultivo.fosforo_min = float(data.get('fosforo_min', 0))
            cultivo.fosforo_max = float(data.get('fosforo_max', 0))
            cultivo.potasio_min = float(data.get('potasio_min', 0))
            cultivo.potasio_max = float(data.get('potasio_max', 0))
            
            cultivo.save()
            return JsonResponse({'mensaje': 'Cultivo guardado correctamente'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
            
    from django.http import JsonResponse
    return JsonResponse({'error': 'Método no permitido'}, status=405)

@login_required(login_url='login')
def eliminar_cultivo_admin(request, cultivo_id):
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'ADMIN':
        from django.http import JsonResponse
        return JsonResponse({'error': 'No autorizado'}, status=403)
        
    if request.method == 'POST':
        from django.http import JsonResponse
        from apps.ia_recomendaciones.models import CultivoIdeal
        
        try:
            cultivo = CultivoIdeal.objects.get(id=cultivo_id)
            cultivo.delete()
            return JsonResponse({'mensaje': 'Cultivo eliminado permanentemente'})
        except CultivoIdeal.DoesNotExist:
            return JsonResponse({'error': 'Cultivo no encontrado'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
            
    from django.http import JsonResponse
    return JsonResponse({'error': 'Método no permitido'}, status=405)

@login_required(login_url='login')
def estado_hardware(request):
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'ADMIN':
        return redirect('home')
        
    from apps.sensores.models import LecturaSensor
    from django.utils import timezone
    from datetime import timedelta
    
    ultima_lectura = LecturaSensor.objects.order_by('-timestamp').first()
    
    estado_conexion = 'Inactivo'
    bateria = 85.0 # Mock de batería del sistema solar
    
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
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'ADMIN':
        return redirect('home')
        
    from apps.ia_recomendaciones.models import ConfiguracionGlobal
    import json
    from django.http import JsonResponse
    
    config = ConfiguracionGlobal.load()
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # IA
            config.tiempo_espera_ia = data.get('tiempo_espera_ia', config.tiempo_espera_ia)
            config.accion_fallo_ia = data.get('accion_fallo_ia', config.accion_fallo_ia)
            
            # Rangos
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
            
            config.save()
            return JsonResponse({'mensaje': 'Configuración guardada exitosamente'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
            
    return render(request, 'admin/configuracion.html', {'config': config})
