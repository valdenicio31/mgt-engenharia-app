from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0004_client_notification_fields")]
    operations = [
        migrations.AddField(model_name="userprofile", name="photo", field=models.ImageField(blank=True, upload_to="profiles/", verbose_name="foto")),
        migrations.AddField(model_name="userprofile", name="phone", field=models.CharField(blank=True, max_length=30, verbose_name="telefone")),
        migrations.AddField(model_name="userprofile", name="birth_date", field=models.DateField(blank=True, null=True, verbose_name="data de nascimento")),
        migrations.AddField(model_name="userprofile", name="street", field=models.CharField(blank=True, max_length=180, verbose_name="rua/logradouro")),
        migrations.AddField(model_name="userprofile", name="address_number", field=models.CharField(blank=True, max_length=20, verbose_name="número")),
        migrations.AddField(model_name="userprofile", name="complement", field=models.CharField(blank=True, max_length=80, verbose_name="complemento")),
        migrations.AddField(model_name="userprofile", name="neighborhood", field=models.CharField(blank=True, max_length=100, verbose_name="bairro")),
        migrations.AddField(model_name="userprofile", name="city", field=models.CharField(blank=True, default="Rio de Janeiro", max_length=100, verbose_name="cidade")),
        migrations.AddField(model_name="userprofile", name="state", field=models.CharField(blank=True, default="RJ", max_length=2, verbose_name="estado")),
        migrations.AddField(model_name="userprofile", name="postal_code", field=models.CharField(blank=True, max_length=10, verbose_name="CEP")),
    ]
