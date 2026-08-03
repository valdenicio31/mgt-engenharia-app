from datetime import date
from django.test import TestCase
from core.gazette import parse_notifications

class GazetteParserTests(TestCase):
    def test_parses_condominium_notification(self):
        text = "EIS-PRO-2023/05163 - CONDOMINIO DO EDIFICIO ERNEST HAECKEL Extraída Notificação número 45/2165/2026 Endereço do imóvel: RUA MARQ DE SÃO VICENTE nº 230 000230000428202696 - OUTRA EMPRESA"
        items = parse_notifications(text, {"publication_date": date(2026,7,31), "edition_id":"14887", "page":46})
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["notification_number"], "45/2165/2026")
        self.assertIn("MARQ DE SÃO VICENTE", items[0]["address"])
    def test_ignores_unrelated_condominium_mention(self):
        items = parse_notifications("Pagamento de taxa de condomínio sem notificação.", {"publication_date":date.today(),"edition_id":"1","page":1})
        self.assertEqual(items, [])

    def test_uses_notification_owner_when_previous_condominium_has_no_notice(self):
        text = "EIS-PRO-2023/07882 - CONDOMINIO BAYSIDE EIS-PRO-2022/12351 - CONDOMINIO SHOPPING GAVEA Extraída Notificação número 45/2172/2026 Endereço do imóvel: RUA EXEMPLO nº 52 SECRETARIA"
        item = parse_notifications(text, {"publication_date":date.today(),"edition_id":"1","page":1})[0]
        self.assertEqual(item["process_number"], "EIS-PRO-2022/12351")
        self.assertEqual(item["condominium_name"], "CONDOMINIO SHOPPING GAVEA")
        self.assertEqual(item["address"], "RUA EXEMPLO no 52")
