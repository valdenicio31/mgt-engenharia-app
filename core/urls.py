from django.urls import path
from . import views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("primeiro-acesso/", views.first_access, name="first_access"),
    path("meu-cadastro/", views.profile, name="profile"),
    path("", views.dashboard, name="dashboard"),
    path("clientes/", views.clients, name="clients"),
    path("clientes/importar/", views.clients_import, name="clients_import"),
    path("clientes/exportar/<str:fmt>/", views.clients_export, name="clients_export"),
    path("<str:resource>/exportar/<str:fmt>/", views.records_export, name="records_export"),
    path("<str:resource>/<int:pk>/excluir/", views.record_delete, name="record_delete"),
    path("oportunidades/", views.opportunities, name="opportunities"),
    path("oportunidades/<int:pk>/carta/", views.opportunity_letter, name="opportunity_letter"),
    path("propostas/", views.proposals, name="proposals"),
    path("projetos/", views.projects, name="projects"),
    path("tarefas/", views.tasks, name="tasks"),
    path("rats/", views.rats, name="rats"),
    path("diario-oficial/", views.gazette_findings, name="gazette_findings"),
]
