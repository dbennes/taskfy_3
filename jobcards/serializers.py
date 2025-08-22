# serializers.py
from rest_framework import serializers
from .models import AllocatedManpower, DailyFieldReport, JobCard, ManpowerBase, TaskBase, ToolsBase, MaterialBase
from .models import Impediments

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

class ImpedimentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Impediments
        fields = '__all__'

class AllocatedManpowerSerializer(serializers.ModelSerializer):
    class Meta:
        model = AllocatedManpower
        fields = '__all__'

class AllocatedManpowerSerializer(serializers.ModelSerializer):
    jobcard_number = serializers.CharField(source="jobcard.job_card_number", read_only=True)
    task_description = serializers.SerializerMethodField()

    class Meta:
        model = AllocatedManpower
        fields = [
            "jobcard_number",
            "discipline",
            "working_code",
            "direct_labor",
            "qty",
            "hours",
            "task_order",
            "task_description",
        ]

    def get_task_description(self, obj):
        try:
            # 1) pegar o JobCard dessa manpower
            job = JobCard.objects.get(job_card_number=obj.jobcard_number)

            # 2) procurar TaskBase com mesmo working_code e order
            task = TaskBase.objects.filter(
                working_code=job.working_code,
                order=obj.task_order
            ).first()

            return task.typical_task if task else None
        except JobCard.DoesNotExist:
            return None
        

class DFRLineReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyFieldReport
        fields = [
            "id", "dfr_number", "line_seq",
            "jobcard_number", "discipline", "working_code",
            "report_date", "total_hours", "total_lines",
            "created_by", "created_at", "notes",
            "task_description", "task_order", "direct_labor",
            "hours", "qty", "source",
        ]

class DFRCreatedSummarySerializer(serializers.Serializer):
    dfr_number = serializers.CharField()
    report_date = serializers.DateField()
    jobcard_number = serializers.CharField()
    total_hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_lines = serializers.IntegerField()