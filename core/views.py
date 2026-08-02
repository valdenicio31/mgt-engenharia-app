from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import redirect, render
from .forms import ClientForm, OpportunityForm, ProjectForm, TaskForm
from .models import AuditLog, Client, Opportunity, Project, Proposal, RAT, Task

def health(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    return JsonResponse({"status": "ok", "service": "mgt-engenharia"})

@login_required
def dashboard(request):
    context = {
        "clients": Client.objects.filter(active=True).count(),
        "opportunities": Opportunity.objects.exclude(stage__in=["ganha", "perdida"]).count(),
        "projects": Project.objects.filter(status="em_execucao").count(),
        "pending_tasks": Task.objects.filter(completed=False).count(),
        "pipeline": Opportunity.objects.select_related("client", "owner").order_by("-updated_at")[:6],
        "recent_projects": Project.objects.select_related("client", "manager").order_by("-updated_at")[:5],
    }
    return render(request, "dashboard.html", context)

def _crud(request, model, form_class, title, template="generic_list.html"):
    form = form_class(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        if hasattr(obj, "owner_id") and not obj.owner_id: obj.owner = request.user
        if hasattr(obj, "manager_id") and not obj.manager_id: obj.manager = request.user
        if hasattr(obj, "assignee_id") and not obj.assignee_id: obj.assignee = request.user
        obj.save()
        AuditLog.objects.create(actor=request.user, action="criado", entity=model.__name__, entity_id=str(obj.pk))
        return redirect(request.path)
    return render(request, template, {"title": title, "items": model.objects.all().order_by("-updated_at")[:50], "form": form})

@login_required
def clients(request): return _crud(request, Client, ClientForm, "Clientes e condomínios")
@login_required
def opportunities(request): return _crud(request, Opportunity, OpportunityForm, "Oportunidades")
@login_required
def projects(request): return _crud(request, Project, ProjectForm, "Projetos")
@login_required
def tasks(request): return _crud(request, Task, TaskForm, "Tarefas")

@login_required
def proposals(request):
    return render(request, "simple_list.html", {"title": "Propostas", "items": Proposal.objects.select_related("opportunity")[:50]})

@login_required
def rats(request):
    return render(request, "simple_list.html", {"title": "RAT — Relatórios de Atendimento", "items": RAT.objects.select_related("project")[:50]})
