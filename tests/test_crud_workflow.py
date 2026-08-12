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

    # Na versão 1.0 a conversão em massa foi desativada: oportunidade de
    # Autovistoria só nasce depois da consulta ao portal com autuação
    # registrada (fluxo Diário Oficial → consulta → autuações → oportunidade).
    def test_bulk_conversion_shortcut_is_disabled_with_selection(self):
        second = Client.objects.create(name="Condomínio Segundo")
        response = self.client.post(
            reverse("clients_to_opportunities"),
            {"client_ids": [self.condominium.pk, second.pk]},
            follow=True,
        )
        self.assertContains(response, "A criação direta foi desativada")
        self.assertEqual(Opportunity.objects.count(), 0)

    def test_bulk_conversion_shortcut_is_disabled_without_selection(self):
        response = self.client.post(reverse("clients_to_opportunities"), follow=True)
        self.assertContains(response, "A criação direta foi desativada")
        self.assertEqual(Opportunity.objects.count(), 0)

    def test_autovistoria_workflow_creates_and_updates_without_duplicate(self):
        self.condominium.street = "Rua das Flores"
        self.condominium.address_number = "100"
        self.condominium.neighborhood = "Centro"
        self.condominium.save()
        page = self.client.get(reverse("client_autovistoria", args=(self.condominium.pk,)))
        self.assertContains(page, "Rua das Flores")
        self.assertContains(page, "Abrir manualmente")
        # fluxo atual: registrar ao menos uma autuação e só então gerar a oportunidade
        payload = {
            "communication_number": "COM-123",
            "infraction_number": "AUT-001",
            "infraction_type": "Fachada",
            "description": "Recuperar revestimento da fachada.",
            "status": "ativa",
            "source_url": "https://autovistoria.rio.rj.gov.br/ConsultaPublica.php",
        }
        self.client.post(reverse("client_autovistoria", args=(self.condominium.pk,)), payload, follow=True)
        self.assertEqual(self.condominium.autovistoria_infractions.count(), 1)

        response = self.client.post(
            reverse("client_autovistoria_create_opportunity", args=(self.condominium.pk,)), follow=True
        )
        self.assertContains(response, "Oportunidade criada com 1 autuação(ões)")
        opportunity = Opportunity.objects.get(client=self.condominium, communication_number="COM-123")
        self.assertEqual(opportunity.source, "Autovistoria Rio")
        self.assertEqual(opportunity.title, "Autovistoria — Condomínio Teste")

        # nova autuação + nova geração deve ATUALIZAR a mesma oportunidade, sem duplicar
        payload["infraction_number"] = "AUT-002"
        payload["description"] = "Revisar para-raios."
        self.client.post(reverse("client_autovistoria", args=(self.condominium.pk,)), payload, follow=True)
        response = self.client.post(
            reverse("client_autovistoria_create_opportunity", args=(self.condominium.pk,)), follow=True
        )
        self.assertContains(response, "Oportunidade atualizada com 1 autuação(ões)")
        self.assertEqual(Opportunity.objects.filter(client=self.condominium).count(), 1)
