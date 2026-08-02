PIPELINE_STAGES = ("lead", "qualificacao", "proposta", "negociacao", "ganha", "perdida")

def completion_percent(done: int, total: int) -> int:
    if total <= 0:
        return 0
    return max(0, min(100, round((done / total) * 100)))

def proposal_conversion(accepted: int, total: int) -> int:
    return completion_percent(accepted, total)

def normalize_stage(stage: str) -> str:
    value = (stage or "").strip().lower()
    if value not in PIPELINE_STAGES:
        raise ValueError("Etapa de funil inválida")
    return value
