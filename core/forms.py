from django import forms
from .models import Client, Opportunity, Project, Task

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
