"""Testes dos papéis e permissões do RC26 (admin/comercial/técnico)."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from core.models import Client, UserProfile
from core.permissions import user_role


def _make_user(username, role, cpf, active=True, superuser=False):
    User = get_user_model()
    factory = User.objects.create_superuser if superuser else User.objects.create_user
    user = factory(username=username, email=f"{username}@example.com", password="SenhaForte!2026")
    user.is_active = active
    user.save(update_fields=("is_active",))
    UserProfile.objects.create(user=user, cpf=cpf, role=role)
    return user


class RoleTests(TestCase):
    def setUp(self):
        self.admin = _make_user("chefe", "admin", "11111111111")
        self.comercial = _make_user("vendas", "comercial", "22222222222")
        self.tecnico = _make_user("campo", "tecnico", "33333333333")
        self.condo = Client.objects.create(name="Cond. Teste", document="00000000000191")

    def test_superuser_is_admin(self):
        root = _make_user("root", "tecnico", "44444444444", superuser=True)
        self.assertEqual(user_role(root), "admin")

    def test_delete_requires_admin(self):
        url = reverse("record_delete", args=["clientes", self.condo.pk])
        self.client.force_login(self.tecnico)
        self.assertEqual(self.client.post(url).status_code, 403)
        self.client.force_login(self.comercial)
        self.assertEqual(self.client.post(url).status_code, 403)
        self.client.force_login(self.admin)
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Client.objects.filter(pk=self.condo.pk).exists())

    def test_export_blocked_for_tecnico(self):
        url = reverse("records_export", args=["clientes", "csv"])
        self.client.force_login(self.tecnico)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.comercial)
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_clients_import_blocked_for_tecnico(self):
        self.client.force_login(self.tecnico)
        self.assertEqual(self.client.post(reverse("clients_import")).status_code, 403)

    def test_gazette_run_blocked_for_tecnico(self):
        self.client.force_login(self.tecnico)
        self.assertEqual(self.client.post(reverse("gazette_findings"), {}).status_code, 403)
        # consultar a lista continua liberado
        self.assertEqual(self.client.get(reverse("gazette_findings")).status_code, 200)


class TeamScreenTests(TestCase):
    def setUp(self):
        self.admin = _make_user("chefe", "admin", "11111111111")
        self.pendente = _make_user("novato", "tecnico", "55555555555", active=False)

    def test_team_requires_admin(self):
        comercial = _make_user("vendas", "comercial", "22222222222")
        self.client.force_login(comercial)
        self.assertEqual(self.client.get(reverse("team")).status_code, 403)

    def test_admin_approves_user_with_role(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("team"), {"usuario": self.pendente.pk, "acao": "aprovar", "papel": "comercial"})
        self.assertRedirects(response, reverse("team"))
        self.pendente.refresh_from_db()
        self.assertTrue(self.pendente.is_active)
        self.assertEqual(self.pendente.profile.role, "comercial")

    def test_admin_cannot_deactivate_self(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("team"), {"usuario": self.admin.pk, "acao": "desativar"})
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_admin_deactivates_other_user(self):
        ativo = _make_user("saindo", "tecnico", "66666666666")
        self.client.force_login(self.admin)
        self.client.post(reverse("team"), {"usuario": ativo.pk, "acao": "desativar"})
        ativo.refresh_from_db()
        self.assertFalse(ativo.is_active)
