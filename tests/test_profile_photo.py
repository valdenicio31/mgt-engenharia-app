from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from core.models import UserProfile


class ProfilePhotoTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="foto", email="foto@example.com", password="SenhaForte123")
        self.profile = UserProfile.objects.create(user=self.user, cpf="12345678901")
        self.client.force_login(self.user)

    def _image(self):
        output = BytesIO()
        Image.new("RGB", (20, 20), "purple").save(output, format="PNG")
        return SimpleUploadedFile("perfil.png", output.getvalue(), content_type="image/png")

    def test_photo_is_saved_in_database_and_served_to_owner(self):
        response = self.client.post(reverse("profile"), {
            "first_name": "Valdenicio", "last_name": "Teste", "email": "foto@example.com", "cpf": "12345678901",
            "phone": "", "birth_date": "", "street": "", "address_number": "", "complement": "",
            "neighborhood": "", "city": "Rio de Janeiro", "state": "RJ", "postal_code": "", "photo": self._image(),
        })
        self.assertRedirects(response, reverse("profile"))
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.photo_data)
        self.assertFalse(self.profile.photo.name)
        photo = self.client.get(reverse("profile_photo"))
        self.assertEqual(photo.status_code, 200)
        self.assertEqual(photo["Content-Type"], "image/png")

    def test_photo_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("profile_photo"))
        self.assertEqual(response.status_code, 302)
