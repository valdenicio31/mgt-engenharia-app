from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0003_gazettefinding")]

    operations = [
        migrations.AddField(model_name="client", name="process_number", field=models.CharField(blank=True, max_length=50, verbose_name="número do processo")),
        migrations.AddField(model_name="client", name="publication_date", field=models.DateField(blank=True, null=True, verbose_name="data da publicação")),
        migrations.AddField(model_name="client", name="street", field=models.CharField(blank=True, max_length=180, verbose_name="rua/logradouro")),
        migrations.AddField(model_name="client", name="address_number", field=models.CharField(blank=True, max_length=20, verbose_name="número")),
        migrations.AddField(model_name="client", name="complement", field=models.CharField(blank=True, max_length=80, verbose_name="complemento")),
        migrations.AddField(model_name="client", name="neighborhood", field=models.CharField(blank=True, max_length=100, verbose_name="bairro")),
        migrations.AddField(model_name="client", name="city", field=models.CharField(blank=True, default="Rio de Janeiro", max_length=100, verbose_name="cidade")),
        migrations.AddField(model_name="client", name="state", field=models.CharField(blank=True, default="RJ", max_length=2, verbose_name="estado")),
        migrations.AddField(model_name="client", name="postal_code", field=models.CharField(blank=True, max_length=10, verbose_name="CEP")),
        migrations.AddField(model_name="client", name="notification_number", field=models.CharField(blank=True, max_length=50, verbose_name="número da notificação")),
        migrations.AddField(model_name="client", name="classification", field=models.CharField(blank=True, choices=[("autovistoria", "Autovistoria explícita"), ("manutencao_predial", "Fiscalização de Manutenção Predial"), ("outros", "Outros")], max_length=30, verbose_name="classificação")),
        migrations.AddField(model_name="client", name="action_description", field=models.TextField(blank=True, verbose_name="descrição / providência")),
        migrations.AddField(model_name="client", name="validation", field=models.CharField(choices=[("validar", "Validar"), ("confirmado", "Confirmado"), ("descartado", "Descartado")], default="validar", max_length=20, verbose_name="validação")),
    ]
