from rest_framework import serializers
from resident_profiling_module.models import Resident

class ResidentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resident
        fields = '__all__'
