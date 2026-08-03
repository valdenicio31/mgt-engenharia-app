from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0010_merge_0007_landinglead_0009_task_updates")]
    operations = [
        migrations.AddField(
            model_name="client",
            name="photo",
            field=models.ImageField(blank=True, upload_to="condominiums/", verbose_name="foto do condomínio"),
        ),
    ]
