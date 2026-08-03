from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [("core", "0002_userprofile")]
    operations = [
        migrations.CreateModel(name="GazetteFinding", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("publication_date", models.DateField(verbose_name="data da publicação")), ("edition_id", models.CharField(max_length=30)),
            ("page", models.PositiveIntegerField()), ("process_number", models.CharField(blank=True, max_length=50)),
            ("condominium_name", models.CharField(max_length=220)), ("notification_number", models.CharField(max_length=50)),
            ("address", models.CharField(max_length=260)), ("source_url", models.URLField(max_length=500)),
            ("raw_excerpt", models.TextField(blank=True)), ("status", models.CharField(choices=[("novo","Novo"),("conferido","Conferido"),("convertido","Convertido em lead"),("descartado","Descartado")], default="novo", max_length=20)),
        ], options={"ordering": ("-publication_date", "condominium_name")}),
        migrations.AddConstraint(model_name="gazettefinding", constraint=models.UniqueConstraint(fields=("edition_id", "notification_number"), name="unique_gazette_notification")),
    ]
