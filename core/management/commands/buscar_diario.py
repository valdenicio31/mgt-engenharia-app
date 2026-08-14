# -*- coding: utf-8 -*-
"""Busca diária automática no Diário Oficial (item 7 — Marcio 13/08).

Uso:
  python manage.py buscar_diario            # edição mais recente disponível
  python manage.py buscar_diario --data 2026-08-13

Agendável via cron/Task Scheduler ou disparado pelo endpoint
/diario-oficial/executar-automatico/ (token). Cria clientes com origem
"diario_oficial" e oportunidades em estágio lead, sem duplicar.
"""
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError

from core.gazette_ingest import ingest_gazette


class Command(BaseCommand):
    help = "Busca as intimações de autovistoria no Diário Oficial e alimenta clientes/oportunidades."

    def add_arguments(self, parser):
        parser.add_argument("--data", help="Data da edição (AAAA-MM-DD). Padrão: edição mais recente.")

    def handle(self, *args, **options):
        selected = None
        if options.get("data"):
            try:
                selected = datetime.strptime(options["data"], "%Y-%m-%d").date()
            except ValueError:
                raise CommandError("Data inválida — use o formato AAAA-MM-DD.")
        try:
            stats = ingest_gazette([selected], origem="busca_diaria_automatica")
        except RuntimeError as exc:
            raise CommandError(str(exc))
        self.stdout.write(self.style.SUCCESS(
            "Diário Oficial ({}): {localizados} notificações · {publicacoes_novas} novas · "
            "{clientes_criados} clientes criados · {clientes_atualizados} atualizados · "
            "{oportunidades_criadas} oportunidades".format(
                options.get("data") or "edição mais recente", **stats)
        ))
