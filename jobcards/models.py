from django.db import models
from django.conf import settings

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
    tag = models.CharField(max_length=250)
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
    offshore_field_check = models.CharField(max_length=3, choices=[('NO', 'No'), ('YES', 'Yes')],default='NO')
    checked_preliminary_by = models.CharField(max_length=100, blank=True, null=True, verbose_name="Checked Preliminary By")
    checked_preliminary_at = models.DateTimeField(blank=True, null=True, verbose_name="Checked Preliminary At")
    image_1 = models.ImageField(upload_to='jobcard_images/', blank=True, null=True)
    image_2 = models.ImageField(upload_to='jobcard_images/', blank=True, null=True)
    image_3 = models.ImageField(upload_to='jobcard_images/', blank=True, null=True)
    image_4 = models.ImageField(upload_to='jobcard_images/', blank=True, null=True)

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
    jobcard_required_qty     = models.DecimalField("JobCard Required Qty", max_digits=12, decimal_places=2, null=True, blank=True)
    unit_req_qty             = models.CharField("Unit Req. Qty", max_length=20, blank=True)
    weight_kg                = models.DecimalField("Weight (Kg)", max_digits=12, decimal_places=2, null=True, blank=True)
    material_segmentation    = models.CharField("Material Segmentation", max_length=100, blank=True)
    comments                 = models.TextField(blank=True)
    sequenc_no_procurement   = models.CharField("Sequenc. Nº Procurement", max_length=50, blank=True)
    status_procurement       = models.CharField("Status Procurement", max_length=50, blank=True)
    mr_number                = models.CharField("MR Number", max_length=50, blank=True)   # <- RENOMEADO!
    basic_material           = models.CharField("Basic Material", max_length=100, blank=True)
    description              = models.TextField()
    project_code             = models.CharField("Project Code", max_length=50, blank=True)
    nps1                     = models.CharField("NPS 1", max_length=20, blank=True)
    qty                      = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    unit                     = models.CharField(max_length=20, blank=True)
    po                       = models.CharField("PO", max_length=50, blank=True)
    reference_documents      = models.TextField("Reference Documents", blank=True, null=True)  # <- NOVO CAMPO

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
    
# BANCO DE IMPEDIMENTOS

class Impediments(models.Model):
    jobcard_number = models.CharField(max_length=30)  # Editable input for JobCard Number
    scaffold = models.BooleanField(default=False)
    material = models.BooleanField(default=False)
    engineering = models.BooleanField(default=False)
    other = models.CharField(max_length=255, blank=True)
    origin_shell = models.BooleanField(default=False)
    origin_utc = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_by = models.CharField(max_length=150, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    mainpower = models.BooleanField(default=False)
    tools = models.BooleanField(default=False)
    access = models.BooleanField(default=False)
    pwt = models.BooleanField(default=False)

    def __str__(self):
        return f'Impediment for {self.jobcard_number}'

# BASE PARA ENGENHARIA E SUPRIMENTOS 

class PMTOBase(models.Model):
    pmto_code = models.CharField("PMTOCODE", max_length=100, unique=True)
    description = models.TextField("DESCRITIVO")
    material = models.CharField("MATERIAL", max_length=100)
    qty = models.DecimalField("QTY", max_digits=10, decimal_places=2)
    weight = models.DecimalField("WEIGHT", max_digits=10, decimal_places=2)
    unit = models.CharField("Unit", max_length=20, default="KG")

    def __str__(self):
        return f"{self.pmto_code} – {self.description[:30]}"
    
class MRBase(models.Model):
    mr_number = models.CharField("MR_NUMBER", max_length=100)
    pmto_code = models.CharField("PMTOCODE", max_length=100)
    type_items = models.CharField("TYPE ITEMS", max_length=100)
    basic_material = models.CharField("BASIC MATERIAL", max_length=200)
    description = models.TextField("DESCRIPTION")

    nps1 = models.CharField("NPS 1", max_length=50)
    length_ft_inch = models.CharField("LENGTH (FT' INCH\")", max_length=50)
    thk_mm = models.CharField("THK (mm)", max_length=50)
    pid = models.CharField("P&ID", max_length=100)
    line_number = models.CharField("LINE Nº", max_length=50)
    qty = models.DecimalField("QTY", max_digits=10, decimal_places=2)
    unit = models.CharField("UNIT", max_length=20)
    design_pressure_bar = models.CharField("DESIGN PRESSURE (Bar)", max_length=50)
    design_temperature_c = models.CharField("DESIGN TEMPERATURE (ºC)", max_length=50)
    service = models.CharField("SERVICE", max_length=100)
    spec = models.TextField("SPEC")
    proposer_sap_code = models.CharField("PROPOSER CODE (SAP CODE)", max_length=150)
    rev = models.CharField("REV", max_length=20)
    notes = models.TextField("NOTES", blank=True)

    def __str__(self):
        return f"{self.mr_number} - {self.pmto_code}"

class ProcurementBase(models.Model):
    po_number = models.CharField("PO Number", max_length=100)
    po_status = models.CharField("Status", max_length=40, default="Ordered")
    po_date = models.DateField("PO Date", blank=True, null=True)
    vendor = models.CharField("Vendor", max_length=100, blank=True, null=True)
    expected_delivery_date = models.DateField("Expected Delivery Date", blank=True, null=True)
    mr_number = models.CharField("MR Number", max_length=100, blank=True, null=True)
    mr_rev = models.CharField("MR Rev", max_length=20, blank=True, null=True)
    qty_mr = models.DecimalField("Qty MR", max_digits=10, decimal_places=2, blank=True, null=True)
    qty_mr_unit = models.CharField("Qty MR [UNIT]", max_length=10, blank=True, null=True)
    item_type = models.CharField("Item Type", max_length=100, blank=True, null=True)
    discipline = models.CharField("Discipline", max_length=100, blank=True, null=True)
    tam_2026 = models.CharField("TAM 2026", max_length=40, blank=True, null=True)
    pmto_code = models.CharField("PMTO CODE", max_length=100, blank=True, null=True)
    tag = models.CharField("TAG", max_length=50, blank=True, null=True)
    detailed_description = models.TextField("Detailed Description", blank=True, null=True)
    qty_purchased = models.DecimalField("Qty Purchased", max_digits=10, decimal_places=2, blank=True, null=True)
    qty_purchased_unit = models.CharField("Qty Purchased [UNIT]", max_length=10, blank=True, null=True)
    qty_received = models.DecimalField("Qty Received", max_digits=10, decimal_places=2, blank=True, null=True, default=0)  # NOVO CAMPO
    
    def __str__(self):
        return f"{self.po_number} ({self.po_status})"
    
# E-CLIC


class DocumentoControle(models.Model):
    codigo = models.CharField(max_length=100)
    codigo_secundario = models.CharField(max_length=100, blank=True, null=True)
    titulo = models.CharField(max_length=255, blank=True, null=True)
    disciplina = models.CharField(max_length=100, blank=True, null=True)
    revisao = models.CharField(max_length=20, blank=True, null=True)
    versao = models.CharField(max_length=20, blank=True, null=True)
    nome_projeto = models.CharField(max_length=255, blank=True, null=True)
    diretorio = models.CharField(max_length=255, blank=True, null=True)
    formato_documento = models.CharField(max_length=100, blank=True, null=True)
    a1_eq = models.CharField(max_length=50, blank=True, null=True)
    status_documento = models.CharField(max_length=100, blank=True, null=True)
    inicio_fluxo = models.CharField(max_length=50, blank=True, null=True)
    fim_fluxo = models.CharField(max_length=50, blank=True, null=True)
    responsavel_atividade = models.CharField(max_length=100, blank=True, null=True)
    status_emissao = models.CharField(max_length=100, blank=True, null=True)
    avanco_fisico = models.CharField(max_length=20, blank=True, null=True)
    data_planejada = models.CharField(max_length=50, blank=True, null=True)
    nome_arquivo = models.CharField(max_length=255, blank=True, null=True)
    tamanho_arquivo = models.CharField(max_length=50, blank=True, null=True)
    data_importacao = models.CharField(max_length=50, blank=True, null=True)
    folhas = models.CharField(max_length=10, blank=True, null=True)
    data_ultima_emissao = models.CharField(max_length=50, blank=True, null=True)
    revisao_ultima_emissao = models.CharField(max_length=20, blank=True, null=True)
    finalidade_ultima_emissao = models.CharField(max_length=100, blank=True, null=True)
    data_recebimento_markup = models.CharField(max_length=50, blank=True, null=True)
    revisao_recebimento_markup = models.CharField(max_length=20, blank=True, null=True)
    tipo_markup = models.CharField(max_length=100, blank=True, null=True)
    data_planejada_ultimo_markup = models.CharField(max_length=50, blank=True, null=True)
    data_recebimento_as_built = models.CharField(max_length=50, blank=True, null=True)
    data_atendimento_as_built = models.CharField(max_length=50, blank=True, null=True)
    controle_copias = models.CharField(max_length=50, blank=True, null=True)
    finalidade_proxima_emissao = models.CharField(max_length=100, blank=True, null=True)
    plan_ifr = models.CharField(max_length=50, blank=True, null=True)
    plan_ifa = models.CharField(max_length=50, blank=True, null=True)
    plan_afc = models.CharField(max_length=50, blank=True, null=True)
    tr_received = models.CharField(max_length=50, blank=True, null=True)
    tr_rev = models.CharField(max_length=50, blank=True, null=True)
    tr_date = models.CharField(max_length=50, blank=True, null=True)
    issued_assai = models.CharField(max_length=50, blank=True, null=True)
    assai_date = models.CharField(max_length=50, blank=True, null=True)
    recvd_assai = models.CharField(max_length=50, blank=True, null=True)
    recvd_date = models.CharField(max_length=50, blank=True, null=True)
    code_11 = models.CharField(max_length=50, blank=True, null=True)
    tr_issued = models.CharField(max_length=50, blank=True, null=True)
    issued_date = models.CharField(max_length=50, blank=True, null=True)
    ivb_required = models.CharField(max_length=10, blank=True, null=True)
    ivb_priority = models.CharField(max_length=10, blank=True, null=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    # Se preferir pode adicionar "auto_now=True" em data_importacao para timestamp real de importação

    class Meta:
        unique_together = ['codigo', 'nome_projeto']  # Pode ajustar para garantir unicidade

    def __str__(self):
        return f"{self.codigo} - Rev {self.revisao}"

class DocumentoRevisaoAlterada(models.Model):
    codigo = models.CharField(max_length=100)
    nome_projeto = models.CharField(max_length=255)
    revisao_anterior = models.CharField(max_length=20, blank=True, null=True)
    revisao_nova = models.CharField(max_length=20, blank=True, null=True)
    data_mudanca = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-data_mudanca']

    def __str__(self):
        return f"{self.codigo} ({self.nome_projeto}): {self.revisao_anterior} → {self.revisao_nova}"

class WarehouseStock(models.Model):
    po_number = models.CharField("PO Number", max_length=100)
    item_type = models.CharField("Item Type", max_length=100, blank=True, null=True)
    vendor = models.CharField("Vendor", max_length=100, blank=True, null=True)
    discipline = models.CharField("Discipline", max_length=100, blank=True, null=True)
    tag = models.CharField("Tag", max_length=50, blank=True, null=True)
    pmto_code = models.CharField("PMTO Code", max_length=100, blank=True, null=True)
    detailed_description = models.TextField("Detailed Description", blank=True, null=True)
    
    # Total quantity purchased (according to PO)
    qty_purchased = models.DecimalField("Qty Purchased", max_digits=10, decimal_places=2, blank=True, null=True)
    qty_purchased_unit = models.CharField("Qty Purchased Unit", max_length=10, blank=True, null=True)
    
    # Total quantity already received
    qty_received = models.DecimalField("Qty Received", max_digits=10, decimal_places=2, default=0)
    
    # Remaining balance to be received (optional, for performance)
    balance_to_receive = models.DecimalField("Balance to Receive", max_digits=10, decimal_places=2, default=0)
    
    # Last receipt date
    last_received_at = models.DateTimeField("Last Received At", blank=True, null=True)
    # User who received (optional)
    received_by = models.CharField("Received By", max_length=100, blank=True, null=True)
    
    # Notes (optional)
    notes = models.TextField("Notes", blank=True, null=True)
    
    registration_type = models.CharField(max_length=10, choices=[('unit', 'Unit'), ('lot', 'Lot')], default='unit')
    
    def __str__(self):
        return f"{self.po_number} - {self.tag} ({self.qty_received}/{self.qty_purchased})"


class WarehousePiece(models.Model):
    stock = models.ForeignKey(
        WarehouseStock, on_delete=models.CASCADE, related_name='pieces'
    )
    rfid_tag = models.CharField(
        max_length=100, unique=True,
        verbose_name="RFID Tag"
    )
    lot_qty = models.DecimalField(
        max_digits=10, decimal_places=2, default=1,
        verbose_name="Quantity in Lot"
    )  # Aceita valores decimais!
    created_at = models.DateTimeField(auto_now_add=True)
    received_by = models.CharField(max_length=100, blank=True, null=True)
    LOCATION_CHOICES = [
        ('warehouse_aveon', 'Warehouse at Aveon Yard'),
        ('dock_aveon', 'Dock at Aveon Yard'),
        ('flotel', 'Flotel'),
        ('laydown_area', 'Laydown Area'),
        # ...adicione mais locais conforme a evolução do processo!
    ]
    location = models.CharField(
        max_length=50,
        choices=LOCATION_CHOICES,
        default='warehouse_aveon'
    )
    notes = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Warehouse Piece"
        verbose_name_plural = "Warehouse Pieces"

    def __str__(self):
        return f"{self.rfid_tag} ({self.stock.po_number} - {self.stock.pmto_code or self.stock.tag})"

# RDC

class DailyFieldReport(models.Model):
    # Identificação do relatório (repete em todas as linhas do mesmo DFR)
    dfr_number = models.CharField(max_length=20, db_index=True)  # NÃO é unique por linha
    line_seq = models.PositiveIntegerField(default=1)            # 1..N dentro do mesmo dfr_number

    # Cabeçalho (repete em todas as linhas desse DFR)
    jobcard_number = models.CharField(max_length=50)
    discipline = models.CharField(max_length=100, blank=True, null=True)
    working_code = models.CharField(max_length=50, blank=True, null=True)
    report_date = models.DateField()
    total_hours = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_lines = models.IntegerField(default=0)
    created_by = models.CharField(max_length=150, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)
    snapshot = models.JSONField(blank=True, null=True)

    # Dados da linha (variável por linha)
    task_description = models.TextField()
    task_order = models.IntegerField(blank=True, null=True)
    direct_labor = models.CharField(max_length=150)
    hours = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    qty = models.IntegerField(default=1)
    source = models.CharField(max_length=12, blank=True, null=True)  # "ALLOCATED" / "MANUAL" etc.

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["dfr_number", "line_seq"], name="uniq_dfr_line"
            )
        ]

    def __str__(self):
        
        return f"{self.dfr_number} • L{self.line_seq:02d} • {self.direct_labor}"

    # util simples para gerar o próximo DFR-000001
    @classmethod
    def next_dfr_number(cls) -> str:
        # pega o MAIOR número existente e soma 1
        # (simples e suficiente para a maioria dos casos; use transaction.atomic na view)
        
        last = cls.objects.order_by("-id").first()
        seq = 1
        if last and last.dfr_number and last.dfr_number.startswith("DFR-"):
            try:
                seq = int(last.dfr_number.split("-")[1]) + 1
            except Exception:
                seq = 1
        return f"DFR-{seq:06d}"
    

    # ===== CRONOGRAMA / P6 =====

class ScheduleWBS(models.Model):
    # slug do caminho completo (root/epc-01/management/...)
    code = models.CharField(max_length=768, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    parent = models.ForeignKey('self', null=True, blank=True,
                               on_delete=models.CASCADE, related_name='children')
    # ordem visual dentro do pai (preenchido no import por template)
    order = models.PositiveIntegerField(default=0)
    # opcional, se quiser salvar um código do P6
    p6_code = models.CharField(max_length=120, blank=True, db_index=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.name}"

    @property
    def level(self) -> int:
        return (self.code or "").count("/")

class ScheduleActivity(models.Model):
    activity_id = models.CharField(max_length=512, unique=True)
    name = models.CharField(max_length=512, blank=True, default="")
    start = models.DateField(null=True, blank=True)
    finish = models.DateField(null=True, blank=True)

    duration_days = models.IntegerField(null=True, blank=True)
    original_duration_days = models.IntegerField(null=True, blank=True)
    percent_complete = models.FloatField(default=0.0)

    points = models.FloatField(null=True, blank=True)
    hh = models.FloatField(null=True, blank=True)

    # se já tem wbs, mantenha como opcional – não vamos usar aqui
    wbs = models.ForeignKey(
        "ScheduleWBS", null=True, blank=True, on_delete=models.SET_NULL, related_name="activities"
    )

    # novo: Level vindo do arquivo (0,1,2,3…)
    level = models.PositiveSmallIntegerField(default=0)

    # já tínhamos ou adicione:
    sort_index = models.PositiveIntegerField(default=0, db_index=True)

    jobcard_number = models.CharField(max_length=64, blank=True, default="")
    status = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        indexes = [
            models.Index(fields=["sort_index"]),
            models.Index(fields=["activity_id"]),
        ]

    def __str__(self):
        return f"{self.activity_id} - {self.name}"


class ScheduleLink(models.Model):
    FS = "FS"; SS = "SS"; FF = "FF"; SF = "SF"
    LINK_TYPES = [(FS, "Finish-Start"), (SS, "Start-Start"), (FF, "Finish-Finish"), (SF, "Start-Finish")]

    predecessor = models.ForeignKey(ScheduleActivity, on_delete=models.CASCADE, related_name="as_predecessor")
    successor   = models.ForeignKey(ScheduleActivity, on_delete=models.CASCADE, related_name="as_successor")
    link_type   = models.CharField(max_length=2, choices=LINK_TYPES, default=FS)
    lag_days    = models.FloatField(default=0.0)

    class Meta:
        unique_together = ("predecessor", "successor", "link_type")
        indexes = [models.Index(fields=["predecessor"]), models.Index(fields=["successor"])]

    def __str__(self):
        return f"{self.predecessor_id} -> {self.successor_id} ({self.link_type}, {self.lag_days}d)"