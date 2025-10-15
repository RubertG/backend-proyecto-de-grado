"""Post-procesamiento del output del LLM.

Se asume que el LLM devuelve Markdown con secciones esperadas. Aun así:
- Normalizamos espacios.
- Garantizamos que todas las secciones existan (inyectando placeholder si falta).
"""
from __future__ import annotations
from typing import Dict, Tuple
import re

OPTIONAL_SECTIONS = ["## Fortalezas", "## Errores", "## Consejos de mejora", "## Pregunta de seguimiento"]

def normalize_output(markdown: str) -> str:
    """Normaliza espacios y elimina encabezados huérfanos sin contenido real.

    Estrategia:
    - Strip general.
    - Quitar bloques de encabezado seguido inmediatamente por otro encabezado o fin (indicando vacío real).
    - Colapsar saltos múltiples.
    - No añade secciones nuevas.
    """
    text = markdown.strip()
    # Eliminar encabezados vacíos (encabezado + fin o encabezado + otro encabezado)
    lines = [l.rstrip() for l in text.splitlines()]
    cleaned: list[str] = []
    for i, line in enumerate(lines):
        if any(line.startswith(sec) for sec in OPTIONAL_SECTIONS):
            # Mira siguiente línea (si existe)
            nxt = lines[i+1].strip() if i + 1 < len(lines) else ""
            if nxt == "" or any(nxt.startswith(sec) for sec in OPTIONAL_SECTIONS):
                # Saltar encabezado vacío
                continue
        cleaned.append(line)
    text = "\n".join(cleaned)
    # Colapsar saltos múltiples
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text

# Posible análisis simple de calidad
QUALITY_PATTERNS = {
    'generic_feedback': re.compile(r"(Buen trabajo|Sigue así)$", re.IGNORECASE),
}

def basic_quality_flags(markdown: str) -> Dict[str, bool]:
    return {name: bool(rx.search(markdown)) for name, rx in QUALITY_PATTERNS.items()}

REF_HEADER_RE = re.compile(r'^##\s+(Referencias|Recursos|Fuentes)\b', re.IGNORECASE | re.MULTILINE)
URL_RE = re.compile(r'https?://\S+')
MD_LINK_RE = re.compile(r'\[([^\]]+)\]\((https?://[^)]+)\)')
CITATION_RE = re.compile(r'(\s*)\[(?:\d+|[a-z]{1,3})\](?=[\s\.,;:!?]|$)', re.IGNORECASE)

def sanitize_references(markdown: str) -> Tuple[str, bool]:
    """Elimina secciones de referencias y enlaces externos.

    Operaciones:
    - Remueve headers de secciones indeseadas.
    - Quita URLs planas.
    - Convierte links markdown a texto plano.
    - Quita citas numéricas tipo [1] o [a].
    Devuelve el texto saneado y flag si hubo cambios.
    """
    original = markdown
    text = markdown
    # Eliminar líneas de secciones de referencias completas (solo header)
    text = REF_HEADER_RE.sub('', text)
    # Sustituir links markdown conservando el texto ancla
    text = MD_LINK_RE.sub(r'\1', text)
    # Eliminar URLs sueltas
    text = URL_RE.sub('', text)
    # Eliminar citas tipo [1]
    text = CITATION_RE.sub('', text)
    # Normalizar espacios en blanco múltiples generados tras eliminación
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    changed = text != original
    return text, changed
