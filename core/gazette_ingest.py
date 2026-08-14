# -*- coding: utf-8 -*-
"""Ingestão das intimações do Diário Oficial (item 7 — busca diária).

Lógica extraída da view gazette_findings para ser compartilhada entre:
  - a pesquisa manual na tela Diário Oficial;
  - o comando `manage.py buscar_diario` (agendável);
  - o endpoint automático protegido por token (disparo externo diário).
"""
import re

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from .gazette import fetch_notifications
from .models import AuditLog, Client, GazetteFinding, Opportunity


def parse_gazette_address(value):
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


def default_owner():
    """Dono das oportunidades criadas por execuções automáticas."""
    users = get_user_model().objects
    return users.filter(is_superuser=True).order_by("pk").first() or users.order_by("pk").first()


def ingest_gazette(dates, owner=None, actor=None, origem="pesquisa_diario_oficial"):
    """Busca e persiste as notificações dos dias informados.

    dates: lista de date (ou [None] para a edição mais recente).
    Retorna dict de estatísticas. Levanta RuntimeError se não houver
    usuário para atribuir as oportunidades.
    """
    owner = owner or default_owner()
    if owner is None:
        raise RuntimeError("Nenhum usuário cadastrado para ser responsável pelas oportunidades.")
    all_findings = []
    for selected_date in dates:
        try:
            _, day_findings = fetch_notifications(selected_date)
            all_findings.extend(day_findings)
        except Exception:
            continue
    stats = {"localizados": len(all_findings), "publicacoes_novas": 0, "clientes_criados": 0,
             "clientes_atualizados": 0, "oportunidades_criadas": 0, "duplicidades": 0}
    for item in all_findings:
        with transaction.atomic():
            finding, was_created = GazetteFinding.objects.get_or_create(
                edition_id=item["edition_id"], notification_number=item["notification_number"], defaults=item
            )
            stats["publicacoes_novas"] += int(was_created)
            client = Client.objects.filter(
                process_number__iexact=finding.process_number,
                notification_number__iexact=finding.notification_number,
            ).first()
            if not client:
                client = Client.objects.filter(name__iexact=finding.condominium_name).first()
            if client:
                stats["duplicidades"] += 1
                changed = False
                for field, value in {
                    "process_number": finding.process_number,
                    "publication_date": finding.publication_date,
                    "notification_number": finding.notification_number,
                    "action_description": f"Intimação localizada automaticamente no Diário Oficial. Página {finding.page}. Fonte: {finding.source_url}",
                    "classification": "autovistoria",
                }.items():
                    if value and not getattr(client, field):
                        setattr(client, field, value)
                        changed = True
                if changed:
                    client.save()
                    stats["clientes_atualizados"] += 1
            else:
                street, number, neighborhood = parse_gazette_address(finding.address)
                client = Client.objects.create(
                    name=finding.condominium_name,
                    origin="diario_oficial",
                    process_number=finding.process_number,
                    publication_date=finding.publication_date,
                    notification_number=finding.notification_number,
                    street=street,
                    address_number=number,
                    neighborhood=neighborhood,
                    classification="autovistoria",
                    action_description=f"Intimação localizada automaticamente no Diário Oficial. Página {finding.page}. Fonte: {finding.source_url}",
                    validation="validar",
                    active=True,
                )
                stats["clientes_criados"] += 1
            finding.client = client
            _, opp_created = Opportunity.objects.get_or_create(
                client=client,
                communication_number=finding.notification_number,
                source="Diário Oficial",
                defaults={
                    "title": f"Autovistoria — {client.name}",
                    "stage": "lead",
                    "estimated_value": 0,
                    "owner": owner,
                    "consultation_status": "Nova intimação — contato comercial pendente",
                    "consultation_notes": f"Processo {finding.process_number}; publicação de {finding.publication_date:%d/%m/%Y}; página {finding.page}.",
                    "consultation_address": finding.address,
                    "source_url": finding.source_url,
                    "consulted_at": timezone.now(),
                },
            )
            stats["oportunidades_criadas"] += int(opp_created)
            finding.status = "convertido"
            finding.save(update_fields=("client", "status", "updated_at"))
    AuditLog.objects.create(actor=actor, action=origem, entity="GazetteFinding",
                            entity_id=str(dates[0] or "edição mais recente"), details=stats)
    return stats
