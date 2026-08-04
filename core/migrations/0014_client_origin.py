from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [("core", "0013_autovistoria_infraction_and_gazette_client")]
    operations = [
        migrations.AddField(
            model_name="client",
            name="origin",
            field=models.CharField(choices=[("manual", "Digitado manualmente"), ("arquivo", "Importado por arquivo"), ("diario_oficial", "Importado do Diário Oficial")], db_index=True, default="manual", max_length=30, verbose_name="origem do cadastro"),
        ),
    ]
