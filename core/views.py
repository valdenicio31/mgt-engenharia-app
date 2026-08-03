from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.mail import send_mail
from django.db import connection, transaction
import csv
import io
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from urllib.parse import quote
from openpyxl import Workbook
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .forms import ClientForm, FirstAccessForm, LandingLeadForm, OpportunityForm, ProjectForm, ProposalForm, TaskForm, UserProfileForm
from .client_io import export_clients, import_clients
from .gazette import fetch_notifications
from .models import AuditLog, Client, GazetteFinding, LandingLead, Opportunity, Project, Proposal, RAT, Task
from .models import UserProfile

def health(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    return JsonResponse({"status": "ok", "service": "mgt-engenharia"})

def autovistoria_landing(request):
    form = LandingLeadForm(request.POST or None)
    submitted = False
    whatsapp_url = "https://wa.me/5521975164643"
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            lead = form.save()
            document = "".join(char for char in lead.document if char.isdigit())
            client = None
            if document:
                client = next((item for item in Client.objects.exclude(document="") if "".join(char for char in item.document if char.isdigit()) == document), None)
            if not client:
                client = Client.objects.filter(email__iexact=lead.email).first()
            details = (
                f"Captação passiva pela Landing Page de Autovistoria. Síndico(a): {lead.syndic_name}. "
                f"Prédio: {lead.building_age or 'não informado'} anos; {lead.floors or 'não informado'} pavimentos; "
                f"{lead.apartments or 0} apartamentos; {lead.stores or 0} lojas; {lead.elevators or 0} elevadores."
            )
            if client:
                client.name = lead.legal_name
                client.document = lead.document
                client.email = lead.email
                client.phone = lead.phone
                client.street = lead.address
                client.postal_code = lead.postal_code
                client.classification = "autovistoria"
                client.action_description = details
                client.active = True
                client.save()
            else:
                client = Client.objects.create(
                    name=lead.legal_name, document=lead.document, email=lead.email, phone=lead.phone,
                    street=lead.address, postal_code=lead.postal_code, classification="autovistoria",
                    action_description=details, validation="validar", active=True,
                )
            owner = get_user_model().objects.filter(is_active=True, is_superuser=True).first() or get_user_model().objects.filter(is_active=True).first()
            opportunity = None
            if owner:
                opportunity, _ = Opportunity.objects.get_or_create(
                    client=client,
                    title=_automatic_opportunity_title(client),
                    defaults={"stage": "lead", "estimated_value": 0, "owner": owner},
                )
            lead.client = client
            lead.opportunity = opportunity
            lead.save(update_fields=("client", "opportunity", "updated_at"))
        send_mail(
            subject=f"Novo pedido de orçamento — {lead.legal_name}",
            message=(
                f"Novo pedido recebido pela Landing Page de Autovistoria.\n\n"
                f"Síndico(a): {lead.syndic_name}\nCondomínio: {lead.legal_name}\n"
                f"E-mail: {lead.email}\nCelular: {lead.phone}\nEndereço: {lead.address}\n"
                f"Acesse o sistema MGT para qualificar a oportunidade."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.MGT_LEAD_NOTIFICATION_EMAIL],
            fail_silently=True,
        )
        submitted = True
        form = LandingLeadForm()
        whatsapp_url += "?text=" + quote(f"Olá, sou {lead.syndic_name}, do {lead.legal_name}. Acabei de solicitar um orçamento de autovistoria pelo site da MGT Engenharia.")
    return render(request, "autovistoria_landing.html", {"form": form, "submitted": submitted, "whatsapp_url": whatsapp_url})

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


def _automatic_opportunity_title(client):
    return f"Autovistoria — {client.name}"


@login_required
@require_POST
def clients_to_opportunities(request):
    selected_ids = list(dict.fromkeys(request.POST.getlist("client_ids")))
    if not selected_ids:
        messages.warning(request, "Selecione pelo menos um condomínio para transformar em oportunidade.")
        return redirect("clients")

    clients_by_id = {
        str(client.pk): client
        for client in Client.objects.filter(pk__in=selected_ids, active=True)
    }
    created = skipped = 0
    created_ids = []
    with transaction.atomic():
        for client_id in selected_ids:
            client = clients_by_id.get(client_id)
            if not client:
                skipped += 1
                continue
            opportunity, was_created = Opportunity.objects.get_or_create(
                client=client,
                title=_automatic_opportunity_title(client),
                defaults={"stage": "lead", "estimated_value": 0, "owner": request.user},
            )
            if was_created:
                created += 1
                created_ids.append(opportunity.pk)
            else:
                skipped += 1

        AuditLog.objects.create(
            actor=request.user,
            action="clientes_para_oportunidades",
            entity="Opportunity",
            entity_id=",".join(str(pk) for pk in created_ids) or "nenhuma",
            details={"selecionados": len(selected_ids), "criados": created, "ignorados": skipped},
        )

    messages.success(request, f"{created} oportunidade(s) criada(s) com sucesso.")
    if skipped:
        messages.info(request, f"{skipped} registro(s) foram ignorados por já existirem ou estarem inativos.")
    return redirect("opportunities" if created else "clients")

CRUD_MODELS = {"clientes": Client, "oportunidades": Opportunity, "propostas": Proposal, "projetos": Project, "tarefas": Task}

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

def _generic_export(model, fmt):
    fields = [f for f in model._meta.fields if f.name not in {"id", "created_at", "updated_at"}]
    headers = [str(f.verbose_name).title() for f in fields]
    rows = []
    for obj in model.objects.all():
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
    content, content_type = _generic_export(model, fmt)
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
    try:
        content, content_type = export_clients(fmt.lower())
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

@login_required
def rats(request):
    return render(request, "simple_list.html", {"title": "RAT — Relatórios de Atendimento", "items": RAT.objects.select_related("project")[:50]})

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
