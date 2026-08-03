from django.contrib import admin
from .models import AuditLog, AutovistoriaInfraction, Client, GazetteFinding, LandingLead, Opportunity, Project, Proposal, RAT, Task

admin.site.site_header = "MGT Engenharia — Administração"
for model in (Client, AutovistoriaInfraction, LandingLead, Opportunity, Proposal, Project, Task, RAT, GazetteFinding, AuditLog):
    admin.site.register(model)
