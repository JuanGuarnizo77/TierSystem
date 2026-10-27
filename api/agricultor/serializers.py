"""
Serializadores del Portal Móvil del Agricultor - TierSystem API.
Gestiona la validación e inserción de predios/fincas y órdenes de análisis de suelo,
garantizando la integridad relacional con el catálogo de cultivos de Huila
y el aislamiento de datos por usuario autenticado.
"""

from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers

from apps.cultivos.models import Cultivo
from apps.terrenos.models import Terreno
from apps.solicitudes.models import SolicitudAnalisis


def _validar_cultivo(value):
    """
    Función utilitaria de validación polimórfica para cultivos.
    Permite tanto el identificador primario numérico (ID) como el nombre textual del cultivo.
    Comprueba su existencia en la tabla maestra cultivos_cultivo.
    Si el valor es nulo o vacío, lo permite para lotes en preparación o descanso.
    """
    value = str(value or '').strip()
    if not value:
        return value
    if value.isdigit():
        # Búsqueda por clave primaria directa
        existe = Cultivo.objects.filter(id=int(value)).exists()
    else:
        # Búsqueda insensible a mayúsculas sobre la columna de nombre
        existe = Cultivo.objects.filter(nombre__icontains=value).exists()
    if not existe:
        raise serializers.ValidationError("El cultivo ingresado no existe en el catálogo oficial de Huila.")
    return value


class TerrenoSerializer(serializers.ModelSerializer):
    """
    Serializador para el registro y consulta de predios agrícolas (Fincas).
    Valida extensión en hectáreas, coordenadas GeoJSON del polígono y cultivo sembrado.
    """
    # Campo virtual gestionado a través del getter/setter del modelo Terreno
    cultivo_principal = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )

    class Meta:
        model = Terreno
        fields = [
            'id', 'nombre', 'ubicacion', 'hectareas',
            'cultivo_principal', 'coordenadas_poligono', 'fecha_registro',
        ]
        read_only_fields = ['id', 'fecha_registro']

    def validate_hectareas(self, value):
        """Regla de validación física: el área del predio debe ser estrictamente positiva."""
        if value <= 0:
            raise serializers.ValidationError("Las hectáreas deben ser un valor mayor a cero.")
        return value

    def validate_cultivo_principal(self, value):
        """Valida que el cultivo principal exista en el catálogo de cultivos."""
        return _validar_cultivo(value)


class SolicitudSerializer(serializers.ModelSerializer):
    """
    Serializador para la radicación y seguimiento de solicitudes de análisis de suelo.
    Restringe las fincas elegibles únicamente a las pertenecientes al agricultor en sesión
    y serializa el diagnóstico emitido por el motor agronómico si ya fue completado.
    """
    # Inicializa el campo con un QuerySet vacío que se poblará dinámicamente según el usuario
    terreno = serializers.PrimaryKeyRelatedField(queryset=Terreno.objects.none())
    # Nombre visible del predio para la interfaz móvil
    terreno_nombre = serializers.CharField(source='terreno.nombre', read_only=True)
    cultivo_deseado = serializers.CharField()
    # Traducción legible de los choices de Django
    estado_texto = serializers.CharField(source='get_estado_display', read_only=True)
    modalidad_texto = serializers.CharField(source='get_modalidad_display', read_only=True)
    # Extrae el informe final de RegistroAnalisis a través de la relación OneToOneField
    diagnostico_ia = serializers.SerializerMethodField()

    class Meta:
        model = SolicitudAnalisis
        fields = [
            'id', 'terreno', 'terreno_nombre', 'cultivo_deseado',
            'modalidad', 'modalidad_texto', 'notas_agricultor',
            'estado', 'estado_texto', 'fecha_solicitud', 'fecha_visita',
            'diagnostico_ia',
        ]
        read_only_fields = ['id', 'estado', 'fecha_solicitud', 'fecha_visita']

    def __init__(self, *args, **kwargs):
        """
        Sobrescribe la inicialización para filtrar las opciones del desplegable de terrenos:
        Garantiza que un agricultor no pueda solicitar análisis sobre predios ajenos.
        """
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            self.fields['terreno'].queryset = Terreno.objects.filter(agricultor=request.user)

    def get_diagnostico_ia(self, obj):
        """Recupera el texto o JSON del informe agronómico definitivo si el análisis ya concluyó."""
        try:
            return obj.analisis_resultado.diagnostico_ia
        except ObjectDoesNotExist:
            return None

    def validate_cultivo_deseado(self, value):
        """Valida que el cultivo proyectado por el productor exista en el catálogo."""
        return _validar_cultivo(value)

    def validate_terreno(self, value):
        """Comprobación estricta de propiedad del lote respecto al usuario en sesión."""
        request = self.context.get('request')
        if request and value.agricultor_id != request.user.id:
            raise serializers.ValidationError("El terreno seleccionado no es válido o no te pertenece.")
        return value