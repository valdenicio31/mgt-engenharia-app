"""Varredura de TODAS as telas do sistema, com cada papel.

Motivo: o smoke test do RC28 na homologação encontrou um erro 500 no
cadastro público que nenhum dos 44 testes existentes pegava — eles
cobriam regras de negócio e permissões, mas ninguém simplesmente abria
cada tela para ver se ela responde. Esta varredura fecha essa lacuna:
percorre todas as rotas com admin, comercial, técnico e anônimo, e
falha se QUALQUER uma devolver 5xx.

Um 403 (bloqueio por papel) ou 302 (redirect de login) é resultado
esperado e não quebra o teste — o que não se admite é erro de servidor.
"""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from core.models import (
    Client as Condominio,
    GazetteFinding,
    Measurement,
    Opportunity,
    Project,
    Proposal,
    RAT,
    Resource,
    Task,
    UserProfile,
)


def _usuario(username, role, cpf):
    user = get_user_model().objects.create_user(
        username=username, email=f"{username}@example.com", password="SenhaForte!2026"
    )
    UserProfile.objects.create(user=user, cpf=cpf, role=role)
    return user


class VarreduraDeTelas(TestCase):
    """Abre cada tela com cada papel e exige que nenhuma quebre."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = _usuario("varre_admin", "admin", "11111111111")
        cls.comercial = _usuario("varre_comercial", "comercial", "22222222222")
        cls.tecnico = _usuario("varre_tecnico", "tecnico", "33333333333")

        cls.condo = Condominio.objects.create(
            name="Condomínio da Varredura", document="00000000000191",
            street="Rua do Teste", city="Rio de Janeiro", state="RJ",
        )
        cls.oportunidade = Opportunity.objects.create(
            client=cls.condo, title="Autovistoria do prédio",
            stage="lead", owner=cls.comercial,
        )
        Proposal.objects.create(
            opportunity=cls.oportunidade, number="PROP-VARRE-1", amount=10000,
        )
        cls.projeto = Project.objects.create(
            client=cls.condo, name="Projeto da Varredura", manager=cls.admin,
            start_date=date.today(), planned_end_date=date.today() + timedelta(days=30),
        )
        Task.objects.create(
            project=cls.projeto, title="Tarefa da varredura", assignee=cls.tecnico,
        )
        cls.medicao = Measurement.objects.create(
            project=cls.projeto, number=1, amount=3000,
        )
        RAT.objects.create(
            project=cls.projeto, service_date=date.today(),
            description="Atendimento da varredura", technician=cls.tecnico,
            measurement=cls.medicao,
        )
        Resource.objects.create(name="Engenheiro da varredura", resource_type="humano")
        GazetteFinding.objects.create(
            publication_date=date.today(), edition_id="1", page=1,
            condominium_name="Condomínio da Varredura", notification_number="123/2026",
            address="Rua do Teste, 1", source_url="https://example.com/diario",
        )

    def _telas(self):
        """(nome legível, url) de tudo que o usuário alcança pelo menu."""
        return [
            ("Visão geral", reverse("dashboard")),
            ("Diário Oficial", reverse("gazette_findings")),
            ("Oportunidades", reverse("opportunities")),
            ("Clientes", reverse("clients")),
            ("Propostas", reverse("proposals")),
            ("Projetos", reverse("projects")),
            ("Tarefas", reverse("tasks")),
            ("Recursos", reverse("resources")),
            ("Alocações", reverse("allocations")),
            ("RAT", reverse("rats")),
            ("Medições", reverse("measurements")),
            ("Equipe", reverse("team")),
            ("Meu cadastro", reverse("profile")),
            ("Ajuda", reverse("help_center")),
            ("Landing", reverse("autovistoria_landing")),
            ("Contrato do cliente", reverse("client_contract", args=[self.condo.pk])),
            ("Carta da oportunidade", reverse("opportunity_letter", args=[self.oportunidade.pk])),
            ("Laudo do projeto", reverse("project_report", args=[self.projeto.pk])),
            ("Exportar clientes (csv)", reverse("records_export", args=["clientes", "csv"])),
            ("Exportar oportunidades (xlsx)", reverse("records_export", args=["oportunidades", "xlsx"])),
        ]

    def _varre(self, papel, usuario=None):
        if usuario is not None:
            self.client.force_login(usuario)
        else:
            self.client.logout()
        quebradas = []
        for nome, url in self._telas():
            resposta = self.client.get(url)
            if resposta.status_code >= 500:
                quebradas.append(f"{nome} ({url}) -> {resposta.status_code}")
        self.assertEqual(
            quebradas, [], f"Telas com erro de servidor para o papel '{papel}': {quebradas}"
        )

    def test_todas_as_telas_respondem_para_admin(self):
        self._varre("admin", self.admin)

    def test_todas_as_telas_respondem_para_comercial(self):
        self._varre("comercial", self.comercial)

    def test_todas_as_telas_respondem_para_tecnico(self):
        self._varre("tecnico", self.tecnico)

    def test_telas_nao_quebram_para_anonimo(self):
        # Anônimo deve ser redirecionado para o login, nunca ver erro 500.
        self._varre("anônimo")

    def test_telas_publicas_abrem_sem_login(self):
        self.client.logout()
        for nome, url in [
            ("Landing", reverse("autovistoria_landing")),
            ("Apresentação", reverse("presentation")),
            ("Primeiro acesso", reverse("first_access")),
            ("Login", reverse("login")),
            ("Recuperar senha", reverse("password_reset")),
            ("Health check", reverse("health")),
        ]:
            with self.subTest(tela=nome):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_menu_do_tecnico_esconde_o_que_ele_nao_pode(self):
        self.client.force_login(self.tecnico)
        corpo = self.client.get(reverse("dashboard")).content.decode()
        self.assertNotIn(reverse("team"), corpo)

    def test_menu_do_admin_mostra_equipe(self):
        self.client.force_login(self.admin)
        corpo = self.client.get(reverse("dashboard")).content.decode()
        self.assertIn(reverse("team"), corpo)
