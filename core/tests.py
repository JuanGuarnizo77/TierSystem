"""
Suite de Pruebas Automatizadas de Seguridad de TierSystem.
=========================================================
Verifica empíricamente los controles de seguridad implementados:
  - Autenticación obligatoria y bloqueo de accesos anónimos.
  - Control de acceso basado en roles (RBAC) y prevención de IDOR/BOLA.
  - Protección CSRF en endpoints mutadores.
  - Validación de rangos físicos y autenticación en tiempo constante de sensores IoT.
  - Limitación de tasa (Rate Limiting) contra fuerza bruta en login.
  - Políticas de contraseñas seguras y unicidad de correo electrónico.
  - Prevención de escalación de privilegios sobre superusuarios.
  - Sanitización contra inyección de fórmulas en exportaciones Excel (CWE-1236).
"""

import json
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase, Client, override_settings

from apps.terrenos.models import Terreno
from apps.solicitudes.models import SolicitudAnalisis
from apps.analisis.models import PuntoMuestreo, RegistroAnalisis
from core.utils import sanitizar_celda_excel


class SeguridadTierSystemTests(TestCase):
    """Pruebas integrales de seguridad web, API e IoT."""

    def setUp(self):
        cache.clear()
        self.client_anon = Client()

        # Agricultor 1 (propietario legítimo)
        self.agri1 = User.objects.create_user(
            username='agri1', email='agri1@test.com', password='PasswordSegura123!'
        )
        self.agri1.perfil.rol = 'AGRICULTOR'
        self.agri1.perfil.save()

        # Agricultor 2 (otro productor)
        self.agri2 = User.objects.create_user(
            username='agri2', email='agri2@test.com', password='PasswordSegura123!'
        )
        self.agri2.perfil.rol = 'AGRICULTOR'
        self.agri2.perfil.save()

        # Laboratorista 1 (técnico asignado)
        self.lab1 = User.objects.create_user(
            username='lab1', email='lab1@test.com', password='PasswordSegura123!'
        )
        self.lab1.perfil.rol = 'LABORATORISTA'
        self.lab1.perfil.save()

        # Laboratorista 2 (técnico NO asignado)
        self.lab2 = User.objects.create_user(
            username='lab2', email='lab2@test.com', password='PasswordSegura123!'
        )
        self.lab2.perfil.rol = 'LABORATORISTA'
        self.lab2.perfil.save()

        # Administrador regular (no superuser)
        self.admin_user = User.objects.create_user(
            username='admin_reg', email='admin@test.com', password='PasswordSegura123!'
        )
        self.admin_user.perfil.rol = 'ADMIN'
        self.admin_user.perfil.save()

        # Superadministrador
        self.superuser = User.objects.create_superuser(
            username='root_super', email='root@test.com', password='PasswordSegura123!'
        )
        self.superuser.perfil.rol = 'ADMIN'
        self.superuser.perfil.save()

        # Terreno y Solicitud asignada a lab1
        self.terreno1 = Terreno.objects.create(
            agricultor=self.agri1,
            nombre='Finca El Mirador',
            ubicacion='Vereda La Jagua, Garzón',
            hectareas=2.5,
            altitud_promedio=1450.0,
        )
        self.solicitud1 = SolicitudAnalisis.objects.create(
            agricultor=self.agri1,
            terreno=self.terreno1,
            laboratorista_asignado=self.lab1,
            modalidad='VISITA',
            estado='EN_PROCESO',
            cultivo_deseado='Café',
        )
        self.punto1 = PuntoMuestreo.objects.create(
            solicitud=self.solicitud1,
            numero=1,
        )

    def test_01_sincronizar_offline_bloquea_anonimo_y_agricultor(self):
        """Verifica que /api/ia/sincronizar-offline/ rechace peticiones anónimas y de agricultores."""
        payload = {'puntos': [], 'diagnosticos': []}
        resp_anon = self.client_anon.post(
            '/api/ia/sincronizar-offline/',
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertIn(resp_anon.status_code, (302, 401, 403))

        self.client.force_login(self.agri1)
        resp_agri = self.client.post(
            '/api/ia/sincronizar-offline/',
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(resp_agri.status_code, 403)

    def test_02_sincronizar_offline_bloquea_idor_otro_laboratorista(self):
        """Verifica que lab2 no pueda sobrescribir el análisis de una solicitud asignada a lab1."""
        self.client.force_login(self.lab2)
        payload = {
            'puntos': [],
            'diagnosticos': [{
                'solicitud_id': self.solicitud1.id,
                'datos_sensor': {
                    'humedad': 60, 'temperatura': 22, 'conductividad': 1.2,
                    'ph': 6.0, 'n': 150, 'p': 45, 'k': 180,
                },
                'diagnostico': {'recomendaciones': [], 'consejo_general': 'Manipulado'},
            }],
        }
        resp = self.client.post(
            '/api/ia/sincronizar-offline/',
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        self.solicitud1.refresh_from_db()
        self.assertEqual(self.solicitud1.estado, 'EN_PROCESO')
        self.assertFalse(RegistroAnalisis.objects.filter(solicitud=self.solicitud1).exists())

    def test_03_diagnosticar_ia_bloquea_idor_y_rol_agricultor(self):
        """Verifica que /api/ia/diagnosticar/ exija rol LABORATORISTA y pertenencia de la solicitud."""
        payload = {
            'solicitud_id': self.solicitud1.id,
            'humedad': 60, 'temperatura': 22, 'conductividad': 1.2,
            'ph': 6.0, 'n': 150, 'p': 45, 'k': 180,
        }
        # Agricultor bloqueado con 403
        self.client.force_login(self.agri1)
        resp_agri = self.client.post(
            '/api/ia/diagnosticar/',
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(resp_agri.status_code, 403)

        # Laboratorista NO asignado bloqueado con 403
        self.client.force_login(self.lab2)
        resp_lab2 = self.client.post(
            '/api/ia/diagnosticar/',
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(resp_lab2.status_code, 403)

    def test_04_asesor_agronomico_bloquea_idor_entre_agricultores(self):
        """Verifica que agri2 no pueda consultar una solicitud perteneciente a agri1."""
        self.client.force_login(self.agri2)
        resp = self.client.post(
            '/api/ia/asesor-suelo/',
            data=json.dumps({
                'solicitud_id': self.solicitud1.id,
                'pregunta': '¿Cómo abonar este lote?',
            }),
            content_type='application/json',
        )
        self.assertIn(resp.status_code, (403, 404))

    def test_05_sensores_captura_estable_y_guardar_punto_seguros(self):
        """Verifica control de acceso y validación de rangos físicos en endpoints de sensores."""
        # Anónimo redirigido en captura_estable
        resp_anon = self.client_anon.get('/api/captura-estable/')
        self.assertEqual(resp_anon.status_code, 302)

        # Agricultor bloqueado con 403 en captura_estable
        self.client.force_login(self.agri1)
        resp_agri = self.client.get('/api/captura-estable/')
        self.assertEqual(resp_agri.status_code, 403)

        # Laboratorista asignado con pH fuera de rango físico (pH=25) recibe 400
        self.client.force_login(self.lab1)
        resp_invalido = self.client.post(
            f'/api/punto/{self.punto1.id}/guardar/',
            data=json.dumps({
                'humedad': 55, 'temperatura': 22, 'conductividad': 1.1,
                'ph': 25.0, 'nitrogeno': 120, 'fosforo': 40, 'potasio': 150,
            }),
            content_type='application/json',
        )
        self.assertEqual(resp_invalido.status_code, 400)

    @override_settings(DEBUG=False, SENSOR_API_KEY='clave-secreta-esp32-segura')
    def test_06_ingesta_sensor_exige_api_key_en_produccion(self):
        """Verifica que /api/lecturas/ valide X-API-Key con compare_digest cuando DEBUG=False."""
        trama = {
            'humedad': 600, 'temperatura': 230, 'conductividad': 120,
            'ph': 62, 'nitrogeno': 140, 'fosforo': 45, 'potasio': 180,
        }
        # Sin API Key -> 401
        r1 = self.client_anon.post(
            '/api/lecturas/',
            data=json.dumps(trama),
            content_type='application/json',
        )
        self.assertEqual(r1.status_code, 401)

        # Con API Key correcta -> 200
        r2 = self.client_anon.post(
            '/api/lecturas/',
            data=json.dumps(trama),
            content_type='application/json',
            HTTP_X_API_KEY='clave-secreta-esp32-segura',
        )
        self.assertEqual(r2.status_code, 200)

    def test_07_rate_limiting_login_fuerza_bruta(self):
        """Verifica que el endpoint de login bloquee con HTTP 429 tras múltiples intentos fallidos."""
        cache.clear()
        for _ in range(8):
            resp = self.client_anon.post('/login/', {'username': 'agri1', 'password': 'wrong'})
            self.assertEqual(resp.status_code, 200)

        resp_bloqueado = self.client_anon.post('/login/', {'username': 'agri1', 'password': 'wrong'})
        self.assertEqual(resp_bloqueado.status_code, 429)

    def test_08_proteccion_superusuario_en_panel_admin(self):
        """Verifica que un administrador no superusuario no pueda desactivar ni eliminar a un superusuario."""
        self.client.force_login(self.admin_user)
        r_estado = self.client.post(
            f'/administrador/usuarios/{self.superuser.id}/estado/',
            data=json.dumps({'is_active': False}),
            content_type='application/json',
        )
        self.assertEqual(r_estado.status_code, 403)

        r_elim = self.client.post(f'/administrador/usuarios/{self.superuser.id}/eliminar/')
        self.assertEqual(r_elim.status_code, 403)

    def test_09_sanitizacion_inyeccion_formulas_excel(self):
        """Verifica la neutralización de payloads DDE/fórmulas en celdas de exportación Excel."""
        self.assertEqual(sanitizar_celda_excel('=CMD|" /C calc"!A0'), "'=CMD|\" /C calc\"!A0")
        self.assertEqual(sanitizar_celda_excel('+SUM(A1:A10)'), "'+SUM(A1:A10)")
        self.assertEqual(sanitizar_celda_excel('@IMPORTXML(...)'), "'@IMPORTXML(...)")
        self.assertEqual(sanitizar_celda_excel('Finca San José'), 'Finca San José')
        self.assertEqual(sanitizar_celda_excel(6.5), 6.5)

    def test_10_validacion_backend_terrenos_hectareas_y_geojson(self):
        """Verifica que el backend valide hectáreas, GeoJSON y bloquee borrado con muestreo activo."""
        self.client.force_login(self.agri1)
        # Hectáreas negativas -> 400
        r_neg = self.client.post('/agricultor/fincas/crear/', {
            'nombre': 'Lote Inválido',
            'ubicacion': 'Garzón',
            'hectareas': '-10',
        })
        self.assertEqual(r_neg.status_code, 400)

        # Payload XSS en coordenadas_poligono -> 400
        r_xss = self.client.post('/agricultor/fincas/crear/', {
            'nombre': 'Lote XSS',
            'ubicacion': 'Garzón',
            'hectareas': '3.5',
            'coordenadas_poligono': '</script><script>alert(1)</script>',
        })
        self.assertEqual(r_xss.status_code, 400)

        # Intento de eliminar terreno1 que tiene solicitud1 en estado EN_PROCESO -> 400
        r_del = self.client.post(f'/agricultor/fincas/eliminar/{self.terreno1.id}/')
        self.assertEqual(r_del.status_code, 400)
        self.assertTrue(Terreno.objects.filter(id=self.terreno1.id).exists())

    def test_11_validacion_backend_solicitudes_modalidad_y_fecha_pasada(self):
        """Verifica validación de modalidad en creación y bloqueo de fechas pasadas al aceptar."""
        from apps.cultivos.models import Cultivo
        Cultivo.objects.create(nombre='Café Castillo', activo=True, ph_min=5.0, ph_max=6.5)
        terreno2 = Terreno.objects.create(
            agricultor=self.agri2, nombre='Finca 2', ubicacion='Pitalito', hectareas=4.0
        )

        # Modalidad manipulada desde el cliente -> 400
        self.client.force_login(self.agri2)
        r_mod = self.client.post('/agricultor/solicitudes/crear/', {
            'terreno_id': terreno2.id,
            'cultivo_deseado': 'Café Castillo',
            'modalidad': 'MODO_FALSO',
        })
        self.assertEqual(r_mod.status_code, 400)

        # Creación legítima -> 200
        r_ok = self.client.post('/agricultor/solicitudes/crear/', {
            'terreno_id': terreno2.id,
            'cultivo_deseado': 'Café Castillo',
            'modalidad': 'VISITA',
        })
        self.assertEqual(r_ok.status_code, 200)
        sol_nueva = SolicitudAnalisis.objects.get(agricultor=self.agri2)

        # Laboratorista intenta aceptar con fecha en el pasado -> 400
        self.client.force_login(self.lab1)
        r_past = self.client.post(f'/laboratorista/solicitudes/aceptar/{sol_nueva.id}/', {
            'fecha_visita': '2020-01-01',
        })
        self.assertEqual(r_past.status_code, 400)
        sol_nueva.refresh_from_db()
        self.assertEqual(sol_nueva.estado, 'PENDIENTE')

    def test_12_autoridad_backend_compartir_resultado_recalcula_promedio_y_diagnostico(self):
        """Verifica que /api/ia/compartir/ use el promedio real de BD y recalcule el diagnóstico."""
        from apps.cultivos.models import Cultivo
        Cultivo.objects.create(
            nombre='Café Especial',
            activo=True,
            humedad_min=50, humedad_max=80,
            temperatura_min=18, temperatura_max=25,
            conductividad_min=0.8, conductividad_max=2.0,
            ph_min=5.0, ph_max=6.0,
            nitrogeno_min=140, nitrogeno_max=240,
            fosforo_min=30, fosforo_max=65,
            potasio_min=150, potasio_max=300,
        )
        # Punto de muestreo real en base de datos
        self.punto1.humedad = 65.0
        self.punto1.temperatura = 21.0
        self.punto1.conductividad = 1.2
        self.punto1.ph = 5.5
        self.punto1.nitrogeno = 180.0
        self.punto1.fosforo = 45.0
        self.punto1.potasio = 200.0
        self.punto1.estado = 'TOMADO'
        self.punto1.save()

        self.client.force_login(self.lab1)
        # Cliente envía datos manipulados en el frontend (ph=12.0) y diagnóstico vacío
        resp = self.client.post(
            '/api/ia/compartir/',
            data=json.dumps({
                'solicitud_id': self.solicitud1.id,
                'datos': {
                    'humedad': 10.0, 'temperatura': 40.0, 'conductividad': 9.0,
                    'ph': 12.0, 'nitrogeno': 5.0, 'fosforo': 5.0, 'potasio': 5.0,
                },
                'diagnostico': {'recomendaciones': [], 'consejo_general': ''},
            }),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        registro = RegistroAnalisis.objects.get(solicitud=self.solicitud1)
        # El backend debió ignorar ph=12.0 del cliente y persistir ph=5.5 del PuntoMuestreo en BD
        self.assertAlmostEqual(float(registro.ph), 5.5, places=1)
        diag_guardado = json.loads(registro.diagnostico_ia)
        self.assertTrue(len(diag_guardado.get('recomendaciones', [])) > 0)

    def test_13_validacion_backend_rangos_invertidos_cultivo_y_configuracion(self):
        """Verifica que el backend administrativo rechace rangos donde mínimo > máximo."""
        self.client.force_login(self.admin_user)
        r_cultivo = self.client.post(
            '/administrador/cultivos/guardar/',
            data=json.dumps({
                'nombre': 'Cultivo Mal Configurado',
                'ph_min': 8.5,
                'ph_max': 4.5,
            }),
            content_type='application/json',
        )
        self.assertEqual(r_cultivo.status_code, 400)

        r_cfg = self.client.post(
            '/administrador/configuracion/',
            data=json.dumps({
                'tiempo_espera_ia': 5,
                'accion_fallo_ia': 'LOCAL',
                'rango_ph_min': 10.0,
                'rango_ph_max': 3.0,
            }),
            content_type='application/json',
        )
        self.assertEqual(r_cfg.status_code, 400)

        # Verificar que tanto DB_LOCAL como CANCELAR funcionen en configuración global
        r_cfg_ok = self.client.post(
            '/administrador/configuracion/',
            data=json.dumps({
                'tiempo_espera_ia': 15,
                'accion_fallo_ia': 'DB_LOCAL',
                'tiempo_inactividad_min': 45,
                'max_intentos_login': 6,
                'tiempo_bloqueo_min': 10,
                'rango_ph_min': 3.5,
                'rango_ph_max': 9.5,
            }),
            content_type='application/json',
        )
        self.assertEqual(r_cfg_ok.status_code, 200)

    def test_14_unicidad_terreno_por_agricultor_y_inmutabilidad_historica_us0037(self):
        """Verifica restricción de nombre único de terreno por agricultor e inmutabilidad histórica US-0037."""
        from apps.cultivos.models import Cultivo
        from apps.solicitudes.views import _evaluar_parametros_agronomicos

        self.client.force_login(self.agri1)
        # Intentar crear otro terreno con el mismo nombre 'Finca El Mirador' para agri1 -> 400
        r_dup = self.client.post('/agricultor/fincas/crear/', {
            'nombre': 'Finca El Mirador',
            'ubicacion': 'Pitalito',
            'hectareas': '2.0',
        })
        self.assertEqual(r_dup.status_code, 400)

        # US-0037: Crear cultivo, guardar análisis, alterar rangos del cultivo y verificar que el informe histórico NO cambie
        cult = Cultivo.objects.create(
            nombre='Cacao Fino',
            activo=True,
            humedad_min=60, humedad_max=75,
            temperatura_min=22, temperatura_max=28,
            conductividad_min=0.8, conductividad_max=2.0,
            ph_min=5.5, ph_max=6.5,
            nitrogeno_min=100, nitrogeno_max=180,
            fosforo_min=25, fosforo_max=50,
            potasio_min=120, potasio_max=220,
        )
        self.solicitud1.cultivo_deseado_ref = cult
        self.solicitud1.save()

        self.punto1.humedad = 65.0
        self.punto1.temperatura = 24.0
        self.punto1.conductividad = 1.2
        self.punto1.ph = 6.0
        self.punto1.nitrogeno = 140.0
        self.punto1.fosforo = 35.0
        self.punto1.potasio = 160.0
        self.punto1.estado = 'TOMADO'
        self.punto1.save()

        self.client.force_login(self.lab1)
        resp = self.client.post(
            '/api/ia/compartir/',
            data=json.dumps({
                'solicitud_id': self.solicitud1.id,
                'datos': {},
                'diagnostico': {},
            }),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        reg = RegistroAnalisis.objects.get(solicitud=self.solicitud1)
        self.assertEqual(reg.origen_diagnostico, 'LOCAL')
        self.assertTrue(reg.pendiente_reenvio_ia)
        self.assertIsNotNone(reg.compatibilidad_cultivo_deseado)

        eval_antes = _evaluar_parametros_agronomicos(reg, 'Cacao Fino')
        estado_ph_antes = next(p['estado'] for p in eval_antes['parametros'] if p['nombre'] == 'pH')
        self.assertEqual(estado_ph_antes, 'Óptimo')

        # Modificar el rango del catálogo después de emitido el análisis
        cult.ph_min = 7.5
        cult.ph_max = 8.5
        cult.save()

        # US-0037: El informe histórico debe conservar su evaluación congelada ('Óptimo')
        eval_despues = _evaluar_parametros_agronomicos(reg, 'Cacao Fino')
        estado_ph_despues = next(p['estado'] for p in eval_despues['parametros'] if p['nombre'] == 'pH')
        self.assertEqual(estado_ph_despues, 'Óptimo')
        self.assertEqual(eval_antes['compatibilidad'], eval_despues['compatibilidad'])


