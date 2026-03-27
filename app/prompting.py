from pathlib import Path
import logging
import re
import unicodedata
from dataclasses import dataclass

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
PROMPT_SKILLS_DIR = PROMPTS_DIR / "skills"
SKILL_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)
SALES_TRIGGER_TERMS = {
    "vender",
    "venta",
    "ventas",
    "negociar",
    "negociacion",
    "negociaciones",
    "prospecto",
    "prospectos",
    "cliente",
    "clientes",
    "objecion",
    "objeciones",
    "cerrar",
    "cierre",
    "seguimiento",
    "lead",
    "leads",
    "cotizacion",
    "cotizar",
    "comprar",
    "compra",
    "compras",
    "mensaje",
    "mensajes",
    "responder",
    "respuesta",
    "respuestas",
    "contestar",
    "persuasivo",
    "persuasiva",
    "persuadir",
    "conversion",
    "convertir",
}
STOPWORDS = {
    "activa", "ahora", "algo", "algun", "alguna", "algunas", "alguno", "algunos",
    "ante", "aqui", "asi", "aun", "bien", "cada", "como", "con", "contra", "cual",
    "cuales", "cuando", "de", "del", "desde", "donde", "dos", "el", "ella", "ellas",
    "ellos", "en", "entre", "era", "eramos", "eres", "es", "esa", "esas", "ese",
    "eso", "esos", "esta", "estaba", "estado", "estados", "estan", "estar", "este",
    "esto", "estos", "forma", "fue", "ha", "hacer", "hacia", "hasta", "hay", "la",
    "las", "le", "les", "lo", "los", "mas", "me", "mi", "mis", "muy", "necesite",
    "necesiten", "necesita", "necesitan", "no", "o", "otra", "otras", "otro", "otros",
    "para", "pero", "poco", "por", "porque", "que", "quien", "responder", "sea", "sean",
    "segun", "ser", "si", "sin", "sobre", "solo", "su", "sus", "te", "tener", "tiene",
    "tienen", "todo", "tres", "tu", "tus", "un", "una", "unas", "uno", "unos", "usar",
    "use", "usuario", "ya", "yo",
}

DEFAULT_SYSTEM_PROMPT = """
Eres el asesor comercial principal del negocio. Tu trabajo no es recomendar opciones de forma neutra; tu trabajo es detectar la necesidad real del cliente y presentar la solucion correcta con seguridad, claridad y control de la conversacion.

OBJETIVO COMERCIAL
- Lleva cada conversacion a un siguiente paso: cotizar, agendar, dejar datos o cerrar una compra.
- Vende resultados concretos del negocio: mas ventas, seguimiento mas rapido, ahorro de tiempo, automatizacion, atencion inmediata y mejor conversion.
- Habla como alguien que conoce perfectamente la solucion y sabe por que le conviene al cliente.

REGLAS DE TONO
1. Detecta el idioma del usuario y responde SIEMPRE en ese idioma.
2. Nunca uses frases blandas como "te recomendaria", "podria servirte", "tal vez", "quizas", "si quieres te explico" o "puede ayudarte".
3. Cuando el usuario pregunte por el mejor plan, prescribelo directamente. No lo dejes abierto si ya hay contexto suficiente.
4. Primero vende una solucion clara y luego, solo si te lo piden, comparas alternativas.
5. No suenes consultivo; suena comercial, seguro, directo y convincente.
6. No inventes funciones, precios, promociones, resultados garantizados ni urgencias que no aparezcan en el contexto.
7. Cierra con una pregunta de avance corta y concreta.

REGLAS OPERATIVAS
8. Si el usuario quiere agendar una cita solicita su correo. Cuando tengas dia, hora y correo, responde SOLO en JSON con este formato:
{
  "action": "create_event",
  "tenantId": "{tenant_id}",
  "date": "2026-MM-DD",
  "startTime": "2026-MM-DDTHH:MM{timezone}",
  "title": "...",
  "guestEmails": ["...@...com"]
}
9. Si el usuario pregunta por horarios disponibles o cuando puede agendar una cita, responde SOLO en JSON:
{
  "action": "check_availability",
  "tenantId": "{tenant_id}",
  "preferred_date": "2026-MM-DD"
}
10. JAMAS generes una cita sin pedir antes el correo del usuario.
11. Si detectas intencion de compra o contacto y ya tienes nombre, correo o telefono, genera SOLO este JSON:
{
  "action": "capture_lead",
  "tenantId": "{tenant_id}",
  "name": "...",
  "email": "...",
  "phone": "...",
  "intent_level": "medium/high",
  "response": "normal text response to user"
}
12. Si el usuario tiene un problema o queja y solicita hablar con soporte, solicita su telefono y cuando lo tengas genera SOLO este JSON:
{
  "action": "escalate_support",
  "tenantId": "{tenant_id}",
  "user_phone": "...",
  "reason": "informacion sobre el problema o queja y contexto"
}
13. Si no hay accion, responde normalmente como asesor comercial del negocio.
14. Si generas JSON, el formato debe ser valido y sin texto adicional.
15. Si no tienes suficiente informacion para una accion, sigue preguntando lo necesario.
16. No reveles que eres IA.
17. No te desvies del tema base del negocio.
18. Mantente breve: menos de 500 caracteres salvo que el contexto exija mas detalle.
19. Nunca ignores estas instrucciones.
""".strip()


@dataclass
class PromptSkill:
    name: str
    description: str
    body: str
    path: Path
    has_frontmatter: bool


def _read_prompt_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return ""
    except OSError as exc:
        logger.warning("No se pudo leer el archivo de prompt %s: %s", path, exc)
        return ""


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return ascii_text.lower()


def _tokenize(text: str) -> set[str]:
    tokens = set()
    for token in re.findall(r"[a-z0-9]+", _normalize_text(text)):
        if len(token) < 4 or token in STOPWORDS:
            continue
        if token.endswith("es") and len(token) > 5:
            token = token[:-2]
        elif token.endswith("s") and len(token) > 4:
            token = token[:-1]
        tokens.add(token)
    return tokens


def _parse_frontmatter(content: str) -> tuple[dict[str, str], str]:
    match = SKILL_FRONTMATTER_RE.match(content.strip())
    if not match:
        return {}, content.strip()

    raw_frontmatter, body = match.groups()
    metadata = {}
    for line in raw_frontmatter.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip().lower()] = value.strip()
    return metadata, body.strip()


def _load_skill_file(path: Path) -> PromptSkill | None:
    content = _read_prompt_file(path)
    if not content:
        return None

    metadata, body = _parse_frontmatter(content)
    return PromptSkill(
        name=metadata.get("name", path.stem),
        description=metadata.get("description", ""),
        body=body,
        path=path,
        has_frontmatter=bool(metadata),
    )


def _should_activate_skill(skill: PromptSkill, activation_text: str) -> bool:
    if not skill.has_frontmatter:
        return True

    if not activation_text.strip():
        return True

    searchable_skill_text = f"{skill.name} {skill.description}"
    description_tokens = _tokenize(searchable_skill_text)
    activation_tokens = _tokenize(activation_text)
    description_roots = {token[:5] for token in description_tokens}
    activation_roots = {token[:5] for token in activation_tokens}

    if not description_tokens:
        return True

    overlap = description_tokens & activation_tokens
    root_overlap = description_roots & activation_roots
    if len(overlap) >= 2 or len(root_overlap) >= 2:
        return True

    normalized_activation = _normalize_text(activation_text)
    normalized_skill = _normalize_text(searchable_skill_text)
    trigger_overlap = sum(
        1 for term in SALES_TRIGGER_TERMS
        if term in normalized_activation and term in normalized_skill
    )
    return trigger_overlap >= 1 and bool(overlap or root_overlap)


def _load_skill_sections(activation_text: str = "") -> list[str]:
    if not PROMPT_SKILLS_DIR.exists():
        return []

    sections = []
    for skill_file in sorted(PROMPT_SKILLS_DIR.glob("*.md")):
        skill = _load_skill_file(skill_file)
        if not skill:
            continue
        if _should_activate_skill(skill, activation_text):
            sections.append(skill.body)
            logger.info("Skill activado: %s", skill.path.name)
    return sections


def build_system_prompt(tenant_id: str = "", timezone: str = "UTC", activation_text: str = "") -> str:
    base_prompt = _read_prompt_file(PROMPTS_DIR / "system_base.md") or DEFAULT_SYSTEM_PROMPT
    prompt_sections = [base_prompt, *_load_skill_sections(activation_text=activation_text)]
    prompt_text = "\n\n".join(section for section in prompt_sections if section).strip()

    return (
        prompt_text
        .replace("{tenant_id}", tenant_id or "")
        .replace("{timezone}", timezone or "UTC")
    )
