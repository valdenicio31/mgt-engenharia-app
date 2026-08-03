import re
import uuid
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.db import transaction
from .models import Client, Opportunity, Project, Proposal, RAT, Task, UserProfile

class EmailCPFAuthenticationForm(AuthenticationForm):
    username = forms.CharField(label="E-mail ou CPF", widget=forms.TextInput(attrs={"autofocus": True, "autocomplete": "username"}))
    password = forms.CharField(label="Senha", strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}))

class FirstAccessForm(UserCreationForm):
    full_name = forms.CharField(label="Nome completo", max_length=150)
    email = forms.EmailField(label="E-mail")
    cpf = forms.CharField(label="CPF", max_length=14)
    class Meta:
        model = get_user_model()
        fields = ("full_name", "email", "cpf", "password1", "password2")
    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Este e-mail já está cadastrado.")
        return email
    def clean_cpf(self):
        cpf = re.sub(r"\D", "", self.cleaned_data["cpf"])
        if len(cpf) != 11 or len(set(cpf)) == 1:
            raise forms.ValidationError("Informe um CPF válido com 11 dígitos.")
        if UserProfile.objects.filter(cpf=cpf).exists():
            raise forms.ValidationError("Este CPF já está cadastrado.")
        return cpf
    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        names = self.cleaned_data["full_name"].strip().split(maxsplit=1)
        user.first_name = names[0]
        user.last_name = names[1] if len(names) > 1 else ""
        user.email = self.cleaned_data["email"]
        user.username = f"user_{uuid.uuid4().hex[:20]}"
        if commit:
            user.save()
            UserProfile.objects.create(user=user, cpf=self.cleaned_data["cpf"])
        return user

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = (
            "name", "document", "email", "phone",
            "process_number", "publication_date", "notification_number",
            "street", "address_number", "complement", "neighborhood",
            "city", "state", "postal_code", "classification",
            "action_description", "validation", "active",
        )
        widgets = {
            "publication_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "action_description": forms.Textarea(attrs={"rows": 4}),
            "state": forms.TextInput(attrs={"maxlength": 2, "style": "text-transform:uppercase"}),
            "postal_code": forms.TextInput(attrs={"placeholder": "00000-000"}),
        }

    def clean(self):
        cleaned = super().clean()
        document = re.sub(r"\D", "", cleaned.get("document") or "")
        process = (cleaned.get("process_number") or "").strip()
        notification = (cleaned.get("notification_number") or "").strip()
        queryset = Client.objects.exclude(pk=self.instance.pk)
        duplicate_document = document and any(
            re.sub(r"\D", "", value or "") == document
            for value in queryset.values_list("document", flat=True)
        )
        if duplicate_document:
            self.add_error("document", "Já existe um cliente com este CNPJ/CPF.")
        if process and notification and queryset.filter(process_number__iexact=process, notification_number__iexact=notification).exists():
            self.add_error("notification_number", "Este processo e esta notificação já estão cadastrados.")
        return cleaned


class UserProfileForm(forms.ModelForm):
    first_name = forms.CharField(label="Nome", max_length=150)
    last_name = forms.CharField(label="Sobrenome", max_length=150, required=False)
    email = forms.EmailField(label="E-mail")

    class Meta:
        model = UserProfile
        fields = ("photo", "cpf", "phone", "birth_date", "street", "address_number", "complement", "neighborhood", "city", "state", "postal_code")
        widgets = {
            "birth_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "state": forms.TextInput(attrs={"maxlength": 2, "style": "text-transform:uppercase"}),
            "postal_code": forms.TextInput(attrs={"placeholder": "00000-000"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if user:
            self.fields["first_name"].initial = user.first_name
            self.fields["last_name"].initial = user.last_name
            self.fields["email"].initial = user.email

    def clean_cpf(self):
        cpf = re.sub(r"\D", "", self.cleaned_data["cpf"])
        if len(cpf) != 11 or len(set(cpf)) == 1:
            raise forms.ValidationError("Informe um CPF válido com 11 dígitos.")
        if UserProfile.objects.exclude(pk=self.instance.pk).filter(cpf=cpf).exists():
            raise forms.ValidationError("Este CPF já pertence a outro usuário.")
        return cpf

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if get_user_model().objects.exclude(pk=self.user.pk).filter(email__iexact=email).exists():
            raise forms.ValidationError("Este e-mail já pertence a outro usuário.")
        return email

    def clean_photo(self):
        photo = self.cleaned_data.get("photo")
        if photo and getattr(photo, "size", 0) > 3 * 1024 * 1024:
            raise forms.ValidationError("A foto deve ter no máximo 3 MB.")
        if photo:
            allowed = {"image/jpeg", "image/png", "image/webp"}
            content_type = getattr(photo, "content_type", "")
            if content_type not in allowed:
                raise forms.ValidationError("Use uma imagem JPG, PNG ou WEBP.")
            self._photo_bytes = photo.read()
            self._photo_content_type = content_type
            photo.seek(0)
        return photo

    @transaction.atomic
    def save(self, commit=True):
        profile = super().save(commit=False)
        self.user.first_name = self.cleaned_data["first_name"].strip()
        self.user.last_name = self.cleaned_data["last_name"].strip()
        self.user.email = self.cleaned_data["email"]
        if hasattr(self, "_photo_bytes"):
            profile.photo_data = self._photo_bytes
            profile.photo_content_type = self._photo_content_type
            profile.photo = ""
        elif self.cleaned_data.get("photo") is False:
            profile.photo_data = None
            profile.photo_content_type = ""
            profile.photo = ""
        if commit:
            self.user.save()
            profile.save()
        return profile

class OpportunityForm(forms.ModelForm):
    class Meta:
        model = Opportunity
        fields = ("client", "title", "stage", "estimated_value")

class LandingContactForm(forms.Form):
    name = forms.CharField(label="Nome", max_length=160)
    condominium = forms.CharField(label="Condomínio", max_length=160)
    email = forms.EmailField(label="E-mail")
    phone = forms.CharField(label="WhatsApp", max_length=30)
    service = forms.CharField(label="Serviço de interesse", max_length=180)
    consent = forms.BooleanField(label="Autorizo o contato da MGT Engenharia e o tratamento destes dados para atendimento.")

class ProposalForm(forms.ModelForm):
    class Meta:
        model = Proposal
        fields = ("opportunity", "number", "amount", "status", "valid_until")
        widgets = {"valid_until": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ("client", "name", "status", "progress")

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ("project", "title", "due_date", "execution_date", "start_time", "end_time", "planned_hours", "progress", "completed")
        widgets = {"due_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"), "execution_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"), "start_time": forms.TimeInput(attrs={"type": "time"}), "end_time": forms.TimeInput(attrs={"type": "time"})}

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("start_time"), cleaned.get("end_time")
        if start and end and end <= start:
            self.add_error("end_time", "A hora final deve ser posterior à hora inicial.")
        return cleaned

class RATForm(forms.ModelForm):
    class Meta:
        model = RAT
        fields = ("project", "service_date", "start_time", "end_time", "description", "notes", "next_steps", "status", "approved_by_client")
        widgets = {
            "service_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "start_time": forms.TimeInput(attrs={"type": "time"}), "end_time": forms.TimeInput(attrs={"type": "time"}),
            "description": forms.Textarea(attrs={"rows": 7}), "notes": forms.Textarea(attrs={"rows": 3}), "next_steps": forms.Textarea(attrs={"rows": 3}),
        }
