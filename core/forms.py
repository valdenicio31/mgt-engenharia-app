import re
import uuid
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.db import transaction
from .models import AutovistoriaInfraction, Client, LandingLead, Opportunity, Project, Proposal, Task, UserProfile

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
            "photo", "name", "document", "email", "phone",
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

    def clean_photo(self):
        photo = self.cleaned_data.get("photo")
        if photo and getattr(photo, "size", 0) > 5 * 1024 * 1024:
            raise forms.ValidationError("A foto do condomínio deve ter no máximo 5 MB.")
        return photo

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
        return photo

    @transaction.atomic
    def save(self, commit=True):
        profile = super().save(commit=False)
        self.user.first_name = self.cleaned_data["first_name"].strip()
        self.user.last_name = self.cleaned_data["last_name"].strip()
        self.user.email = self.cleaned_data["email"]
        if commit:
            self.user.save()
            profile.save()
        return profile


class AutovistoriaInfractionForm(forms.ModelForm):
    class Meta:
        model = AutovistoriaInfraction
        fields = ("communication_number", "infraction_number", "infraction_type", "description", "infraction_date", "status", "source_url")
        widgets = {
            "infraction_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "description": forms.Textarea(attrs={"rows": 5, "placeholder": "Copie ou descreva a exigência exibida no portal da Prefeitura."}),
        }


class OpportunityForm(forms.ModelForm):
    class Meta:
        model = Opportunity
        fields = ("client", "title", "stage", "estimated_value")

class LandingLeadForm(forms.ModelForm):
    lgpd_consent = forms.BooleanField(
        label="Autorizo a MGT Engenharia a utilizar estes dados para preparar o orçamento e entrar em contato.",
        required=True,
    )

    class Meta:
        model = LandingLead
        exclude = ("source", "client", "opportunity")
        widgets = {
            "address": forms.TextInput(attrs={"placeholder": "Rua, número, complemento, bairro e cidade"}),
            "postal_code": forms.TextInput(attrs={"placeholder": "00000-000"}),
            "other": forms.Textarea(attrs={"rows": 3, "placeholder": "Informe outras características relevantes"}),
            "built_area": forms.NumberInput(attrs={"min": 0, "step": "0.01"}),
        }

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
        fields = ("project", "title", "due_date", "completed")
        widgets = {"due_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}
