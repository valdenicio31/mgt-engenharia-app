from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from core.models import Client, Opportunity, Project, RAT, RATRevision


class RATAndLandingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(username="gestor", email="gestor@example.com", password="SenhaForte123")
        self.client.force_login(self.user)
        self.condominium = Client.objects.create(name="Condomínio Modelo")
        self.project = Project.objects.create(client=self.condominium, name="Projeto Modelo", manager=self.user)

    def test_generates_edits_versions_and_deletes_daily_rat(self):
        create = self.client.post(reverse("rats"), {"project": self.project.pk, "service_date": date.today().isoformat(), "start_time": "08:00", "end_time": "12:00", "description": "Inspeção predial", "notes": "Sem ocorrências", "next_steps": "Emitir relatório", "status": "gerada"})
        self.assertRedirects(create, reverse("rats"))
        rat = RAT.objects.get()
        self.assertEqual(float(rat.total_hours), 4.0)
        document = self.client.get(reverse("rat_document", args=(rat.pk,)))
        self.assertContains(document, "Márcio Guimarães")
        edit = self.client.post(f"{reverse('rats')}?editar={rat.pk}", {"project": self.project.pk, "service_date": date.today().isoformat(), "start_time": "08:00", "end_time": "13:00", "description": "Inspeção atualizada", "notes": "", "next_steps": "", "status": "enviada"})
        self.assertRedirects(edit, reverse("rats"))
        rat.refresh_from_db()
        self.assertEqual(rat.version, 2)
        self.assertEqual(float(rat.total_hours), 5.0)
        self.assertEqual(RATRevision.objects.get().snapshot["description"], "Inspeção predial")
        deleted = self.client.post(reverse("record_delete", args=("rats", rat.pk)))
        self.assertRedirects(deleted, reverse("rats"))
        self.assertFalse(RAT.objects.exists())

    def test_landing_contact_creates_client_and_opportunity(self):
        self.client.logout()
        response = self.client.post(reverse("landing_page"), {"name": "João Síndico", "condominium": "Condomínio Novo", "email": "joao@example.com", "phone": "21999990000", "service": "Autovistoria", "consent": "on"})
        self.assertContains(response, "Contato recebido")
        opportunity = Opportunity.objects.get()
        self.assertEqual(opportunity.source, "landing_page")
        self.assertEqual(opportunity.client.name, "Condomínio Novo")
