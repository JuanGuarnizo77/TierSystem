from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers

from apps.cultivos.models import Cultivo
from apps.terrenos.models import Terreno
from apps.solicitudes.models import SolicitudAnalisis


def _validar_cultivo(value):
    """Acepta ID numérico o nombre. Vacío se permite (queda sin cultivo)."""
    value = str(value or '').strip()
    if not value:
        return value
    if value.isdigit():
        existe = Cultivo.objects.filter(id=int(value)).exists()
    else:
        existe = Cultivo.objects.filter(nombre__icontains=value).exists()
    if not existe:
        raise serializers.ValidationError("El cultivo no existe en el catálogo.")
    return value


class TerrenoSerializer(serializers.ModelSerializer):
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
        if value <= 0:
            raise serializers.ValidationError("Las hectáreas deben ser mayores a 0.")
        return value

    def validate_cultivo_principal(self, value):
        return _validar_cultivo(value)


class SolicitudSerializer(serializers.ModelSerializer):
    terreno = serializers.PrimaryKeyRelatedField(queryset=Terreno.objects.none())
    terreno_nombre = serializers.CharField(source='terreno.nombre', read_only=True)
    cultivo_deseado = serializers.CharField()
    estado_texto = serializers.CharField(source='get_estado_display', read_only=True)
    modalidad_texto = serializers.CharField(source='get_modalidad_display', read_only=True)
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
        super().__init__(*args, **kwargs)
        # Filtra el queryset de terrenos para permitir solo fincas del agricultor autenticado
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            self.fields['terreno'].queryset = Terreno.objects.filter(agricultor=request.user)

    def get_diagnostico_ia(self, obj):
        try:
            return obj.analisis_resultado.diagnostico_ia
        except ObjectDoesNotExist:
            return None

    def validate_cultivo_deseado(self, value):
        return _validar_cultivo(value)

    def validate_terreno(self, value):
        request = self.context.get('request')
        if request and value.agricultor_id != request.user.id:
            raise serializers.ValidationError("El terreno seleccionado no es válido o no te pertenece.")
        return value