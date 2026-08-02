from django.urls import path
from . import views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("", views.dashboard, name="dashboard"),
    path("clientes/", views.clients, name="clients"),
    path("oportunidades/", views.opportunities, name="opportunities"),
    path("propostas/", views.proposals, name="proposals"),
    path("projetos/", views.projects, name="projects"),
    path("tarefas/", views.tasks, name="tasks"),
    path("rats/", views.rats, name="rats"),
]
