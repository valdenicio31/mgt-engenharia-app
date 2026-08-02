import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name="Client", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("name", models.CharField(max_length=160, verbose_name="nome")), ("document", models.CharField(blank=True, max_length=20, verbose_name="CNPJ/CPF")),
            ("email", models.EmailField(blank=True, max_length=254)), ("phone", models.CharField(blank=True, max_length=30)), ("active", models.BooleanField(default=True)),
        ]),
        migrations.CreateModel(name="Opportunity", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("title", models.CharField(max_length=180)), ("stage", models.CharField(choices=[("lead","Lead"),("qualificacao","Qualificacao"),("proposta","Proposta"),("negociacao","Negociacao"),("ganha","Ganha"),("perdida","Perdida")], default="lead", max_length=20)),
            ("estimated_value", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
            ("client", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="opportunities", to="core.client")),
            ("owner", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.CreateModel(name="Proposal", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("number", models.CharField(max_length=30, unique=True)), ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
            ("status", models.CharField(choices=[("rascunho","Rascunho"),("enviada","Enviada"),("aceita","Aceita"),("recusada","Recusada")], default="rascunho", max_length=20)), ("valid_until", models.DateField(blank=True, null=True)),
            ("opportunity", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="proposals", to="core.opportunity")),
        ]),
        migrations.CreateModel(name="Project", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("name", models.CharField(max_length=180)), ("status", models.CharField(choices=[("planejado","Planejado"),("em_execucao","Em_Execucao"),("pausado","Pausado"),("concluido","Concluido")], default="planejado", max_length=20)), ("progress", models.PositiveSmallIntegerField(default=0)),
            ("client", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="projects", to="core.client")), ("manager", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.CreateModel(name="Task", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("title", models.CharField(max_length=180)), ("due_date", models.DateField(blank=True, null=True)), ("completed", models.BooleanField(default=False)),
            ("assignee", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)), ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tasks", to="core.project")),
        ]),
        migrations.CreateModel(name="RAT", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("service_date", models.DateField()), ("description", models.TextField()), ("approved_by_client", models.BooleanField(default=False)),
            ("project", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="rats", to="core.project")), ("technician", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.CreateModel(name="AuditLog", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("action", models.CharField(max_length=80)), ("entity", models.CharField(max_length=80)), ("entity_id", models.CharField(max_length=50)), ("details", models.JSONField(blank=True, default=dict)), ("created_at", models.DateTimeField(auto_now_add=True)),
            ("actor", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
        ]),
    ]
