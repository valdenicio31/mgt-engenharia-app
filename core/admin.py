from django.contrib import admin
from .models import AuditLog, Client, Opportunity, Project, Proposal, RAT, Task

admin.site.site_header = "MGT Engenharia — Administração"
for model in (Client, Opportunity, Proposal, Project, Task, RAT, AuditLog):
    admin.site.register(model)
