"""Documentos que vão para o cliente: valor do contrato e crédito do produtor."""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from core.models import (
    Client as Condominio, Measurement, Opportunity, Project,
    Proposal, RAT, UserProfile,
)


class ContratoValorTests(TestCase):
    """O contrato tem de sair com o valor da proposta ACEITA."""

    def setUp(self):
        self.admin = get_user_model().objects.create_user(
            username="chefe", email="chefe@example.com", password="SenhaForte!2026"
        )
        UserProfile.objects.create(user=self.admin, cpf="11111111111", role="admin")
        self.client.force_login(self.admin)
        self.condo = Condominio.objects.create(name="Cond. Contrato", document="00000000000191")
        self.op = Opportunity.objects.create(
            client=self.condo, title="Autovistoria", stage="ganha",
            owner=self.admin, estimated_value=Decimal("10000"),
        )

    def _contrato(self):
        return self.client.get(reverse("client_contract", args=[self.condo.pk]))

    def test_usa_valor_da_proposta_aceita(self):
        Proposal.objects.create(
            opportunity=self.op, number="PROP-1", amount=Decimal("48000"), status="aceita"
        )
        resposta = self._contrato()
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.context["total"], Decimal("48000"))
        # 30% de sinal e o saldo em 3 medições que fecham com o total
        self.assertEqual(resposta.context["sinal"], Decimal("14400.00"))
        valores = [v for _, _, v in resposta.context["medicoes"]]
        self.assertEqual(sum(valores), Decimal("48000.00"))
        self.assertNotContains(resposta, "preencher conforme proposta aceita")

    def test_ignora_proposta_nao_aceita_e_cai_no_estimado(self):
        Proposal.objects.create(
            opportunity=self.op, number="PROP-2", amount=Decimal("90000"), status="enviada"
        )
        resposta = self._contrato()
        self.assertEqual(resposta.context["total"], Decimal("10000"))

    def test_sem_proposta_nem_estimativa_nao_quebra(self):
        self.op.estimated_value = Decimal("0")
        self.op.save(update_fields=["estimated_value"])
        resposta = self._contrato()
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "preencher conforme proposta aceita")


class CreditoProdutorTests(TestCase):
    """O selo '@By ViaIA 2026' aparece em todas as telas e documentos."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="user", email="user@example.com", password="SenhaForte!2026"
        )
        UserProfile.objects.create(user=self.user, cpf="22222222222", role="admin")
        self.condo = Condominio.objects.create(name="Cond. Selo", document="00000000000191")
        self.op = Opportunity.objects.create(
            client=self.condo, title="Autovistoria", stage="ganha", owner=self.user
        )
        self.proj = Project.objects.create(
            client=self.condo, name="Projeto Selo", manager=self.user,
            start_date=date.today(), planned_end_date=date.today() + timedelta(days=10),
        )
        med = Measurement.objects.create(project=self.proj, number=1, amount=Decimal("100"))
        RAT.objects.create(
            project=self.proj, service_date=date.today(), description="Atendimento",
            technician=self.user, measurement=med,
        )

    def _tem_selo(self, resposta):
        corpo = resposta.content.decode()
        self.assertIn("@By", corpo)
        self.assertIn("ViaIA", corpo)
        self.assertIn("2026", corpo)

    def test_selo_nas_telas_publicas(self):
        for nome in ("autovistoria_landing", "login", "first_access", "password_reset"):
            with self.subTest(tela=nome):
                self._tem_selo(self.client.get(reverse(nome)))

    def test_selo_no_sistema_logado(self):
        self.client.force_login(self.user)
        self._tem_selo(self.client.get(reverse("dashboard")))

    def test_selo_nos_documentos_do_cliente(self):
        self.client.force_login(self.user)
        for nome, args in (
            ("client_contract", [self.condo.pk]),
            ("opportunity_letter", [self.op.pk]),
            ("project_report", [self.proj.pk]),
        ):
            with self.subTest(documento=nome):
                self._tem_selo(self.client.get(reverse(nome, args=args)))

    def test_grafia_antiga_nao_sobrou(self):
        self.client.force_login(self.user)
        for resposta in (
            self.client.get(reverse("dashboard")),
            self.client.get(reverse("client_contract", args=[self.condo.pk])),
            self.client.get(reverse("autovistoria_landing")),
        ):
            corpo = resposta.content.decode()
            self.assertNotIn("Criação ViaIA Soluções", corpo)
            self.assertNotIn("By VIA IA ©", corpo)
            self.assertNotIn("Desenvolvido por", corpo)
