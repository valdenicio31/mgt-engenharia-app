from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0011_client_photo")]

    operations = [
        migrations.AddField(model_name="opportunity", name="source", field=models.CharField(blank=True, max_length=60, verbose_name="origem")),
        migrations.AddField(model_name="opportunity", name="communication_number", field=models.CharField(blank=True, max_length=50, verbose_name="número do comunicado")),
        migrations.AddField(model_name="opportunity", name="consultation_status", field=models.CharField(blank=True, max_length=180, verbose_name="situação consultada")),
        migrations.AddField(model_name="opportunity", name="consultation_notes", field=models.TextField(blank=True, verbose_name="observações da consulta")),
        migrations.AddField(model_name="opportunity", name="consultation_address", field=models.CharField(blank=True, max_length=300, verbose_name="endereço consultado")),
        migrations.AddField(model_name="opportunity", name="source_url", field=models.URLField(blank=True, max_length=500, verbose_name="link da consulta")),
        migrations.AddField(model_name="opportunity", name="consulted_at", field=models.DateTimeField(blank=True, null=True, verbose_name="consultado em")),
    ]
