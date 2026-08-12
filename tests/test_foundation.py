from django.test import TestCase
from django.urls import reverse

class FoundationTests(TestCase):
    def test_login_page_renders(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "MGT_LOGIN_OFICIAL_RECONSTRUCAO_V1")

    def test_dashboard_redirects_anonymous(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
