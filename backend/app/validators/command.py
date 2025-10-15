"""Validación estructural para ejercicios tipo 'command'.

Alcance (limitado a sintaxis):
- Parseo con shlex.split (detecta comillas sin cerrar, etc.).
- Whitelist opcional del comando base.
- No ejecuta el comando ni valida permisos.

Ejemplo rápido:
    from app.validators.command import validate_command
    res = validate_command("docker build .")
    if res.is_valid:
        ...

Para ejercicios conceptuales, usar `validate_conceptual` que siempre retorna True.
"""
from __future__ import annotations
from dataclasses import dataclass
import shlex
from typing import List, Iterable

@dataclass(slots=True)
class CommandValidationResult:
    is_valid: bool
    errors: List[str]
    tokens: List[str]

DEFAULT_ALLOWED: tuple[str, ...] = (
    "docker", "kubectl", "git", "python", "pip", "echo", "ls", "cat"
)

class CommandValidator:
    """Validador de comandos basado en parsing con shlex."""
    def __init__(self, allowed_commands: Iterable[str] | None = None) -> None:
        self.allowed = tuple(allowed_commands) if allowed_commands else DEFAULT_ALLOWED

    def validate(self, command_str: str) -> CommandValidationResult:
        if not command_str.strip():
            return CommandValidationResult(False, ["Comando vacío"], [])
        try:
            tokens = shlex.split(command_str)
        except ValueError as e:
            raw = str(e).lower()
            if "no closing quotation" in raw:
                msg = "Comillas sin cerrar"
            else:
                msg = "Error sintáctico en el comando"
            return CommandValidationResult(False, [msg], [])
        if not tokens:
            return CommandValidationResult(False, ["Sin tokens"], [])
        base = tokens[0]
        if self.allowed and base not in self.allowed:
            return CommandValidationResult(False, [f"Comando no permitido: {base}"], tokens)
        return CommandValidationResult(True, [], tokens)

_default_command_validator = CommandValidator()

def validate_command(command_str: str) -> CommandValidationResult:
    """Atajo funcional para validar un comando."""
    return _default_command_validator.validate(command_str)

# Conceptual passthrough

def validate_conceptual(_: str) -> bool:
    return True
