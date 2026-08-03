import json
import math
import re
import unicodedata
from datetime import date, timedelta
from urllib.parse import quote
from urllib.request import Request, urlopen

BASE_URL = "https://doweb.rio.rj.gov.br"
USER_AGENT = "MGT-Engenharia-Homologacao/1.0"

NOTICE_RE = re.compile(
    r"(?P<process>(?:EIS-PRO-\d{4}/\d+|\d{15,20}|\d{2}/\d{2}/[\d.]+/\d{4}))\s*-\s*"
    r"(?P<name>CONDOM[IÍ]NIO\s+.{2,180}?)\s+"
    r"Extra[ií]d[ao]\s+(?:a\s+)?Notifica[cç][aã]o\s+n[uú]mero\s+"
    r"(?P<notice>[\d./-]+)\s+Endere[cç]o\s+do\s+im[oó]vel:\s*"
    r"(?P<address>.*?)(?=\s+(?:[\d]{15,20}|EIS-PRO-\d{4}/\d+)\s*-|\s+[\"“]|\s+SECRETARIA|\s+Assinado|$)",
    re.IGNORECASE | re.DOTALL,
)

def _get_json(url):
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urlopen(request, timeout=40) as response:
        return json.load(response)

def latest_available_date(reference=None, lookback_days=10):
    reference = reference or date.today()
    for offset in range(lookback_days + 1):
        candidate = reference - timedelta(days=offset)
        url = f"{BASE_URL}/apifront/portal/edicoes/edicoes_from_data/{candidate.isoformat()}.json"
        payload = _get_json(url)
        if not payload.get("erro") and payload.get("itens"):
            return candidate
    raise RuntimeError("Nenhuma edição foi encontrada nos últimos 10 dias.")

def normalize_text(value):
    return " ".join(unicodedata.normalize("NFKC", value or "").split())

def parse_notifications(text, metadata):
    results = []
    for match in NOTICE_RE.finditer(normalize_text(text)):
        process_number = normalize_text(match.group("process"))
        name = normalize_text(match.group("name")).strip(" -.;")
        nested = re.search(r"(?P<process>(?:EIS-PRO-\d{4}/\d+|\d{15,20}))\s*-\s*(?P<name>CONDOM[IÍ]NIO.+)$", name, re.IGNORECASE)
        if nested:
            process_number = normalize_text(nested.group("process"))
            name = normalize_text(nested.group("name")).strip(" -.;")
        address = normalize_text(match.group("address")).strip(" -.;")
        address_number = re.match(r"(.+?\b(?:n[oº°]|s/n)\s*[\w.-]+)", address, re.IGNORECASE)
        if address_number:
            address = address_number.group(1)
        if len(address) > 260:
            address = address[:260].rsplit(" ", 1)[0]
        results.append({
            "publication_date": metadata["publication_date"],
            "edition_id": str(metadata["edition_id"]),
            "page": int(metadata["page"]),
            "process_number": process_number,
            "condominium_name": name,
            "notification_number": normalize_text(match.group("notice")),
            "address": address,
            "source_url": f"{BASE_URL}/ver/{metadata['edition_id']}/{metadata['page']}/CONDOMINIO",
            "raw_excerpt": normalize_text(match.group(0))[:1500],
        })
    return results

def fetch_notifications(publication_date=None):
    publication_date = publication_date or latest_available_date()
    day = publication_date.isoformat()
    findings, seen = [], set()
    page_index, pages = 0, 1
    while page_index < pages:
        url = f"{BASE_URL}/busca/busca/buscar/query/{page_index}/di:{day}/df:{day}/?1=1&q={quote('CONDOMINIO')}"
        payload = _get_json(url)
        total = payload.get("hits", {}).get("total", 0)
        if isinstance(total, dict):
            total = total.get("value", 0)
        pages = max(1, math.ceil(total / 10))
        for hit in payload.get("hits", {}).get("hits", []):
            source = hit.get("_source", {})
            metadata = {"publication_date": publication_date, "edition_id": source.get("diario_id"), "page": source.get("pagina", 1)}
            for item in parse_notifications(source.get("conteudo", ""), metadata):
                key = (item["edition_id"], item["notification_number"])
                if key not in seen:
                    seen.add(key)
                    findings.append(item)
        page_index += 1
    return publication_date, findings
