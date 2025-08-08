# serializers.py
from rest_framework import serializers
from .models import JobCard, ManpowerBase, ToolsBase, MaterialBase

class JobCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobCard
        fields = '__all__'

class ManpowerBaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManpowerBase
        fields = '__all__'

