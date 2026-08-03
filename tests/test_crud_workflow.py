from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from core.models import Client, Opportunity, Project, Task


class CrudWorkflowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="teste", password="SenhaForte123")
        self.client.force_login(self.user)
        self.condominium = Client.objects.create(name="Condomínio Teste", email="teste@example.com", phone="21999990000")

    def test_opportunity_can_be_edited_deleted_exported_and_contacted(self):
        opportunity = Opportunity.objects.create(client=self.condominium, title="Autovistoria", owner=self.user)
        page = self.client.get(reverse("opportunities"))
        self.assertContains(page, "WhatsApp")
        self.assertContains(page, "Carta")
        edit = self.client.post(f"{reverse('opportunities')}?editar={opportunity.pk}", {
            "client": self.condominium.pk, "title": "Autovistoria atualizada", "stage": "qualificacao", "estimated_value": "1000.00",
        })
        self.assertRedirects(edit, reverse("opportunities"))
        opportunity.refresh_from_db()
        self.assertEqual(opportunity.title, "Autovistoria atualizada")
        exported = self.client.get(reverse("records_export", args=("oportunidades", "csv")))
        self.assertEqual(exported.status_code, 200)
        self.assertIn("Autovistoria atualizada", exported.content.decode("utf-8-sig"))
        letter = self.client.get(reverse("opportunity_letter", args=(opportunity.pk,)))
        self.assertContains(letter, "MGT Engenharia")
        deleted = self.client.post(reverse("record_delete", args=("oportunidades", opportunity.pk)))
        self.assertRedirects(deleted, reverse("opportunities"))
        self.assertFalse(Opportunity.objects.filter(pk=opportunity.pk).exists())

    def test_project_and_task_pages_use_portuguese_labels(self):
        project = Project.objects.create(client=self.condominium, name="Obra", manager=self.user)
        Task.objects.create(project=project, title="Inspeção", assignee=self.user)
        self.assertContains(self.client.get(reverse("projects")), "Progresso (%)")
        self.assertContains(self.client.get(reverse("tasks")), "Concluída")

    def test_gazette_rejects_invalid_period(self):
        response = self.client.post(reverse("gazette_findings"), {"start_date": "2026-01-01", "end_date": "2026-03-01"}, follow=True)
        self.assertContains(response, "período válido de até 31 dias")
