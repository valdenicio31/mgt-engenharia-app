from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from .forms import ClientForm, FirstAccessForm, OpportunityForm, ProjectForm, TaskForm, UserProfileForm
from .client_io import export_clients, import_clients
from .gazette import fetch_notifications
from .models import AuditLog, Client, GazetteFinding, Opportunity, Project, Proposal, RAT, Task
from .models import UserProfile

def health(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    return JsonResponse({"status": "ok", "service": "mgt-engenharia"})

def first_access(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = FirstAccessForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="core.authentication.EmailOrCPFBackend")
        AuditLog.objects.create(actor=user, action="primeiro_acesso", entity="User", entity_id=str(user.pk))
        return redirect("dashboard")
    return render(request, "registration/first_access.html", {"form": form})

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

@login_required
def profile(request):
    profile_obj, _ = UserProfile.objects.get_or_create(user=request.user, defaults={"cpf": f"{request.user.pk:011d}"[-11:]})
    form = UserProfileForm(request.POST or None, request.FILES or None, instance=profile_obj, user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        AuditLog.objects.create(actor=request.user, action="atualizacao_perfil", entity="UserProfile", entity_id=str(profile_obj.pk))
        messages.success(request, "Seus dados foram atualizados com sucesso.")
        return redirect("profile")
    return render(request, "profile.html", {"form": form, "profile": profile_obj})

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
def clients(request): return _crud(request, Client, ClientForm, "Clientes e condomínios", "clients.html")

@login_required
def clients_import(request):
    if request.method != "POST" or "file" not in request.FILES:
        messages.error(request, "Selecione um arquivo para importar.")
        return redirect("clients")
    upload = request.FILES["file"]
    if upload.size > 5 * 1024 * 1024:
        messages.error(request, "O arquivo excede o limite de 5 MB.")
        return redirect("clients")
    try:
        created, updated, errors = import_clients(upload)
        AuditLog.objects.create(actor=request.user, action="importacao_clientes", entity="Client", entity_id=upload.name, details={"incluidos": created, "atualizados": updated, "erros": errors[:20]})
        messages.success(request, f"Importação concluída: {created} incluídos e {updated} atualizados.")
        if errors:
            messages.warning(request, f"{len(errors)} linha(s) não foram importadas. Primeiro erro: {errors[0]}")
    except Exception as exc:
        messages.error(request, f"Não foi possível importar: {exc}")
    return redirect("clients")

@login_required
def clients_export(request, fmt):
    try:
        content, content_type = export_clients(fmt.lower())
    except ValueError as exc:
        return HttpResponse(str(exc), status=400)
    filename = f"MGT_Engenharia_Condominios.{fmt.lower()}"
    response = HttpResponse(content, content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
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

@login_required
def gazette_findings(request):
    if request.method == "POST":
        try:
            publication_date, findings = fetch_notifications()
            created = 0
            for item in findings:
                _, was_created = GazetteFinding.objects.get_or_create(
                    edition_id=item["edition_id"], notification_number=item["notification_number"], defaults=item
                )
                created += int(was_created)
            AuditLog.objects.create(actor=request.user, action="pesquisa_diario_oficial", entity="GazetteFinding", entity_id=str(publication_date), details={"localizados": len(findings), "novos": created})
            messages.success(request, f"Edição de {publication_date:%d/%m/%Y}: {len(findings)} notificações localizadas, {created} novas.")
        except Exception:
            messages.error(request, "Não foi possível consultar o Diário Oficial agora. Tente novamente em alguns minutos.")
        return redirect("gazette_findings")
    return render(request, "gazette_findings.html", {"items": GazetteFinding.objects.all()[:200]})
