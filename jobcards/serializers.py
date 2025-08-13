# serializers.py
from rest_framework import serializers
from .models import JobCard, ManpowerBase, ToolsBase, MaterialBase

class JobCardSerializer(serializers.ModelSerializer):
    pdf_name = serializers.SerializerMethodField()

    def get_pdf_name(self, obj):
        if hasattr(obj, 'pdf_file') and obj.pdf_file:
            return obj.pdf_file.name.split('/')[-1]
        if obj.job_card_number and hasattr(obj, 'rev'):
            return f"JobCard_{obj.job_card_number}_Rev_{obj.rev}.pdf"
        if obj.job_card_number:
            return f"{obj.job_card_number}.pdf"
        return None

    class Meta:
        model = JobCard
        fields = '__all__'
