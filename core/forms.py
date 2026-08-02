import re
import uuid
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.db import transaction
from .models import Client, Opportunity, Project, Task, UserProfile

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
        fields = ("name", "document", "email", "phone", "active")

class OpportunityForm(forms.ModelForm):
    class Meta:
        model = Opportunity
        fields = ("client", "title", "stage", "estimated_value")

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ("client", "name", "status", "progress")

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ("project", "title", "due_date", "completed")
