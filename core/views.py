from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import connection
import csv
import io
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from urllib.parse import quote
from openpyxl import Workbook
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .forms import ClientForm, FirstAccessForm, LandingContactForm, OpportunityForm, ProjectForm, ProposalForm, RATForm, TaskForm, UserProfileForm
from .client_io import export_clients, import_clients
from .gazette import fetch_notifications
from .models import AuditLog, Client, GazetteFinding, Opportunity, Project, Proposal, RAT, RATRevision, Task
from .models import UserProfile

def health(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    return JsonResponse({"status": "ok", "service": "mgt-engenharia"})

def landing_page(request):
    form = LandingContactForm(request.POST or None)
    sent = False
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        client, _ = Client.objects.get_or_create(
            email__iexact=data["email"],
            defaults={"name": data["condominium"], "email": data["email"], "phone": data["phone"], "action_description": f"Contato: {data['name']} — origem: Landing Page"},
        )
        if not client.phone:
            client.phone = data["phone"]; client.save(update_fields=("phone", "updated_at"))
        owner = get_user_model().objects.filter(is_superuser=True).first() or get_user_model().objects.first()
        if owner:
            Opportunity.objects.create(client=client, title=data["service"], owner=owner, source="landing_page")
            AuditLog.objects.create(actor=None, action="lead_landing_page", entity="Opportunity", entity_id=str(client.pk), details={"contato": data["name"], "consentimento": True})
            sent = True
            form = LandingContactForm()
    return render(request, "landing_page.html", {"contact_email": settings.MGT_CONTACT_EMAIL, "whatsapp": settings.MGT_WHATSAPP, "form": form, "sent": sent})

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

@login_required
def profile_photo(request):
    profile_obj = get_object_or_404(UserProfile, user=request.user)
    if not profile_obj.photo_data:
        return HttpResponse(status=404)
    response = HttpResponse(bytes(profile_obj.photo_data), content_type=profile_obj.photo_content_type or "image/jpeg")
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response

def _crud(request, model, form_class, title, template="generic_list.html"):
    edit_id = request.GET.get("editar")
    instance = get_object_or_404(model, pk=edit_id) if edit_id else None
    form = form_class(request.POST or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        if hasattr(obj, "owner_id") and not obj.owner_id: obj.owner = request.user
        if hasattr(obj, "manager_id") and not obj.manager_id: obj.manager = request.user
        if hasattr(obj, "assignee_id") and not obj.assignee_id: obj.assignee = request.user
        obj.save()
        action = "alterado" if instance else "criado"
        AuditLog.objects.create(actor=request.user, action=action, entity=model.__name__, entity_id=str(obj.pk))
        messages.success(request, "Registro atualizado com sucesso." if instance else "Registro criado com sucesso.")
        return redirect(request.path)
    resource = {Client: "clientes", Opportunity: "oportunidades", Proposal: "propostas", Project: "projetos", Task: "tarefas"}[model]
    return render(request, template, {"title": title, "items": model.objects.all().order_by("-updated_at")[:50], "form": form, "editing": instance, "resource": resource})

@login_required
def clients(request): return _crud(request, Client, ClientForm, "Clientes e condomínios", "clients.html")

CRUD_MODELS = {"clientes": Client, "oportunidades": Opportunity, "propostas": Proposal, "projetos": Project, "tarefas": Task, "rats": RAT}

@login_required
@require_POST
def record_delete(request, resource, pk):
    model = CRUD_MODELS.get(resource)
    if not model:
        return HttpResponse("Recurso inválido.", status=404)
    obj = get_object_or_404(model, pk=pk)
    try:
        label = str(obj)
        obj.delete()
        AuditLog.objects.create(actor=request.user, action="excluido", entity=model.__name__, entity_id=str(pk), details={"registro": label})
        messages.success(request, "Registro excluído com sucesso.")
    except Exception:
        messages.error(request, "Este registro está relacionado a outros dados e não pode ser excluído.")
    return redirect(f"/{resource}/")

def _generic_export(model, fmt, queryset=None):
    fields = [f for f in model._meta.fields if f.name not in {"id", "created_at", "updated_at"}]
    headers = [str(f.verbose_name).title() for f in fields]
    rows = []
    for obj in (queryset if queryset is not None else model.objects.all()):
        values = []
        for field in fields:
            display = getattr(obj, f"get_{field.name}_display", None)
            value = display() if display else getattr(obj, field.name)
            if hasattr(value, "strftime"): value = value.strftime("%d/%m/%Y")
            values.append(str(value) if value is not None else "")
        rows.append(values)
    if fmt == "xlsx":
        workbook = Workbook(); sheet = workbook.active; sheet.append(headers)
        for row in rows: sheet.append(row)
        output = io.BytesIO(); workbook.save(output)
        return output.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    if fmt in {"csv", "txt"}:
        output = io.StringIO(); writer = csv.writer(output, delimiter=";" if fmt == "csv" else "\t", lineterminator="\n"); writer.writerow(headers); writer.writerows(rows)
        return output.getvalue().encode("utf-8-sig"), "text/csv" if fmt == "csv" else "text/plain"
    if fmt == "xml":
        root = ET.Element(model._meta.model_name)
        for row in rows:
            node = ET.SubElement(root, "registro")
            for header, value in zip(headers, row): ET.SubElement(node, "campo", nome=header).text = value
        return ET.tostring(root, encoding="utf-8", xml_declaration=True), "application/xml"
    raise ValueError("Formato inválido")

@login_required
def records_export(request, resource, fmt):
    model = CRUD_MODELS.get(resource)
    if not model or fmt not in {"xlsx", "csv", "txt", "xml"}: return HttpResponse("Exportação inválida.", status=400)
    queryset = model.objects.all()
    ids = request.GET.get("ids", "").strip()
    if ids:
        queryset = queryset.filter(pk__in=[value for value in ids.split(",") if value.isdigit()])
    content, content_type = _generic_export(model, fmt, queryset)
    response = HttpResponse(content, content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="MGT_{resource}.{fmt}"'
    return response

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
    queryset = Client.objects.all()
    ids = request.GET.get("ids", "").strip()
    if ids:
        queryset = queryset.filter(pk__in=[value for value in ids.split(",") if value.isdigit()])
    try:
        content, content_type = export_clients(fmt.lower(), queryset)
    except ValueError as exc:
        return HttpResponse(str(exc), status=400)
    filename = f"MGT_Engenharia_Condominios.{fmt.lower()}"
    response = HttpResponse(content, content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
@login_required
def opportunities(request): return _crud(request, Opportunity, OpportunityForm, "Oportunidades", "opportunities.html")

@login_required
def opportunity_letter(request, pk):
    opportunity = get_object_or_404(Opportunity.objects.select_related("client", "owner"), pk=pk)
    return render(request, "opportunity_letter.html", {"opportunity": opportunity})
@login_required
def projects(request): return _crud(request, Project, ProjectForm, "Projetos")
@login_required
def tasks(request): return _crud(request, Task, TaskForm, "Tarefas")

@login_required
def proposals(request): return _crud(request, Proposal, ProposalForm, "Propostas")

def _rat_snapshot(rat):
    return {"project": str(rat.project), "service_date": rat.service_date.isoformat(), "start_time": str(rat.start_time or ""), "end_time": str(rat.end_time or ""), "total_hours": str(rat.total_hours), "description": rat.description, "notes": rat.notes, "next_steps": rat.next_steps, "status": rat.status, "approved_by_client": rat.approved_by_client}

@login_required
def rats(request):
    edit_id = request.GET.get("editar")
    instance = get_object_or_404(RAT, pk=edit_id) if edit_id else None
    original_snapshot = _rat_snapshot(instance) if instance else None
    initial = {"service_date": datetime.now().date(), "status": "rascunho"}
    if request.GET.get("gerar") == "hoje" and request.GET.get("projeto"):
        project = get_object_or_404(Project, pk=request.GET["projeto"])
        tasks = list(project.tasks.filter(execution_date=datetime.now().date()).order_by("start_time"))
        starts = [task.start_time for task in tasks if task.start_time]
        ends = [task.end_time for task in tasks if task.end_time]
        initial.update({"project": project, "start_time": min(starts) if starts else None, "end_time": max(ends) if ends else None, "description": "\n".join(f"• {task.title} — {task.progress}% concluída ({task.executed_hours}h)" for task in tasks) or "Atividades realizadas no atendimento do dia."})
    form = RATForm(request.POST or None, instance=instance, initial=initial if not instance else None)
    if request.method == "POST" and form.is_valid():
        rat = form.save(commit=False); rat.technician = instance.technician if instance else request.user
        if instance:
            RATRevision.objects.create(rat=instance, version=instance.version, snapshot=original_snapshot, changed_by=request.user)
            rat.version += 1
        rat.save()
        AuditLog.objects.create(actor=request.user, action="rat_alterada" if instance else "rat_gerada", entity="RAT", entity_id=str(rat.pk), details={"versao": rat.version})
        messages.success(request, "RAT atualizada com nova versão." if instance else "RAT do dia gerada com sucesso.")
        return redirect("rats")
    return render(request, "rats.html", {"title": "RAT — Relatórios de Atendimento", "items": RAT.objects.select_related("project", "technician").order_by("-service_date", "-created_at")[:100], "form": form, "editing": instance, "projects": Project.objects.all()})

@login_required
def rat_document(request, pk):
    rat = get_object_or_404(RAT.objects.select_related("project__client", "technician"), pk=pk)
    tasks = list(rat.project.tasks.all())
    planned = round(sum(float(task.planned_hours or 0) for task in tasks), 2)
    executed = round(sum(float(task.executed_hours or 0) for task in tasks), 2)
    remaining = round(max(0, planned - executed), 2)
    return render(request, "rat_document.html", {"rat": rat, "planned_hours": planned, "executed_hours": executed, "remaining_hours": remaining})

@login_required
def gazette_findings(request):
    if request.method == "POST":
        try:
            start_raw, end_raw = request.POST.get("start_date"), request.POST.get("end_date")
            end_date = datetime.strptime(end_raw, "%Y-%m-%d").date() if end_raw else None
            start_date = datetime.strptime(start_raw, "%Y-%m-%d").date() if start_raw else end_date
            if start_date and end_date and (end_date < start_date or (end_date - start_date).days > 31):
                raise ValueError("Escolha um período válido de até 31 dias.")
            dates = [None] if not start_date else [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]
            all_findings = []
            for selected_date in dates:
                try:
                    _, day_findings = fetch_notifications(selected_date)
                    all_findings.extend(day_findings)
                except Exception:
                    continue
            findings = all_findings
            created = 0
            for item in findings:
                _, was_created = GazetteFinding.objects.get_or_create(
                    edition_id=item["edition_id"], notification_number=item["notification_number"], defaults=item
                )
                created += int(was_created)
            period = f"{start_date:%d/%m/%Y} a {end_date:%d/%m/%Y}" if start_date else "edição mais recente"
            AuditLog.objects.create(actor=request.user, action="pesquisa_diario_oficial", entity="GazetteFinding", entity_id=period, details={"localizados": len(findings), "novos": created})
            messages.success(request, f"Período {period}: {len(findings)} notificações localizadas, {created} novas.")
        except ValueError as exc:
            messages.error(request, str(exc))
        except Exception:
            messages.error(request, "Não foi possível consultar o Diário Oficial agora. Tente novamente em alguns minutos.")
        return redirect("gazette_findings")
    return render(request, "gazette_findings.html", {"items": GazetteFinding.objects.all()[:200]})
