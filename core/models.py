from django.conf import settings
from django.db import models

class Timestamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True

class Client(Timestamped):
    name = models.CharField("nome", max_length=160)
    document = models.CharField("CNPJ/CPF", max_length=20, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    active = models.BooleanField(default=True)
    def __str__(self): return self.name

class Opportunity(Timestamped):
    STAGES = [(x, x.title()) for x in ("lead", "qualificacao", "proposta", "negociacao", "ganha", "perdida")]
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name="opportunities")
    title = models.CharField(max_length=180)
    stage = models.CharField(max_length=20, choices=STAGES, default="lead")
    estimated_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    def __str__(self): return self.title

class Proposal(Timestamped):
    STATUS = [(x, x.title()) for x in ("rascunho", "enviada", "aceita", "recusada")]
    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, related_name="proposals")
    number = models.CharField(max_length=30, unique=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS, default="rascunho")
    valid_until = models.DateField(null=True, blank=True)
    def __str__(self): return self.number

class Project(Timestamped):
    STATUS = [(x, x.title()) for x in ("planejado", "em_execucao", "pausado", "concluido")]
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name="projects")
    name = models.CharField(max_length=180)
    status = models.CharField(max_length=20, choices=STATUS, default="planejado")
    progress = models.PositiveSmallIntegerField(default=0)
    manager = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    def __str__(self): return self.name

class Task(Timestamped):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=180)
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    due_date = models.DateField(null=True, blank=True)
    completed = models.BooleanField(default=False)
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
