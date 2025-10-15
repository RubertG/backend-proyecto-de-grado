"""Validación estructural y sintáctica de Dockerfiles (enfocada en robustez y cobertura).

Objetivo: Rechazar entradas claramente inválidas o mal formadas, sin llegar a ser
un linter profundo de mejores prácticas. Todos los mensajes en español.

Cobertura implementada:
1. Parseo básico con dockerfile-parse.
2. Reglas de estructura global:
    - Primera instrucción debe ser FROM.
    - Debe existir al menos un FROM.
    - Instrucciones desconocidas => error.
3. Validaciones específicas por instrucción (cuando aplica):
    - FROM: sintaxis mínima válida; alias AS permitido.
    - COPY/ADD: requiere ≥2 paths (fuente(s) y destino) en forma shell o JSON.
    - EXPOSE: puertos deben ser enteros o entero/protocolo.
    - ENV: pares válidos (KEY=VAL o KEY VAL). Maneja múltiple por línea.
    - ARG: nombre válido (y opcional default con =).
    - CMD/ENTRYPOINT: JSON array o shell form no vacía.
    - HEALTHCHECK: NONE o contiene CMD tras flags.
    - WORKDIR: no vacío.
4. Advertencias (warnings) no invalidan (p.ej. uso de MAINTAINER, imagen latest).
5. Salida incluye errores, warnings y metadatos básicos.

No se evalúan:
- Seguridad, tamaño de imagen, eficiencia de capas.
- Resolución real de rutas o existencia de archivos.

Resultado:
     DockerfileValidationResult(is_valid, errors, warnings, parsed)

Dependencia: dockerfile-parse
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import json
import re
from dockerfile_parse import DockerfileParser  # type: ignore
import io

@dataclass(slots=True)
class DockerfileValidationResult:
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    parsed: Optional[Dict[str, Any]] = None

ALLOWED_INSTRUCTIONS = {
    "FROM","WORKDIR","COPY","RUN","CMD","ENTRYPOINT","ENV","ARG","EXPOSE",
    "VOLUME","USER","LABEL","STOPSIGNAL","HEALTHCHECK","ONBUILD","SHELL","ADD",
    # Permitimos MAINTAINER (deprecated) para generar warning en lugar de error.
    "MAINTAINER"
}

_RE_FROM = re.compile(r"^([\w./:-]+)(\s+AS\s+[\w.-]+)?$", re.IGNORECASE)
_RE_ARG = re.compile(r"^[A-Z_][A-Z0-9_]*(=.*)?$", re.IGNORECASE)
_RE_EXPOSE = re.compile(r"^[0-9]+(/(tcp|udp))?$", re.IGNORECASE)
_RE_ENV_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

class DockerfileValidator:
    def validate(self, content: str) -> DockerfileValidationResult:
        if not content.strip():
            return DockerfileValidationResult(False, ["Dockerfile vacío"], [], None)
        # Normalizamos saltos de línea a \n
        content_norm = content.replace('\r\n', '\n').replace('\r', '\n')
        buf = io.StringIO(content_norm)
        try:
            parser = DockerfileParser(fileobj=buf)
            structure = parser.structure  # fuerza parseo, lista de dicts
            if not structure:
                return DockerfileValidationResult(False, ["Dockerfile sin instrucciones"], [], None)
            errors: list[str] = []
            warnings: list[str] = []

            # Reglas globales
            first_instr = structure[0].get("instruction")
            if first_instr != "FROM":
                errors.append("La primera instrucción debe ser FROM")
            from_count = sum(1 for i in structure if i.get("instruction") == "FROM")
            if from_count == 0:
                errors.append("Falta instrucción FROM")

            unknown = [i.get("instruction") for i in structure if i.get("instruction") not in ALLOWED_INSTRUCTIONS]
            unknown_clean = [u for u in unknown if u]  # filtrar None
            if unknown_clean:
                errors.append("Instrucciones desconocidas: " + ", ".join(sorted(set(unknown_clean))))

            # Validaciones específicas
            for inst in structure:
                instr = inst.get("instruction") or ""
                value = (inst.get("value") or "").strip()
                upper = instr.upper()

                if upper == "FROM":
                    if not value:
                        errors.append("FROM sin imagen base")
                    elif not _RE_FROM.match(value):
                        errors.append("Sintaxis inválida en FROM")
                    else:
                        # warning imagen latest
                        img = value.split()[0]
                        if img.endswith(":latest"):
                            warnings.append("Uso de tag 'latest' (no determinista)")
                elif upper in ("COPY", "ADD"):
                    if not value:
                        errors.append(f"{upper} sin argumentos")
                    else:
                        if value.startswith('['):
                            # Forma JSON
                            try:
                                arr = json.loads(value)
                                if not isinstance(arr, list) or len(arr) < 2:
                                    errors.append(f"{upper} JSON debe tener al menos origen y destino")
                            except Exception:
                                errors.append(f"{upper} JSON inválido")
                        else:
                            parts = value.split()
                            if len(parts) < 2:
                                errors.append(f"{upper} requiere al menos origen y destino")
                elif upper == "EXPOSE":
                    if not value:
                        errors.append("EXPOSE sin puertos")
                    else:
                        for token in value.split():
                            if not _RE_EXPOSE.match(token):
                                errors.append(f"Puerto inválido en EXPOSE: {token}")
                elif upper == "ENV":
                    if not value:
                        errors.append("ENV sin contenido")
                    else:
                        tokens = value.split()
                        # Dos formas: KEY=VAL ... o pares KEY VAL
                        if all('=' in t for t in tokens):
                            for t in tokens:
                                k = t.split('=',1)[0]
                                if not _RE_ENV_KEY.match(k):
                                    errors.append(f"Nombre de variable inválido en ENV: {k}")
                        else:
                            # Debe ser pares
                            if len(tokens) % 2 != 0:
                                errors.append("ENV con número impar de tokens (pares clave valor esperados)")
                            else:
                                for i in range(0, len(tokens), 2):
                                    k = tokens[i]
                                    if not _RE_ENV_KEY.match(k):
                                        errors.append(f"Nombre de variable inválido en ENV: {k}")
                elif upper == "ARG":
                    if not value:
                        errors.append("ARG sin nombre")
                    elif not _RE_ARG.match(value):
                        errors.append("Sintaxis inválida en ARG")
                elif upper in ("CMD","ENTRYPOINT"):
                    if not value:
                        errors.append(f"{upper} sin contenido")
                    elif value.startswith('['):
                        try:
                            arr = json.loads(value)
                            if not isinstance(arr, list) or not arr:
                                errors.append(f"{upper} JSON debe ser lista con al menos un elemento")
                        except Exception:
                            errors.append(f"{upper} JSON inválido")
                elif upper == "HEALTHCHECK":
                    if not value:
                        errors.append("HEALTHCHECK sin contenido")
                    else:
                        if value.strip().upper() == "NONE":
                            pass
                        elif " CMD " in f" {value} ":
                            # se asume válido a nivel básico
                            pass
                        elif value.startswith("CMD ") or value.startswith("CMD["):
                            pass
                        else:
                            warnings.append("HEALTHCHECK no parece contener CMD (validación básica)")
                elif upper == "WORKDIR":
                    if not value:
                        errors.append("WORKDIR sin ruta")
                elif upper == "MAINTAINER":
                    warnings.append("MAINTAINER está deprecado (usar LABEL maintainer=")

            parsed_basic = {
                "base_images": [i.get("value") for i in structure if (i.get("instruction") or "").upper() == "FROM"],
                "stages": sum(1 for i in structure if (i.get("instruction") or "").upper() == "FROM"),
                "instruction_count": len(structure),
            }
            is_valid = not errors
            return DockerfileValidationResult(is_valid, errors, warnings, parsed_basic)
        except Exception:
            return DockerfileValidationResult(False, ["No se pudo parsear el Dockerfile (sintaxis inválida)"] , [], None)

_default_validator = DockerfileValidator()

def validate_dockerfile(content: str) -> DockerfileValidationResult:
    """Atajo funcional para validar un Dockerfile."""
    return _default_validator.validate(content)
