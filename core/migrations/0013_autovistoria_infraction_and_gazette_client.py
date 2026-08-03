from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [("core", "0012_opportunity_autovistoria_consultation")]
    operations = [
        migrations.AddField(
            model_name="gazettefinding", name="client",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="gazette_findings", to="core.client", verbose_name="condomínio vinculado"),
        ),
        migrations.CreateModel(
            name="AutovistoriaInfraction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
                ("communication_number", models.CharField(blank=True, max_length=50, verbose_name="número do comunicado")),
                ("infraction_number", models.CharField(max_length=80, verbose_name="número da autuação")),
                ("infraction_type", models.CharField(blank=True, max_length=180, verbose_name="tipo da autuação")),
                ("description", models.TextField(verbose_name="descrição / exigência")),
                ("infraction_date", models.DateField(blank=True, null=True, verbose_name="data da autuação")),
                ("status", models.CharField(choices=[("ativa","Ativa"),("regularizada","Regularizada"),("cancelada","Cancelada"),("desconhecida","Não informada")], default="ativa", max_length=20, verbose_name="situação")),
                ("source_url", models.URLField(blank=True, default="https://autovistoria.rio.rj.gov.br/ConsultaPublica.php", max_length=500, verbose_name="fonte da consulta")),
                ("consulted_at", models.DateTimeField(auto_now_add=True, verbose_name="consultado em")),
                ("client", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="autovistoria_infractions", to="core.client", verbose_name="condomínio")),
                ("gazette_finding", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="infractions", to="core.gazettefinding", verbose_name="publicação do Diário Oficial")),
                ("opportunity", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="infractions", to="core.opportunity", verbose_name="oportunidade")),
            ],
            options={"ordering": ("-consulted_at", "infraction_number")},
        ),
        migrations.AddConstraint(model_name="autovistoriainfraction", constraint=models.UniqueConstraint(fields=("client", "infraction_number"), name="unique_client_autovistoria_infraction")),
    ]
