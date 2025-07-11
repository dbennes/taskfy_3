from django.db import models


class JobCard(models.Model):
    item = models.IntegerField()
    seq_number = models.CharField(max_length=10)
    discipline = models.CharField(max_length=50)
    discipline_code = models.CharField(max_length=10)
    location = models.CharField(max_length=20)
    level = models.CharField(max_length=10)
    activity_id = models.CharField(max_length=50)
    start = models.DateField(null=True, blank=True)
    finish = models.DateField(null=True, blank=True)
    system = models.CharField(max_length=20)
    subsystem = models.CharField(max_length=20)
    workpack_number = models.CharField(max_length=20)
    working_code = models.CharField(max_length=20)
    tag = models.CharField(max_length=50)
    working_code_description = models.TextField()
    job_card_number = models.CharField(max_length=50)
    rev = models.CharField(max_length=10, blank=True, null=True,)
    jobcard_status = models.CharField(max_length=50)
    job_card_description = models.TextField()
    completed = models.CharField(max_length=10)  # Pode virar BooleanField com tratamento
    total_weight = models.CharField(max_length=30)  # Se for número, trocar para FloatField
    unit = models.CharField(max_length=20, blank=True)
    total_duration_hs = models.CharField(max_length=30,null=True, blank=True)  # Se for número, usar FloatField
    indice_kpi = models.CharField(max_length=30,null=True, blank=True)
    total_man_hours = models.CharField(max_length=30, null=True, blank=True)
    prepared_by = models.CharField(max_length=100)
    date_prepared = models.DateField(null=True, blank=True)
    approved_br = models.CharField(max_length=50, null=True, blank=True)
    date_approved = models.DateField(null=True, blank=True)
    hot_work_required = models.CharField(max_length=10,null=True, blank=True)
    status = models.CharField(max_length=50, blank=True, null=True,)
    comments = models.TextField(blank=True, null=True,)
    last_modified_by = models.CharField(max_length=150, blank=True, null=True)
    last_modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.job_card_number} - {self.activity_id}"
    
class ManpowerBase(models.Model):
    item = models.IntegerField()
    discipline = models.CharField(max_length=100)
    working_code = models.CharField(max_length=20)
    working_description = models.TextField()
    direct_labor = models.CharField(max_length=100)
    qty = models.FloatField()

    def __str__(self):
        return f"{self.item} - {self.working_code} - {self.direct_labor}"
    
class ToolsBase(models.Model):
    item = models.IntegerField()
    discipline = models.CharField(max_length=100)
    working_code = models.CharField(max_length=50)
    direct_labor = models.CharField(max_length=100)
    qty_direct_labor = models.FloatField()
    special_tooling = models.CharField(max_length=255)
    qty = models.FloatField()

    def __str__(self):
        return f"{self.item} - {self.special_tooling}"
    
class EngineeringBase(models.Model):
    item = models.IntegerField()
    discipline = models.CharField(max_length=100)
    document = models.CharField(max_length=255)
    jobcard_number = models.CharField(max_length=100)
    rev = models.CharField(max_length=20)
    status = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.tag} - {self.document}"

class TaskBase(models.Model):
    item = models.IntegerField()
    discipline = models.CharField(max_length=100)
    working_code = models.CharField(max_length=50)
    typical_task = models.TextField()
    order = models.IntegerField()

    def __str__(self):
        return f"{self.working_code} - {self.typical_task[:30]}..."

class MaterialBase(models.Model):
    item                     = models.PositiveIntegerField(null=True, blank=True)
    job_card_number          = models.CharField("Job Card Number", max_length=50)
    working_code             = models.CharField("Working Code", max_length=50, blank=True)
    discipline               = models.CharField(max_length=50, blank=True)
    tag_jobcard_base         = models.CharField("Tag JobCard Base", max_length=100, blank=True)
    jobcard_required_qty     = models.DecimalField("JobCard Required Qty", max_digits=12, decimal_places=2, null=True,blank=True)
    unit_req_qty             = models.CharField("Unit Req. Qty", max_length=20, blank=True)
    weight_kg                = models.DecimalField("Weight (Kg)", max_digits=12,decimal_places=2,null=True,blank=True)
    material_segmentation    = models.CharField("Material Segmentation", max_length=100, blank=True)
    comments                 = models.TextField(blank=True)
    sequenc_no_procurement   = models.CharField("Sequenc. Nº Procurement", max_length=50, blank=True)
    status_procurement       = models.CharField("Status Procurement", max_length=50, blank=True)
    mto_item_no              = models.CharField("MTO Item No", max_length=50, blank=True)
    basic_material           = models.CharField("Basic Material", max_length=100, blank=True)
    description              = models.TextField()
    project_code             = models.CharField("Project Code", max_length=50, blank=True)
    nps1                     = models.CharField("NPS 1", max_length=20, blank=True)
    qty                      = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    unit                     = models.CharField(max_length=20, blank=True)
    po                       = models.CharField("PO", max_length=50, blank=True)

    class Meta:
        verbose_name = "Material Base"
        verbose_name_plural = "Materials Base"

    def __str__(self):
        return f"{self.job_card_number} – {self.description[:30]}…"
    
# BANCOS PARA ALOCAÇÃO DE RECURSOS E MATERIAIS E FERRAMENTAS

class AllocatedManpower(models.Model):
    jobcard_number = models.CharField(max_length=100)
    discipline     = models.CharField(max_length=100)
    working_code   = models.CharField(max_length=50)
    direct_labor   = models.CharField(max_length=100)
    qty            = models.DecimalField(max_digits=10, decimal_places=2)
    hours          = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    task_order     = models.IntegerField() 
    


    def __str__(self):
        return f"{self.jobcard_number} → {self.direct_labor} ({self.qty})"

class AllocatedMaterial(models.Model):
    jobcard_number = models.CharField(max_length=100)
    discipline     = models.CharField(max_length=50)
    working_code   = models.CharField(max_length=50)
    pmto_code      = models.CharField(max_length=100)
    description    = models.TextField()
    qty            = models.DecimalField(max_digits=10, decimal_places=2)
    comments       = models.TextField(blank=True, null=True)
    nps1 = models.CharField(max_length=50, blank=True, null=True)  # Adicione isso se não existir

    def __str__(self):
        return f"{self.jobcard_number} → {self.pmto_code} ({self.qty})"

class AllocatedTool(models.Model):
    jobcard_number   = models.CharField(max_length=100)
    discipline       = models.CharField(max_length=100)
    working_code     = models.CharField(max_length=50)
    direct_labor     = models.CharField(max_length=100)
    qty_direct_labor = models.DecimalField(max_digits=10, decimal_places=2)
    special_tooling  = models.CharField(max_length=255)
    qty              = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.jobcard_number} → {self.special_tooling} ({self.qty})"

class AllocatedEngineering(models.Model):
    jobcard_number = models.CharField(max_length=100)
    discipline     = models.CharField(max_length=50)
    document       = models.CharField(max_length=200)
    tag            = models.CharField(max_length=50)
    rev            = models.CharField(max_length=10, blank=True)
    status         = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"{self.jobcard_number} → {self.document} ({self.rev})"
    
class AllocatedTask(models.Model):
    jobcard_number = models.CharField(max_length=50)
    task_order = models.IntegerField()
    description = models.TextField()
    max_hours = models.FloatField(default=0.0)   # Novo campo
    total_hours = models.FloatField(default=0.0) # Novo campo
    completed = models.BooleanField(default=False)
    percent = models.FloatField(default=0.0)
    not_applicable = models.BooleanField(default=False)  # 🔥 NOVO CAMPO

    def __str__(self):
        return f"{self.jobcard_number} - Task {self.task_order}"
    
# BANCO AUXILIARES 

class Discipline(models.Model):
    code = models.CharField(max_length=10, unique=True)  # Ex: GE
    name = models.CharField(max_length=50)               # Ex: GENERAL

    def __str__(self):
        return f"{self.code} - {self.name}"

class Area(models.Model):
    area_code = models.CharField(max_length=20)          # Ex: A01
    code = models.CharField(max_length=20)               # Ex: A01.MD
    location = models.CharField(max_length=100)          # Ex: WATERFLOOD MAIN DECK
    level = models.CharField(max_length=10)              # Ex: MD

    def __str__(self):
        return f"{self.code} - {self.location} - {self.level}"

class WorkingCode(models.Model):
    code = models.CharField(max_length=10, unique=True)  # Ex: SCI
    description = models.CharField(max_length=200)       # Ex: SCAFFOLDING (ASSEMBLY/DISASSEMBLY)

    def __str__(self):
        return f"{self.code} - {self.description[:30]}"

class System(models.Model):
    system_code = models.CharField(max_length=20)        # Ex: 04
    subsystem_code = models.CharField(max_length=50)     # Ex: 04-34_BN

    def __str__(self):
        return f"{self.system_code} - {self.subsystem_code}"   
    
 