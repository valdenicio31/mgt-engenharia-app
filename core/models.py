from django.conf import settings
from django.db import models

class Timestamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True

class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    cpf = models.CharField("CPF", max_length=11, unique=True)
    photo = models.ImageField("foto", upload_to="profiles/", blank=True)
    phone = models.CharField("telefone", max_length=30, blank=True)
    birth_date = models.DateField("data de nascimento", null=True, blank=True)
    street = models.CharField("rua/logradouro", max_length=180, blank=True)
    address_number = models.CharField("número", max_length=20, blank=True)
    complement = models.CharField("complemento", max_length=80, blank=True)
    neighborhood = models.CharField("bairro", max_length=100, blank=True)
    city = models.CharField("cidade", max_length=100, blank=True, default="Rio de Janeiro")
    state = models.CharField("estado", max_length=2, blank=True, default="RJ")
    postal_code = models.CharField("CEP", max_length=10, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.email} — {self.cpf}"

class GazetteFinding(Timestamped):
    STATUS = [("novo", "Novo"), ("conferido", "Conferido"), ("convertido", "Convertido em lead"), ("descartado", "Descartado")]
    publication_date = models.DateField("data da publicação")
    edition_id = models.CharField(max_length=30)
    page = models.PositiveIntegerField()
    process_number = models.CharField(max_length=50, blank=True)
    condominium_name = models.CharField(max_length=220)
    notification_number = models.CharField(max_length=50)
    address = models.CharField(max_length=260)
    source_url = models.URLField(max_length=500)
    raw_excerpt = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default="novo")

    class Meta:
        ordering = ("-publication_date", "condominium_name")
        constraints = [models.UniqueConstraint(fields=("edition_id", "notification_number"), name="unique_gazette_notification")]

    def __str__(self):
        return f"{self.condominium_name} — {self.notification_number}"

class Client(Timestamped):
    CLASSIFICATIONS = [
        ("autovistoria", "Autovistoria explícita"),
        ("manutencao_predial", "Fiscalização de Manutenção Predial"),
        ("outros", "Outros"),
    ]
    VALIDATIONS = [
        ("validar", "Validar"),
        ("confirmado", "Confirmado"),
        ("descartado", "Descartado"),
    ]
    name = models.CharField("nome", max_length=160)
    document = models.CharField("CNPJ/CPF", max_length=20, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    process_number = models.CharField("número do processo", max_length=50, blank=True)
    publication_date = models.DateField("data da publicação", null=True, blank=True)
    street = models.CharField("rua/logradouro", max_length=180, blank=True)
    address_number = models.CharField("número", max_length=20, blank=True)
    complement = models.CharField("complemento", max_length=80, blank=True)
    neighborhood = models.CharField("bairro", max_length=100, blank=True)
    city = models.CharField("cidade", max_length=100, blank=True, default="Rio de Janeiro")
    state = models.CharField("estado", max_length=2, blank=True, default="RJ")
    postal_code = models.CharField("CEP", max_length=10, blank=True)
    notification_number = models.CharField("número da notificação", max_length=50, blank=True)
    classification = models.CharField("classificação", max_length=30, choices=CLASSIFICATIONS, blank=True)
    action_description = models.TextField("descrição / providência", blank=True)
    validation = models.CharField("validação", max_length=20, choices=VALIDATIONS, default="validar")
    active = models.BooleanField(default=True)
    def __str__(self): return self.name

class Opportunity(Timestamped):
    STAGES = [("lead", "Lead"), ("qualificacao", "Qualificação"), ("proposta", "Proposta"), ("negociacao", "Negociação"), ("ganha", "Ganha"), ("perdida", "Perdida")]
    client = models.ForeignKey(Client, verbose_name="cliente/condomínio", on_delete=models.PROTECT, related_name="opportunities")
    title = models.CharField("título", max_length=180)
    stage = models.CharField("etapa", max_length=20, choices=STAGES, default="lead")
    estimated_value = models.DecimalField("valor estimado", max_digits=12, decimal_places=2, default=0)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="responsável", on_delete=models.PROTECT)
    def __str__(self): return self.title

class Proposal(Timestamped):
    STATUS = [("rascunho", "Rascunho"), ("enviada", "Enviada"), ("aceita", "Aceita"), ("recusada", "Recusada")]
    opportunity = models.ForeignKey(Opportunity, verbose_name="oportunidade", on_delete=models.CASCADE, related_name="proposals")
    number = models.CharField("número", max_length=30, unique=True)
    amount = models.DecimalField("valor", max_digits=12, decimal_places=2)
    status = models.CharField("situação", max_length=20, choices=STATUS, default="rascunho")
    valid_until = models.DateField("válida até", null=True, blank=True)
    def __str__(self): return self.number

class Project(Timestamped):
    STATUS = [("planejado", "Planejado"), ("em_execucao", "Em execução"), ("pausado", "Pausado"), ("concluido", "Concluído")]
    client = models.ForeignKey(Client, verbose_name="cliente/condomínio", on_delete=models.PROTECT, related_name="projects")
    name = models.CharField("nome do projeto", max_length=180)
    status = models.CharField("situação", max_length=20, choices=STATUS, default="planejado")
    progress = models.PositiveSmallIntegerField("progresso (%)", default=0)
    manager = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="gestor", on_delete=models.PROTECT)
    def __str__(self): return self.name

class Task(Timestamped):
    project = models.ForeignKey(Project, verbose_name="projeto", on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField("tarefa", max_length=180)
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="responsável", on_delete=models.PROTECT)
    due_date = models.DateField("prazo", null=True, blank=True)
    completed = models.BooleanField("concluída", default=False)
    def __str__(self): return self.title

class RAT(Timestamped):
    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name="rats")
    service_date = models.DateField()
    description = models.TextField()
    technician = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    approved_by_client = models.BooleanField(default=False)

class AuditLog(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=80)
    entity = models.CharField(max_length=80)
    entity_id = models.CharField(max_length=50)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
