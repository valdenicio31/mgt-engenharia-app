from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("core", "0006_alter_opportunity_client_and_more")]

    operations = [
        migrations.CreateModel(
            name="LandingLead",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("syndic_name", models.CharField(max_length=160, verbose_name="síndico(a)")),
                ("email", models.EmailField(max_length=254, verbose_name="e-mail")),
                ("phone", models.CharField(max_length=30, verbose_name="celular")),
                ("legal_name", models.CharField(max_length=180, verbose_name="razão social")),
                ("document", models.CharField(max_length=20, verbose_name="CNPJ/CPF")),
                ("address", models.CharField(max_length=260, verbose_name="endereço")),
                ("postal_code", models.CharField(max_length=10, verbose_name="CEP")),
                ("building_age", models.PositiveSmallIntegerField(blank=True, null=True, verbose_name="idade aproximada do prédio")),
                ("floors", models.PositiveSmallIntegerField(blank=True, null=True, verbose_name="nº de pavimentos")),
                ("apartments", models.PositiveIntegerField(blank=True, null=True, verbose_name="quantidade de apartamentos")),
                ("stores", models.PositiveIntegerField(blank=True, null=True, verbose_name="quantidade de lojas")),
                ("duplex_penthouse", models.BooleanField(choices=[(True, "Sim"), (False, "Não")], default=False, verbose_name="cobertura duplex")),
                ("garage_floors", models.PositiveSmallIntegerField(blank=True, null=True, verbose_name="andares de garagem")),
                ("underground_garage", models.BooleanField(choices=[(True, "Sim"), (False, "Não")], default=False, verbose_name="garagem no subsolo")),
                ("elevators", models.PositiveSmallIntegerField(blank=True, null=True, verbose_name="número de elevadores")),
                ("built_area", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, verbose_name="área total edificada aproximada (m²)")),
                ("pool", models.BooleanField(default=False, verbose_name="piscina")),
                ("sauna", models.BooleanField(default=False, verbose_name="sauna")),
                ("courts", models.BooleanField(default=False, verbose_name="quadras polivalentes")),
                ("generators", models.BooleanField(default=False, verbose_name="geradores")),
                ("other", models.TextField(blank=True, verbose_name="outros")),
                ("lgpd_consent", models.BooleanField(default=False, verbose_name="consentimento LGPD")),
                ("source", models.CharField(default="Landing Page", max_length=40, verbose_name="origem")),
                ("client", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="landing_leads", to="core.client")),
                ("opportunity", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="landing_leads", to="core.opportunity")),
            ],
        ),
    ]
