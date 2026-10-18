from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers

from apps.terrenos.models import Terreno
from apps.solicitudes.models import SolicitudAnalisis


class TerrenoSerializer(serializers.ModelSerializer):
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


class SolicitudSerializer(serializers.ModelSerializer):
    terreno = serializers.PrimaryKeyRelatedField(queryset=Terreno.objects.none())
    terreno_nombre = serializers.CharField(source='terreno.nombre', read_only=True)
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

    def validate_terreno(self, value):
        request = self.context.get('request')
        if request and value.agricultor_id != request.user.id:
            raise serializers.ValidationError("El terreno seleccionado no es válido o no te pertenece.")
        return value
