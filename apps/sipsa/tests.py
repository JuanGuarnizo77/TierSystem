"""
Tests unitarios para el módulo SIPSA/DANE.
Cubre el motor de predicción y las vistas principales.
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from datetime import date, timedelta

from .prediccion import calcular_prediccion, MIN_SEMANAS
from .models import CultivoSipsa, PrecioSemanal, PrediccionPrecio

User = get_user_model()


# ─── Tests del motor de predicción ─────────────────────────────────────────

class CalcularPrediccionTests(TestCase):

    def test_lista_vacia_retorna_estable(self):
        resultado = calcular_prediccion([])
        self.assertEqual(resultado['tendencia'], 'Estable')
        self.assertEqual(resultado['confianza_pct'], 0.0)
        self.assertEqual(resultado['semanas_usadas'], 0)

    def test_menos_de_min_semanas_retorna_estable(self):
        resultado = calcular_prediccion([1000, 1050])  # 2 puntos < MIN_SEMANAS=3
        self.assertEqual(resultado['tendencia'], 'Estable')
        self.assertEqual(resultado['confianza_pct'], 0.0)

    def test_serie_creciente_retorna_alza(self):
        # Serie claramente al alza
        precios = [1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700]
        resultado = calcular_prediccion(precios)
        self.assertEqual(resultado['tendencia'], 'Alza')
        self.assertGreater(resultado['variacion_pct'], 0)
        self.assertGreater(resultado['confianza_pct'], 0)

    def test_serie_decreciente_retorna_baja(self):
        # Serie claramente a la baja
        precios = [2000, 1900, 1800, 1700, 1600, 1500, 1400, 1300]
        resultado = calcular_prediccion(precios)
        self.assertEqual(resultado['tendencia'], 'Baja')
        self.assertLess(resultado['variacion_pct'], 0)

    def test_serie_plana_retorna_estable(self):
        # Serie plana — sin variación
        precios = [1500, 1500, 1500, 1500, 1500, 1500, 1500, 1500]
        resultado = calcular_prediccion(precios)
        self.assertEqual(resultado['tendencia'], 'Estable')
        self.assertAlmostEqual(resultado['variacion_pct'], 0.0, places=1)

    def test_confianza_maxima_con_8_semanas(self):
        precios = [1000] * 8
        resultado = calcular_prediccion(precios)
        self.assertEqual(resultado['confianza_pct'], 100.0)

    def test_precio_estimado_es_float(self):
        precios = [1000, 1050, 1100, 1150, 1200]
        resultado = calcular_prediccion(precios)
        self.assertIsInstance(resultado['precio_estimado'], float)

    def test_semanas_usadas_coincide_con_input(self):
        precios = [1000, 1050, 1100, 1150]
        resultado = calcular_prediccion(precios)
        self.assertEqual(resultado['semanas_usadas'], 4)


# ─── Tests de vistas ───────────────────────────────────────────────────────

class SipsaDashboardViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='agricultortest', password='pass1234')
        cls.cultivo = CultivoSipsa.objects.create(
            nombre='Papa Test', categoria='Tubérculos', unidad='kg', activo=True
        )
        hoy = date.today()
        lunes = hoy - timedelta(days=hoy.weekday())
        for i in range(8):
            semana = lunes - timedelta(weeks=7 - i)
            PrecioSemanal.objects.create(
                cultivo=cls.cultivo,
                fecha_semana=semana,
                semana_label=f'Sem {i + 1}',
                precio_kg=1000 + i * 50,
                precio_local=970 + i * 50,
            )
        PrediccionPrecio.objects.create(
            cultivo=cls.cultivo,
            tendencia_predicha='Alza',
            confianza_pct=100.0,
            precio_estimado=1400,
            variacion_estimada_pct=5.0,
            semanas_usadas=8,
        )

    def setUp(self):
        self.client = Client()
        self.client.login(username='agricultortest', password='pass1234')

    def test_dashboard_retorna_200(self):
        response = self.client.get('/agricultor/sipsa/')
        self.assertEqual(response.status_code, 200)

    def test_dashboard_contiene_cultivo(self):
        response = self.client.get('/agricultor/sipsa/')
        self.assertContains(response, 'Papa Test')

    def test_dashboard_redirige_sin_login(self):
        self.client.logout()
        response = self.client.get('/agricultor/sipsa/')
        self.assertIn(response.status_code, [302, 301])

    def test_detalle_cultivo_retorna_200(self):
        response = self.client.get(f'/agricultor/sipsa/cultivo/{self.cultivo.pk}/')
        self.assertEqual(response.status_code, 200)

    def test_detalle_cultivo_contiene_nombre(self):
        response = self.client.get(f'/agricultor/sipsa/cultivo/{self.cultivo.pk}/')
        self.assertContains(response, 'Papa Test')

    def test_actualizar_sin_superuser_redirige(self):
        """Un agricultor normal no puede disparar la actualización."""
        response = self.client.post('/agricultor/sipsa/actualizar/')
        # Debe redirigir (302) por user_passes_test, no devolver 200/500
        self.assertEqual(response.status_code, 302)
