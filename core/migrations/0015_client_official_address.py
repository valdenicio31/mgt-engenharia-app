from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0014_client_origin")]
    operations = [
        migrations.AddField(
            model_name="client",
            name="official_street_code",
            field=models.CharField(blank=True, db_index=True, max_length=30, verbose_name="código oficial do logradouro"),
        ),
        migrations.AddField(
            model_name="client",
            name="address_validated_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="endereço validado em"),
        ),
    ]
