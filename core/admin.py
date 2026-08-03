from django.contrib import admin
from .models import AuditLog, Client, GazetteFinding, Opportunity, Project, Proposal, RAT, Task

admin.site.site_header = "MGT Engenharia — Administração"
for model in (Client, Opportunity, Proposal, Project, Task, RAT, GazetteFinding, AuditLog):
    admin.site.register(model)
