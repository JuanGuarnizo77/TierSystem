"""
Batería de Pruebas Unitarias para el Módulo SIPSA / DANE.
=========================================================
Valida la integridad y robustez matemática y funcional de:
  1. Motor de proyección y análisis de tendencias de precios mayoristas (`calcular_prediccion`):
      - Manejo seguro de series temporales vacías o con datos insuficientes (< MIN_SEMANAS).
      - Identificación precisa de tendencias al 'Alza', 'Baja' y 'Estable'.
      - Coeficiente de confianza proporcional al historial disponible (hasta 8 semanas).
      - Tipado y consistencia de los datos numéricos de salida.
  2. Vistas y controladores web del módulo SIPSA:
      - Código de estado HTTP 200 en tablero del productor (`SipsaDashboardViewTest`).
      - Renderizado correcto del nombre de cultivo y precios históricos.
      - Restricciones de seguridad y redirección ante solicitudes no autenticadas (HTTP 302).
      - Protección del endpoint administrativo de actualización para evitar accesos de usuarios comunes.
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from datetime import date, timedelta

from .prediccion import calcular_prediccion, MIN_SEMANAS
from .models import PrecioSemanal
from apps.cultivos.models import Cultivo

# Modelo de usuario activo configurado en Django
User = get_user_model()


# =============================================================================
# PRUEBAS DEL MOTOR MATEMÁTICO DE PREDICCIÓN Y TENDENCIA
# =============================================================================

class CalcularPrediccionTests(TestCase):
    """
    Casos de prueba para la función pura `calcular_prediccion`.

    Verifica el comportamiento algorítmico ante distintos escenarios de series de tiempo.
    """

    def test_lista_vacia_retorna_estable(self):
        """
        Una serie sin registros debe retornar una tendencia neutra ('Estable')
        con confianza 0.0% y 0 semanas utilizadas, sin generar excepciones matemáticas.
        """
        resultado = calcular_prediccion([])
        self.assertEqual(resultado['tendencia'], 'Estable')
        self.assertEqual(resultado['confianza_pct'], 0.0)
        self.assertEqual(resultado['semanas_usadas'], 0)

    def test_menos_de_min_semanas_retorna_estable(self):
        """
        Si la cantidad de semanas es inferior a MIN_SEMANAS (3), no se puede calcular
        una regresión confiable y debe retornar 'Estable' con confianza 0.0%.
        """
        resultado = calcular_prediccion([1000, 1050])  # 2 puntos < MIN_SEMANAS=3
        self.assertEqual(resultado['tendencia'], 'Estable')
        self.assertEqual(resultado['confianza_pct'], 0.0)

    def test_serie_creciente_retorna_alza(self):
        """
        Una serie de precios estrictamente creciente debe clasificarse como 'Alza'
        con una variación porcentual estrictamente positiva y confianza mayor a cero.
        """
        precios = [1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700]
        resultado = calcular_prediccion(precios)
        self.assertEqual(resultado['tendencia'], 'Alza')
        self.assertGreater(resultado['variacion_pct'], 0)
        self.assertGreater(resultado['confianza_pct'], 0)

    def test_serie_decreciente_retorna_baja(self):
        """
        Una serie de precios en descenso sostenido debe clasificarse como 'Baja'
        con una tasa de variación negativa.
        """
        precios = [2000, 1900, 1800, 1700, 1600, 1500, 1400, 1300]
        resultado = calcular_prediccion(precios)
        self.assertEqual(resultado['tendencia'], 'Baja')
        self.assertLess(resultado['variacion_pct'], 0)

    def test_serie_plana_retorna_estable(self):
        """
        Una serie con precios invariables en el tiempo debe arrojar tendencia 'Estable'
        y una variación porcentual de cero.
        """
        precios = [1500, 1500, 1500, 1500, 1500, 1500, 1500, 1500]
        resultado = calcular_prediccion(precios)
        self.assertEqual(resultado['tendencia'], 'Estable')
        self.assertAlmostEqual(resultado['variacion_pct'], 0.0, places=1)

    def test_confianza_maxima_con_8_semanas(self):
        """
        Al suministrar el histórico completo de 8 semanas, el indicador de confiabilidad
        estadística debe alcanzar el 100.0%.
        """
        precios = [1000] * 8
        resultado = calcular_prediccion(precios)
        self.assertEqual(resultado['confianza_pct'], 100.0)

    def test_precio_estimado_es_float(self):
        """
        El valor proyectado del precio para la semana entrante debe ser de tipo numérico flotante.
        """
        precios = [1000, 1050, 1100, 1150, 1200]
        resultado = calcular_prediccion(precios)
        self.assertIsInstance(resultado['precio_estimado'], float)

    def test_semanas_usadas_coincide_con_input(self):
        """
        El campo `semanas_usadas` debe reflejar con exactitud el tamaño de la muestra suministrada.
        """
        precios = [1000, 1050, 1100, 1150]
        resultado = calcular_prediccion(precios)
        self.assertEqual(resultado['semanas_usadas'], 4)


# =============================================================================
# PRUEBAS DE VISTAS Y CONTROLADORES SIPSA
# =============================================================================

class SipsaDashboardViewTest(TestCase):
    """
    Pruebas de integración HTTP sobre las vistas de monitor de precios de mercado SIPSA.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Configuración de datos compartidos para los casos de prueba:
          - Usuario de pruebas con rol agricultor.
          - Especie agrícola con 8 semanas de precios registrados en Neiva / Surabastos.
        """
        cls.user = User.objects.create_user(username='agricultortest', password='pass1234')
        cls.cultivo = Cultivo.objects.create(
            nombre='Papa Test',
            categoria='Tubérculos',
            activo=True
        )

        # Generar histórico semanal ficticio pero continuo
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

    def setUp(self):
        """Inicializa el cliente de pruebas simulando la sesión del usuario agricultor."""
        self.client = Client()
        self.client.login(username='agricultortest', password='pass1234')

    def test_dashboard_retorna_200(self):
        """La vista general del tablero de precios debe responder exitosamente con código 200."""
        response = self.client.get('/agricultor/sipsa/')
        self.assertEqual(response.status_code, 200)

    def test_dashboard_contiene_cultivo(self):
        """El cuerpo HTML debe contener el nombre de las especies monitoreadas ('Papa Test')."""
        response = self.client.get('/agricultor/sipsa/')
        self.assertContains(response, 'Papa Test')

    def test_dashboard_redirige_sin_login(self):
        """Un usuario sin sesión activa debe ser redirigido a la pantalla de inicio de sesión."""
        self.client.logout()
        response = self.client.get('/agricultor/sipsa/')
        self.assertIn(response.status_code, [302, 301])

    def test_detalle_cultivo_retorna_200(self):
        """La ficha analítica detallada de una especie debe cargar con código HTTP 200."""
        response = self.client.get(f'/agricultor/sipsa/cultivo/{self.cultivo.pk}/')
        self.assertEqual(response.status_code, 200)

    def test_detalle_cultivo_contiene_nombre(self):
        """La vista de detalle debe incluir la denominación del cultivo consultado."""
        response = self.client.get(f'/agricultor/sipsa/cultivo/{self.cultivo.pk}/')
        self.assertContains(response, 'Papa Test')

    def test_actualizar_sin_superuser_redirige(self):
        """
        Un productor agrícola sin permisos de superusuario no puede ejecutar el proceso
        de ingestión o sincronización directa desde el DANE (debe ser redirigido).
        """
        response = self.client.post('/agricultor/sipsa/actualizar/')
        self.assertEqual(response.status_code, 302)
