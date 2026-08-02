from django.contrib.auth import authenticate, get_user_model
from django.test import TestCase
from django.urls import reverse
from core.models import UserProfile

class AuthenticationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="internal", email="teste@example.com", password="SenhaForte!2026")
        UserProfile.objects.create(user=self.user, cpf="12345678901")
    def test_login_by_email(self):
        self.assertEqual(authenticate(username="TESTE@example.com", password="SenhaForte!2026"), self.user)
    def test_login_by_formatted_cpf(self):
        self.assertEqual(authenticate(username="123.456.789-01", password="SenhaForte!2026"), self.user)
    def test_first_access_creates_profile_and_logs_in(self):
        response = self.client.post(reverse("first_access"), {"full_name":"Maria da Silva","email":"maria@example.com","cpf":"987.654.321-00","password1":"SenhaSegura!2026","password2":"SenhaSegura!2026"})
        self.assertRedirects(response, reverse("dashboard"))
        self.assertTrue(UserProfile.objects.filter(cpf="98765432100", user__email="maria@example.com").exists())
    def test_duplicate_email_is_rejected(self):
        response = self.client.post(reverse("first_access"), {"full_name":"Outra Pessoa","email":"TESTE@example.com","cpf":"98765432100","password1":"SenhaSegura!2026","password2":"SenhaSegura!2026"})
        self.assertContains(response, "Este e-mail já está cadastrado")
    def test_password_reset_page_exists(self):
        self.assertEqual(self.client.get(reverse("password_reset")).status_code, 200)
