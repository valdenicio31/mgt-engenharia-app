from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.mail import send_mail
from django.db import connection, transaction
from django.db.models import Count
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
    active_clients = Client.objects.filter(active=True)
    context = {
        "clients": active_clients.count(),
        "opportunities": Opportunity.objects.exclude(stage__in=["ganha", "perdida"]).count(),
        "projects": Project.objects.filter(status="em_execucao").count(),
        "pending_tasks": Task.objects.filter(completed=False).count(),
        "pipeline": Opportunity.objects.select_related("client", "owner").order_by("-updated_at")[:6],
        "recent_projects": Project.objects.select_related("client", "manager").order_by("-updated_at")[:5],
        "clients_by_street": active_clients.exclude(street="").values("street").annotate(total=Count("id")).order_by("-total", "street")[:10],
        "clients_by_neighborhood": active_clients.exclude(neighborhood="").values("neighborhood").annotate(total=Count("id")).order_by("-total", "neighborhood")[:10],
        "clients_by_city": active_clients.exclude(city="").values("city").annotate(total=Count("id")).order_by("-total", "city")[:10],
    }
    return render(request, "dashboard.html", context)


@login_required
def profile(request):
    profile_obj, _ = UserProfile.objects.get_or_create(user=request.user, defaults={"cpf": f"{request.user.pk:011d}"[-11:]})
    form = UserProfileForm(request.POST or None, request.FILES or None, instance=profile_obj, user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
