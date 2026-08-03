import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from core.client_io import export_clients, import_clients
from core.models import Client


class ClientTransferTests(TestCase):
    def csv_file(self, rows):
        content = "Nome;Numero_Processo;Numero_Notificacao;Rua;Numero;Classificacao;Validacao\n" + rows
        return SimpleUploadedFile("clientes.csv", content.encode("utf-8"), content_type="text/csv")

    def test_import_and_duplicate_analysis(self):
        created, updated, errors = import_clients(self.csv_file("Condomínio Teste;P-1;N-1;Rua A;10;Autovistoria explícita;Confirmado\n"))
        self.assertEqual((created, updated, errors), (1, 0, []))
        created, updated, errors = import_clients(self.csv_file("Condomínio Teste;P-1;N-1;Rua A;10;Autovistoria explícita;Confirmado\n"))
        self.assertEqual((created, updated, errors), (0, 1, []))
        self.assertEqual(Client.objects.count(), 1)

    def test_exports_all_supported_formats(self):
        Client.objects.create(name="Condomínio Teste", process_number="P-1")
        for fmt in ("xlsx", "csv", "txt", "xml"):
            content, content_type = export_clients(fmt)
            self.assertTrue(content)
            self.assertTrue(content_type)

    def test_large_import_uses_cached_duplicate_analysis(self):
        rows = "".join(
            f"Condomínio {index};P-{index};N-{index};Rua {index};{index};Autovistoria explícita;Confirmado\n"
            for index in range(1, 1001)
        )
        created, updated, errors = import_clients(self.csv_file(rows))
        self.assertEqual((created, updated, errors), (1000, 0, []))
        self.assertEqual(Client.objects.count(), 1000)

    def test_import_accepts_datetime_text(self):
        content = "Nome;Data_Publicacao\nCondomínio Data;2026-07-01 04:00:00\n"
        upload = SimpleUploadedFile("clientes.csv", content.encode("utf-8"), content_type="text/csv")
        created, updated, errors = import_clients(upload)
        self.assertEqual((created, updated, errors), (1, 0, []))
        self.assertEqual(str(Client.objects.get().publication_date), "2026-07-01")
