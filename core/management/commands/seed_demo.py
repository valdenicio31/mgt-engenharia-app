from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from core.models import Client, Opportunity, Project, Proposal, RAT, Task

class Command(BaseCommand):
    help = "Carrega dados demonstrativos idempotentes para homologação"
    def handle(self, *args, **options):
        user = get_user_model().objects.filter(is_superuser=True).first()
        if not user:
            self.stdout.write(self.style.WARNING("Crie um superusuário antes de carregar a demonstração.")); return
        client, _ = Client.objects.get_or_create(name="Condomínio Horizonte", defaults={"email": "sindico@example.com", "phone": "(11) 99999-0000"})
        opp, _ = Opportunity.objects.get_or_create(client=client, title="Modernização elétrica", defaults={"stage": "proposta", "estimated_value": 185000, "owner": user})
        Proposal.objects.get_or_create(number="MGT-2026-001", defaults={"opportunity": opp, "amount": 185000, "status": "enviada", "valid_until": date.today() + timedelta(days=15)})
        project, _ = Project.objects.get_or_create(client=client, name="Adequação SPDA", defaults={"status": "em_execucao", "progress": 62, "manager": user})
        Task.objects.get_or_create(project=project, title="Vistoria técnica do bloco A", defaults={"assignee": user, "due_date": date.today() + timedelta(days=3)})
        RAT.objects.get_or_create(project=project, service_date=date.today(), defaults={"description": "Inspeção inicial e levantamento fotográfico.", "technician": user})
        self.stdout.write(self.style.SUCCESS("Dados demonstrativos carregados."))
