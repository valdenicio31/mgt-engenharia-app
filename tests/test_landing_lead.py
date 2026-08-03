from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import Client, LandingLead, Opportunity


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class LandingLeadTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_superuser(
            username="gestor", email="gestor@example.com", password="SenhaForte123"
        )

    def payload(self):
        return {
            "syndic_name": "João da Silva",
            "email": "sindico@example.com",
            "phone": "21999999999",
            "legal_name": "Condomínio Autovistoria",
            "document": "10.652.916/0001-80",
            "address": "Rua das Flores, 100, Rio de Janeiro",
            "postal_code": "20000-000",
            "building_age": "30",
            "floors": "12",
            "apartments": "48",
            "stores": "2",
            "duplex_penthouse": "False",
            "garage_floors": "2",
            "underground_garage": "True",
            "elevators": "3",
            "built_area": "8500.00",
            "pool": "on",
            "sauna": "on",
            "other": "Salão de festas",
            "lgpd_consent": "on",
        }

    def test_landing_page_is_public_and_focused_on_autovistoria(self):
        response = self.client.get(reverse("autovistoria_landing"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AUTOVISTORIA PREDIAL")
        self.assertContains(response, "Solicitar orçamento")

    def test_submission_creates_lead_client_opportunity_and_email(self):
        response = self.client.post(reverse("autovistoria_landing"), self.payload())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Solicitação recebida com sucesso")
        lead = LandingLead.objects.get()
        client = Client.objects.get()
        opportunity = Opportunity.objects.get()
        self.assertEqual(lead.client, client)
        self.assertEqual(lead.opportunity, opportunity)
        self.assertEqual(client.classification, "autovistoria")
        self.assertEqual(opportunity.title, "Autovistoria — Condomínio Autovistoria")
        self.assertEqual(opportunity.owner, self.owner)
        self.assertEqual(len(mail.outbox), 1)

    def test_lgpd_consent_is_required(self):
        data = self.payload()
        data.pop("lgpd_consent")
        response = self.client.post(reverse("autovistoria_landing"), data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Este campo é obrigatório")
        self.assertFalse(LandingLead.objects.exists())
