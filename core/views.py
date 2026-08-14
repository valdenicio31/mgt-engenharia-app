from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.mail import send_mail
from django.db import connection, transaction
from django.db.models import Count, Max, Q
import csv
import json
import io
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from django.utils import timezone
from urllib.parse import quote
from decimal import Decimal, ROUND_HALF_UP
from openpyxl import Workbook
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.core.exceptions import PermissionDenied
from .forms import AutovistoriaInfractionForm, ClientForm, FirstAccessForm, LandingLeadForm, MeasurementForm, OpportunityForm, ProjectForm, ProposalForm, RATForm, ResourceForm, TaskAllocationForm, TaskForm, UserProfileForm
from .permissions import role_required, user_role
from .client_io import export_clients, import_clients
from .gazette import fetch_notifications
from .gazette_ingest import ingest_gazette
from .models import AuditLog, AutovistoriaInfraction, Client, GazetteFinding, LandingLead, Measurement, Opportunity, Project, Proposal, RAT, Resource, Task, TaskAllocation
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
            lead = form.save(commit=False)
            # rastreio de canal: o formulário posta pra própria URL, então os
            # parâmetros utm_* da divulgação (instagram/facebook/whatsapp) se preservam
            utm_source = (request.GET.get("utm_source") or "").strip()[:20]
            lead.source = f"Landing · {utm_source}" if utm_source else "Landing Page"
            lead.save()
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
    submitted = False
    if request.method == "POST" and form.is_valid():
        user = form.save()
        AuditLog.objects.create(actor=user, action="primeiro_acesso_pendente", entity="User", entity_id=str(user.pk))
        send_mail(
            subject=f"Novo cadastro aguardando aprovação — {user.get_full_name()}",
            message=(
                f"Novo pedido de acesso ao sistema MGT.\n\n"
                f"Nome: {user.get_full_name()}\nE-mail: {user.email}\n\n"
                f"Acesse a tela Equipe para aprovar ou recusar o acesso."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.MGT_LEAD_NOTIFICATION_EMAIL],
            fail_silently=True,
        )
        submitted = True
        form = FirstAccessForm()
    return render(request, "registration/first_access.html", {"form": form, "submitted": submitted})

@login_required
def dashboard(request):
    location = (request.GET.get("local") or "").strip()
    clients_qs = Client.objects.filter(active=True)
    if location:
        clients_qs = clients_qs.filter(
            Q(street__icontains=location) | Q(neighborhood__icontains=location) | Q(city__icontains=location)
        )
    # Pendências do dia (item 9 — atalhos do uso diário)
    today = timezone.localdate()
    hoje_7d = timezone.now() - timedelta(days=7)
    pendencias = {
        "projetos_sem_rat": Project.objects.filter(status="em_execucao").exclude(rats__service_date=today).count(),
        "leads_7d": LandingLead.objects.filter(created_at__gte=hoje_7d).count(),
        "oportunidades_lead": Opportunity.objects.filter(stage="lead").count(),
    }
    if user_role(request.user) == "admin":
        pendencias["aprovacoes"] = get_user_model().objects.filter(is_active=False, profile__isnull=False).count()
    context = {
        "pendencias": pendencias,
        "clients": clients_qs.count(),
        "opportunities": Opportunity.objects.exclude(stage__in=["ganha", "perdida"]).count(),
        "projects": Project.objects.filter(status="em_execucao").count(),
        "pending_tasks": Task.objects.filter(completed=False).count(),
        "pipeline": Opportunity.objects.select_related("client", "owner").order_by("-updated_at")[:6],
        "recent_projects": Project.objects.select_related("client", "manager").order_by("-updated_at")[:5],
        "location_filter": location,
        "by_street": clients_qs.exclude(street="").values("street").annotate(total=Count("id")).order_by("-total", "street")[:10],
        "by_neighborhood": clients_qs.exclude(neighborhood="").values("neighborhood").annotate(total=Count("id")).order_by("-total", "neighborhood")[:10],
        "by_city": clients_qs.exclude(city="").values("city").annotate(total=Count("id")).order_by("-total", "city")[:10],
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

def _client_queryset(request):
    """Filtros/ordenação de Clientes — compartilhado entre a tela e a exportação da visão."""
    items = Client.objects.all()
    search = (request.GET.get("q") or "").strip()
    city = (request.GET.get("cidade") or "").strip()
    neighborhood = (request.GET.get("bairro") or "").strip()
    validation = (request.GET.get("validacao") or "").strip()
    if search:
        items = items.filter(Q(name__icontains=search) | Q(document__icontains=search) | Q(street__icontains=search) | Q(process_number__icontains=search) | Q(notification_number__icontains=search))
    if city:
        items = items.filter(city__iexact=city)
    if neighborhood:
        items = items.filter(neighborhood__iexact=neighborhood)
    if validation:
        items = items.filter(validation=validation)
    allowed_sorts = {
        "nome": "name", "rua": "street", "bairro": "neighborhood", "cidade": "city",
        "processo": "process_number", "notificacao": "notification_number", "atualizado": "updated_at",
    }
    sort = request.GET.get("ordenar", "rua")
    direction = request.GET.get("direcao", "asc")
    sort_field = allowed_sorts.get(sort, "street")
    prefix = "-" if direction == "desc" else ""
    if sort == "rua":
        items = items.order_by(f"{prefix}street", f"{prefix}neighborhood", f"{prefix}name")
    elif sort == "bairro":
        items = items.order_by(f"{prefix}neighborhood", f"{prefix}street", f"{prefix}name")
    else:
        items = items.order_by(f"{prefix}{sort_field}", "name")
    filters = {
        "q": search, "cidade": city, "bairro": neighborhood, "validacao": validation,
        "cities": Client.objects.exclude(city="").values_list("city", flat=True).distinct().order_by("city"),
        "neighborhoods": Client.objects.exclude(neighborhood="").values_list("neighborhood", flat=True).distinct().order_by("neighborhood"),
    }
    return items, filters, sort, direction


def _opportunity_queryset(request):
    """Filtros/ordenação de Oportunidades — mesmo padrão de Clientes."""
    items = Opportunity.objects.select_related("client", "owner").all()
    search = (request.GET.get("q") or "").strip()
    stage = (request.GET.get("etapa") or "").strip()
    owner = (request.GET.get("responsavel") or "").strip()
    if search:
        items = items.filter(Q(title__icontains=search) | Q(client__name__icontains=search) | Q(client__document__icontains=search) | Q(communication_number__icontains=search) | Q(source__icontains=search))
    if stage:
        items = items.filter(stage=stage)
    if owner:
        items = items.filter(owner_id=owner)
    allowed_sorts = {
        "titulo": "title", "cliente": "client__name", "etapa": "stage",
        "valor": "estimated_value", "atualizado": "updated_at",
    }
    sort = request.GET.get("ordenar", "atualizado")
    direction = request.GET.get("direcao", "desc" if request.GET.get("ordenar") in (None, "", "atualizado") else "asc")
    sort_field = allowed_sorts.get(sort, "updated_at")
    prefix = "-" if direction == "desc" else ""
    items = items.order_by(f"{prefix}{sort_field}", "title")
    owners_qs = get_user_model().objects.filter(opportunity__isnull=False).distinct().order_by("first_name", "username")
    filters = {
        "q": search, "etapa": stage, "responsavel": owner,
        "stages": Opportunity.STAGES, "owners": owners_qs,
    }
    return items, filters, sort, direction


def _crud(request, model, form_class, title, template="generic_list.html"):
    edit_id = request.GET.get("editar")
    instance = get_object_or_404(model, pk=edit_id) if edit_id else None
    form = form_class(request.POST or None, request.FILES or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        if model is Client and not instance:
            obj.origin = "manual"
        if hasattr(obj, "owner_id") and not obj.owner_id: obj.owner = request.user
        if hasattr(obj, "manager_id") and not obj.manager_id: obj.manager = request.user
        if hasattr(obj, "assignee_id") and not obj.assignee_id: obj.assignee = request.user
        obj.save()
        action = "alterado" if instance else "criado"
        AuditLog.objects.create(actor=request.user, action=action, entity=model.__name__, entity_id=str(obj.pk))
        messages.success(request, "Registro atualizado com sucesso." if instance else "Registro criado com sucesso.")
        if model is Opportunity and obj.stage == "ganha":
            client = obj.client
            if client.validation != "confirmado" or not client.active:
                client.validation = "confirmado"
                client.active = True
                client.save(update_fields=("validation", "active", "updated_at"))
                AuditLog.objects.create(actor=request.user, action="oportunidade_ganha", entity="Client", entity_id=str(client.pk), details={"oportunidade": obj.pk})
            messages.success(request, f"🎉 Oportunidade ganha! O condomínio {client.name} foi confirmado como cliente — gere o contrato padrão na tela de Clientes (ação 📄 Contrato).")
        return redirect(request.path)
    resource = {Client: "clientes", Opportunity: "oportunidades", Proposal: "propostas", Project: "projetos", Task: "tarefas", Resource: "recursos", TaskAllocation: "alocacoes"}[model]
    items = model.objects.all().order_by("-updated_at")
    filters = {}
    sort = direction = ""
    if model is Client:
        items, filters, sort, direction = _client_queryset(request)
    elif model is Opportunity:
        items, filters, sort, direction = _opportunity_queryset(request)
    show_form = bool(instance or request.GET.get("novo") or (request.method == "POST" and form.errors))
    return render(request, template, {"title": title, "items": items[:100], "form": form, "editing": instance, "show_form": show_form, "resource": resource, "filters": filters, "sort": sort, "direction": direction})

@login_required
def clients(request): return _crud(request, Client, ClientForm, "Clientes e condomínios", "clients.html")


def _client_consultation_address(client):
    first_line = ", ".join(part for part in [client.street, client.address_number] if part)
    if client.complement:
        first_line = f"{first_line} - {client.complement}" if first_line else client.complement
    locality = " - ".join(part for part in [client.neighborhood, client.city, client.state] if part)
    return " | ".join(part for part in [first_line, locality] if part)


@login_required
def client_autovistoria(request, pk):
    client = get_object_or_404(Client, pk=pk, active=True)
    portal_url = "https://autovistoria.rio.rj.gov.br/ConsultaPublica.php"
    form = AutovistoriaInfractionForm(
        request.POST or None,
        initial={"communication_number": client.notification_number, "source_url": portal_url},
    )
    if request.method == "POST" and form.is_valid():
        infraction_number = form.cleaned_data["infraction_number"].strip()
        if AutovistoriaInfraction.objects.filter(
            client=client, infraction_number__iexact=infraction_number
        ).exists():
            form.add_error(
                "infraction_number",
                "Esta autuação já está cadastrada para este condomínio.",
            )
        else:
            with transaction.atomic():
                infraction = form.save(commit=False)
                infraction.client = client
                finding = client.gazette_findings.order_by("-publication_date").first()
                if finding:
                    infraction.gazette_finding = finding
                infraction.save()
                if (
                    infraction.communication_number
                    and client.notification_number != infraction.communication_number
                ):
                    client.notification_number = infraction.communication_number
                    client.save(update_fields=("notification_number", "updated_at"))
                AuditLog.objects.create(
                    actor=request.user,
                    action="autuacao_autovistoria_importada",
                    entity="AutovistoriaInfraction",
                    entity_id=str(infraction.pk),
                    details={
                        "cliente": client.name,
                        "autuacao": infraction.infraction_number,
                        "etapa": "autuacao_registrada_aguardando_oportunidade",
                    },
                )
            messages.success(
                request,
                "Autuação registrada. Inclua todas as demais autuações encontradas e, ao final, gere a oportunidade.",
            )
            return redirect("client_autovistoria", pk=client.pk)
    infractions = client.autovistoria_infractions.select_related(
        "opportunity", "gazette_finding"
    ).all()
    pending_infractions = infractions.filter(opportunity__isnull=True)
    return render(
        request,
        "client_autovistoria.html",
        {
            "client": client,
            "form": form,
            "portal_url": portal_url,
            "consultation_address": _client_consultation_address(client),
            "infractions": infractions,
            "pending_infractions_count": pending_infractions.count(),
        },
    )


@login_required
@require_POST
def client_autovistoria_robot_import(request, pk):
    """Recebe os comunicados lidos pela extensão do Chrome.

    O CAPTCHA permanece sob responsabilidade do usuário. A extensão apenas
    preenche os campos e, depois da consulta manual, envia a tabela exibida.
    """
    client = get_object_or_404(Client, pk=pk, active=True)
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JsonResponse({"ok": False, "error": "Conteúdo JSON inválido."}, status=400)

    rows = payload.get("items")
    if not isinstance(rows, list) or not rows:
        return JsonResponse({"ok": False, "error": "Nenhum comunicado foi recebido."}, status=400)
    if len(rows) > 200:
        return JsonResponse({"ok": False, "error": "A consulta excedeu o limite de 200 itens."}, status=400)

    created = 0
    skipped = 0
    errors = []
    finding = client.gazette_findings.order_by("-publication_date").first()
    imported_ids = []

    with transaction.atomic():
        for position, raw in enumerate(rows, start=1):
            if not isinstance(raw, dict):
                errors.append(f"Linha {position}: formato inválido.")
                continue
            communication = str(raw.get("communication_number") or "").strip()[:50]
            infraction_number = str(raw.get("infraction_number") or communication).strip()[:80]
            infraction_type = str(raw.get("infraction_type") or "").strip()[:180]
            complement = str(raw.get("complement") or "").strip()
            notes = str(raw.get("notes") or "").strip()
            date_text = str(raw.get("infraction_date") or "").strip()
            if not infraction_number:
                errors.append(f"Linha {position}: comunicado sem identificação.")
                continue

            infraction_date = None
            for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"):
                try:
                    infraction_date = datetime.strptime(date_text, fmt).date() if date_text else None
                    break
                except ValueError:
                    continue

            description_parts = []
            if infraction_type:
                description_parts.append(infraction_type)
            if complement and complement not in {"-", "--"}:
                description_parts.append(f"Complemento/unidade: {complement}")
            if notes and notes not in {"-", "--"}:
                description_parts.append(f"Observação: {notes}")
            description = ". ".join(description_parts) or "Comunicado identificado no portal da Autovistoria."

            if AutovistoriaInfraction.objects.filter(client=client, infraction_number__iexact=infraction_number).exists():
                skipped += 1
                continue

            item = AutovistoriaInfraction.objects.create(
                client=client,
                gazette_finding=finding,
                communication_number=communication,
                infraction_number=infraction_number,
                infraction_type=infraction_type,
                description=description,
                infraction_date=infraction_date,
                status="ativa",
                source_url="https://autovistoria.rio.rj.gov.br/ConsultaPublica.php",
            )
            imported_ids.append(item.pk)
            created += 1

        if created:
            last_communication = next((str(r.get("communication_number") or "").strip() for r in reversed(rows) if isinstance(r, dict) and r.get("communication_number")), "")
            if last_communication and not client.notification_number:
                client.notification_number = last_communication[:50]
                client.save(update_fields=("notification_number", "updated_at"))

        AuditLog.objects.create(
            actor=request.user,
            action="autuacoes_importadas_pelo_robo_assistido",
            entity="Client",
            entity_id=str(client.pk),
            details={
                "cliente": client.name,
                "incluidas": created,
                "duplicadas": skipped,
                "erros": errors[:20],
                "ids": imported_ids,
                "captcha": "preenchido_manualmente_pelo_usuario",
            },
        )

    return JsonResponse({
        "ok": True,
        "created": created,
        "skipped": skipped,
        "errors": errors,
        "message": f"{created} comunicado(s) importado(s); {skipped} duplicado(s) ignorado(s).",
    })


@login_required
@require_POST
def client_autovistoria_create_opportunity(request, pk):
    client = get_object_or_404(Client, pk=pk, active=True)
    pending = list(client.autovistoria_infractions.filter(opportunity__isnull=True))
    if not pending:
        messages.warning(request, "Nenhuma autuação nova foi registrada. Consulte o portal e importe ao menos uma autuação antes de gerar a oportunidade.")
        return redirect("client_autovistoria", pk=client.pk)

    with transaction.atomic():
        opportunity = Opportunity.objects.filter(client=client, source="Autovistoria Rio").order_by("pk").first()
        created = opportunity is None
        if created:
            opportunity = Opportunity(
                client=client,
                source="Autovistoria Rio",
                owner=request.user,
                title=_automatic_opportunity_title(client),
                stage="lead",
                estimated_value=0,
            )
        if not opportunity.owner_id:
            opportunity.owner = request.user
        latest = pending[-1]
        opportunity.communication_number = latest.communication_number or client.notification_number
        opportunity.consultation_status = "; ".join(sorted({item.get_status_display() for item in pending}))
        opportunity.consultation_notes = "\n\n".join(
            f"Autuação {item.infraction_number}: {item.description}" for item in pending
        )
        opportunity.consultation_address = _client_consultation_address(client)
        opportunity.source_url = latest.source_url or "https://autovistoria.rio.rj.gov.br/ConsultaPublica.php"
        opportunity.consulted_at = timezone.now()
        opportunity.save()
        AutovistoriaInfraction.objects.filter(pk__in=[item.pk for item in pending]).update(opportunity=opportunity)
        AuditLog.objects.create(
            actor=request.user,
            action="oportunidade_criada_a_partir_de_autuacoes",
            entity="Opportunity",
            entity_id=str(opportunity.pk),
            details={
                "cliente": client.name,
                "autuacoes": [item.infraction_number for item in pending],
                "oportunidade_criada": created,
            },
        )
    messages.success(request, f"Oportunidade {'criada' if created else 'atualizada'} com {len(pending)} autuação(ões).")
    return redirect("opportunities")

def _automatic_opportunity_title(client):
    return f"Autovistoria — {client.name}"


@login_required
@require_POST
def clients_to_opportunities(request):
    # Na versão 1.0, oportunidades de Autovistoria só podem nascer depois da
    # consulta ao portal e do registro de pelo menos uma autuação. Mantemos a
    # rota para compatibilidade com links antigos, mas bloqueamos o atalho.
    messages.warning(
        request,
        "A criação direta foi desativada. Abra o condomínio, consulte a Autovistoria, "
        "registre todos os itens autuados e só então gere a oportunidade.",
    )
    return redirect("clients")

CRUD_MODELS = {"clientes": Client, "oportunidades": Opportunity, "propostas": Proposal, "projetos": Project, "tarefas": Task, "recursos": Resource, "alocacoes": TaskAllocation, "rats": RAT, "medicoes": Measurement}

@role_required("admin")
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

@role_required("admin", "comercial")
def records_export(request, resource, fmt):
    model = CRUD_MODELS.get(resource)
    if not model or fmt not in {"xlsx", "csv", "txt", "xml"}: return HttpResponse("Exportação inválida.", status=400)
    queryset = None
    if request.GET.get("escopo") == "visao":
        if model is Opportunity:
            queryset, _, _, _ = _opportunity_queryset(request)
        elif model is Client:
            queryset, _, _, _ = _client_queryset(request)
    content, content_type = _generic_export(model, fmt, queryset)
    scope_suffix = "_visao" if queryset is not None else ""
    response = HttpResponse(content, content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="MGT_{resource}{scope_suffix}.{fmt}"'
    return response

@role_required("admin", "comercial")
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

@role_required("admin", "comercial")
def clients_export(request, fmt):
    queryset = None
    if request.GET.get("escopo") == "visao":
        queryset, _, _, _ = _client_queryset(request)
    try:
        content, content_type = export_clients(fmt.lower(), queryset)
    except ValueError as exc:
        return HttpResponse(str(exc), status=400)
    filename = f"MGT_Engenharia_Condominios{'_visao' if queryset is not None else ''}.{fmt.lower()}"
    response = HttpResponse(content, content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
@login_required
def opportunities(request): return _crud(request, Opportunity, OpportunityForm, "Oportunidades", "opportunities.html")

@login_required
def opportunity_letter(request, pk):
    opportunity = get_object_or_404(
        Opportunity.objects.select_related("client", "owner").prefetch_related("infractions"),
        pk=pk,
    )
    return render(
        request,
        "opportunity_letter.html",
        {"opportunity": opportunity, "infractions": opportunity.infractions.all()},
    )


@login_required
def client_contract(request, pk):
    """Contrato padrão de prestação de serviço (item 4 — Marcio 13/08):
    discriminação do serviço, prazo com cronograma de execução e pagamento
    30% de sinal + saldo por medição, parcelável em até 3x no cartão."""
    client = get_object_or_404(Client, pk=pk)
    opportunity = None
    opp_id = request.GET.get("oportunidade")
    if opp_id:
        opportunity = client.opportunities.filter(pk=opp_id).first()
    if opportunity is None:
        opportunity = (client.opportunities.filter(stage="ganha").order_by("-updated_at").first()
                       or client.opportunities.order_by("-updated_at").first())
    infractions = opportunity.infractions.all() if opportunity else AutovistoriaInfraction.objects.filter(client=client)
    total = (opportunity.estimated_value if opportunity else None) or Decimal("0")
    centavos = Decimal("0.01")
    sinal = (total * Decimal("0.30")).quantize(centavos, rounding=ROUND_HALF_UP)
    saldo = total - sinal
    parcela = (saldo / 3).quantize(centavos, rounding=ROUND_HALF_UP) if saldo else Decimal("0")
    try:
        weeks = max(2, min(52, int(request.GET.get("semanas") or 8)))
    except ValueError:
        weeks = 8
    fim_vistoria = max(2, round(weeks * 0.4))
    fim_laudo = max(fim_vistoria + 1, round(weeks * 0.7))
    cronograma = [
        ("1. Planejamento e mobilização", "Reunião inicial, levantamento documental e plano de vistoria", "Semana 1"),
        ("2. Vistoria técnica em campo", "Inspeção das áreas comuns, fachadas e sistemas do condomínio", f"Semanas 2 a {fim_vistoria}"),
        ("3. Análise e laudo técnico", "Consolidação das evidências, classificação e emissão do laudo", f"Semanas {fim_vistoria + 1} a {fim_laudo}"),
        ("4. Plano de ação e encerramento", "Orientação das providências, medição final e entrega", f"Semanas {fim_laudo + 1} a {weeks}"),
    ]
    medicoes = [
        ("Sinal (assinatura do contrato)", "30% do valor", sinal),
        ("Medição 1 — conclusão da vistoria em campo", "sobre o saldo, conforme avanço", None),
        ("Medição 2 — entrega do laudo técnico", "sobre o saldo, conforme avanço", None),
        ("Medição final — plano de ação e encerramento", "sobre o saldo, conforme avanço", None),
    ]
    return render(request, "client_contract.html", {
        "client": client, "opportunity": opportunity, "infractions": infractions,
        "total": total, "sinal": sinal, "saldo": saldo, "parcela": parcela,
        "weeks": weeks, "cronograma": cronograma, "medicoes": medicoes,
    })
@login_required
def projects(request): return _crud(request, Project, ProjectForm, "Projetos", "projects.html")
@login_required
def tasks(request): return _crud(request, Task, TaskForm, "Tarefas")

@login_required
def proposals(request): return _crud(request, Proposal, ProposalForm, "Propostas")

@login_required
def resources(request): return _crud(request, Resource, ResourceForm, "Recursos (equipe e equipamentos)")

@login_required
def allocations(request): return _crud(request, TaskAllocation, TaskAllocationForm, "Alocações de recursos")

@login_required
def rats(request):
    """RAT diária (item 5): uma RAT por dia por projeto em execução."""
    edit_id = request.GET.get("editar")
    instance = get_object_or_404(RAT, pk=edit_id) if edit_id else None
    initial = {}
    if not instance:
        initial["service_date"] = timezone.localdate()
        if request.GET.get("projeto"):
            initial["project"] = request.GET.get("projeto")
    form = RATForm(request.POST or None, instance=instance, initial=initial)
    if request.method == "POST" and form.is_valid():
        rat = form.save(commit=False)
        if not rat.technician_id:
            rat.technician = request.user
        rat.save()
        action = "alterado" if instance else "criado"
        AuditLog.objects.create(actor=request.user, action=action, entity="RAT", entity_id=str(rat.pk))
        messages.success(request, "RAT registrada com sucesso.")
        return redirect("rats")
    today = timezone.localdate()
    running = Project.objects.filter(status="em_execucao").select_related("client")
    missing_today = running.exclude(rats__service_date=today)
    items = RAT.objects.select_related("project", "technician", "measurement")[:100]
    show_form = bool(instance or request.GET.get("novo") or request.GET.get("projeto") or (request.method == "POST" and form.errors))
    return render(request, "rats.html", {
        "title": "RAT — Relatórios de Atendimento", "items": items, "form": form,
        "editing": instance, "show_form": show_form, "missing_today": missing_today, "today": today,
    })


@login_required
def measurements(request):
    """Medição de cobrança (item 5): consolida as RATs abertas do projeto."""
    form = MeasurementForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        medicao = form.save(commit=False)
        ultimo = medicao.project.measurements.aggregate(m=Max("number"))["m"] or 0
        medicao.number = ultimo + 1
        medicao.save()
        anexadas = RAT.objects.filter(project=medicao.project, measurement__isnull=True).update(measurement=medicao)
        AuditLog.objects.create(actor=request.user, action="medicao_criada", entity="Measurement", entity_id=str(medicao.pk), details={"rats_consolidadas": anexadas})
        messages.success(request, f"Medição {medicao.number} criada consolidando {anexadas} RAT(s) do projeto {medicao.project}.")
        return redirect("measurements")
    items = Measurement.objects.select_related("project__client").prefetch_related("rats").order_by("-created_at")[:100]
    return render(request, "measurements.html", {"title": "Medições de cobrança", "items": items, "form": form})


@login_required
def project_report(request, pk):
    """Laudo de conclusão + dashboards planejado × executado (item 5)."""
    project = get_object_or_404(Project.objects.select_related("client", "manager"), pk=pk)
    tasks_qs = project.tasks.select_related("assignee").order_by("due_date")
    tasks_done = [t for t in tasks_qs if t.completed]
    rats_qs = project.rats.select_related("technician").order_by("service_date")
    first_rat, last_rat = rats_qs.first(), rats_qs.last()
    medicoes = project.measurements.prefetch_related("rats").order_by("number")
    total_medido = sum((m.amount for m in medicoes), Decimal("0"))
    planned_days = None
    if project.start_date and project.planned_end_date and project.planned_end_date >= project.start_date:
        planned_days = (project.planned_end_date - project.start_date).days + 1
    executed_days = (last_rat.service_date - first_rat.service_date).days + 1 if first_rat else 0
    barra_max = max(planned_days or 0, executed_days, 1)
    return render(request, "project_report.html", {
        "project": project, "tasks": tasks_qs, "tasks_done": len(tasks_done),
        "rats": rats_qs, "first_rat": first_rat, "last_rat": last_rat,
        "medicoes": medicoes, "total_medido": total_medido,
        "planned_days": planned_days, "executed_days": executed_days,
        "delay_days": (executed_days - planned_days) if planned_days else 0,
        "planned_pct": int((planned_days or 0) * 100 / barra_max), "executed_pct": int(executed_days * 100 / barra_max),
    })


def _parse_gazette_address(value):
    import re
    text = (value or "").strip()
    neighborhood = ""
    if " - " in text:
        parts = [part.strip() for part in text.split(" - ") if part.strip()]
        if len(parts) > 1:
            text, neighborhood = parts[0], parts[-1]
    match = re.match(r"^(.*?)(?:,|\s+n[º°o.]*)\s*(\d+[A-Za-z]?)\b", text, re.IGNORECASE)
    if match:
        return match.group(1).strip(), match.group(2).strip(), neighborhood
    return text, "", neighborhood

@login_required
def gazette_findings(request):
    if request.method == "POST":
        # Executar a busca no Diário cria clientes e oportunidades — restrito
        # a admin/comercial; técnico continua podendo consultar a lista.
        if user_role(request.user) not in ("admin", "comercial"):
            raise PermissionDenied
        try:
            start_raw, end_raw = request.POST.get("start_date"), request.POST.get("end_date")
            end_date = datetime.strptime(end_raw, "%Y-%m-%d").date() if end_raw else None
            start_date = datetime.strptime(start_raw, "%Y-%m-%d").date() if start_raw else end_date
            if start_date and end_date and (end_date < start_date or (end_date - start_date).days > 31):
                raise ValueError("Escolha um período válido de até 31 dias.")
            dates = [None] if not start_date else [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]
            stats = ingest_gazette(dates, owner=request.user, actor=request.user)
            period = f"{start_date:%d/%m/%Y} a {end_date:%d/%m/%Y}" if start_date else "edição mais recente"
            messages.success(request, f"Período {period}: {stats['localizados']} notificações, {stats['clientes_criados']} clientes criados e {stats['oportunidades_criadas']} oportunidades geradas.")
        except ValueError as exc:
            messages.error(request, str(exc))
        except Exception:
            messages.error(request, "Não foi possível consultar o Diário Oficial agora. Tente novamente em alguns minutos.")
        return redirect("gazette_findings")
    return render(request, "gazette_findings.html", {"items": GazetteFinding.objects.select_related("client").all()[:200]})


def gazette_auto_run(request):
    """Disparo externo da busca diária (item 7). Protegido por token:
    GET/POST /diario-oficial/executar-automatico/?token=<GAZETTE_CRON_TOKEN>.
    Sem o token configurado no ambiente, o endpoint fica desativado."""
    expected = getattr(settings, "GAZETTE_CRON_TOKEN", "")
    provided = request.GET.get("token") or request.headers.get("X-Cron-Token", "")
    if not expected or provided != expected:
        return JsonResponse({"erro": "não autorizado"}, status=403)
    try:
        stats = ingest_gazette([None], origem="busca_diaria_automatica")
    except Exception as exc:
        return JsonResponse({"erro": str(exc)}, status=500)
    return JsonResponse({"ok": True, **stats})



@role_required("admin")
def team(request):
    """Equipe: aprovação de novos usuários, papéis e ativação (RC26)."""
    User = get_user_model()
    if request.method == "POST":
        action = request.POST.get("acao")
        target = get_object_or_404(User, pk=request.POST.get("usuario"))
        if target.is_superuser and target != request.user:
            messages.error(request, "Superusuários só podem ser alterados no /admin.")
            return redirect("team")
        if action == "aprovar":
            target.is_active = True
            target.save(update_fields=("is_active",))
            role = request.POST.get("papel")
            if role in dict(UserProfile.ROLES):
                UserProfile.objects.filter(user=target).update(role=role)
            AuditLog.objects.create(actor=request.user, action="usuario_aprovado", entity="User", entity_id=str(target.pk), details={"papel": role or ""})
            messages.success(request, f"Acesso de {target.get_full_name() or target.email} aprovado.")
        elif action == "papel":
            role = request.POST.get("papel")
            if role in dict(UserProfile.ROLES):
                UserProfile.objects.filter(user=target).update(role=role)
                AuditLog.objects.create(actor=request.user, action="papel_alterado", entity="User", entity_id=str(target.pk), details={"papel": role})
                messages.success(request, f"Papel de {target.get_full_name() or target.email} atualizado.")
        elif action == "desativar":
            if target == request.user:
                messages.error(request, "Você não pode desativar o próprio acesso.")
            else:
                target.is_active = False
                target.save(update_fields=("is_active",))
                AuditLog.objects.create(actor=request.user, action="usuario_desativado", entity="User", entity_id=str(target.pk))
                messages.success(request, f"Acesso de {target.get_full_name() or target.email} desativado.")
        return redirect("team")
    users = User.objects.select_related("profile").order_by("is_active", "-date_joined")
    return render(request, "team.html", {"users": users, "roles": UserProfile.ROLES})

@login_required
def help_center(request):
    modules = [
        {"slug": "visao-geral", "title": "Visão geral", "objective": "Apresentar os principais indicadores operacionais e comerciais do MGT.", "steps": ["Acompanhe os totais e pendências.", "Use os atalhos para acessar os módulos.", "Confira os dados após importações e atualizações."]},
        {"slug": "clientes", "title": "Clientes e condomínios", "objective": "Centralizar o cadastro mestre dos condomínios e identificar a origem de cada registro.", "steps": ["Cadastre manualmente pelo botão Novo condomínio.", "Importe arquivos pela opção Importar arquivo.", "Consulte a coluna Origem para saber se o registro é manual, de arquivo ou do Diário Oficial.", "Use Alterar, Consultar Autovistoria e Excluir conforme a necessidade."]},
        {"slug": "diario-oficial", "title": "Diário Oficial", "objective": "Localizar intimações de autovistoria e transformá-las em clientes e oportunidades comerciais.", "steps": ["Informe o período desejado.", "Execute a pesquisa.", "O sistema registra as publicações encontradas.", "Quando aplicável, cria ou atualiza o cliente com origem Diário Oficial.", "Gera automaticamente a oportunidade comercial sem duplicar registros equivalentes."]},
        {"slug": "oportunidades", "title": "Oportunidades", "objective": "Acompanhar o funil comercial desde o lead até o fechamento.", "steps": ["Revise as oportunidades criadas automaticamente.", "Defina responsável, etapa e valor estimado.", "Registre o avanço para qualificação, proposta, negociação, ganha ou perdida."]},
        {"slug": "autovistoria", "title": "Autovistoria", "objective": "Consultar autuações e vincular as exigências ao condomínio e à oportunidade.", "steps": ["Abra o cliente e clique em Consultar Autovistoria.", "Execute o robô assistido ou registre a contingência manual.", "Revise as autuações encontradas.", "Gere a oportunidade quando houver pendências ainda não vinculadas."]},
        {"slug": "propostas", "title": "Propostas", "objective": "Registrar e acompanhar propostas comerciais vinculadas às oportunidades.", "steps": ["Crie a proposta a partir da oportunidade.", "Informe valores e status.", "Atualize o andamento até aceite ou recusa."]},
        {"slug": "projetos", "title": "Projetos", "objective": "Controlar os serviços contratados e sua execução.", "steps": ["Cadastre o projeto após o fechamento.", "Vincule cliente, responsáveis e datas.", "Acompanhe o status até a conclusão."]},
        {"slug": "tarefas", "title": "Tarefas", "objective": "Organizar atividades e pendências da equipe.", "steps": ["Crie a tarefa.", "Defina responsável e prazo.", "Atualize o status conforme a execução."]},
        {"slug": "rat", "title": "RAT", "objective": "Registrar atendimentos e serviços técnicos realizados.", "steps": ["Crie a RAT vinculada ao cliente ou projeto.", "Descreva o serviço executado.", "Finalize e preserve o histórico técnico."]},
    ]
    return render(request, "help_center.html", {"modules": modules, "system_objective": "Transformar informações públicas e operacionais em clientes, oportunidades e serviços rastreáveis para a MGT Engenharia."})
