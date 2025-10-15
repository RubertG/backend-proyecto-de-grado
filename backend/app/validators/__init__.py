"""Paquete de validadores estructurales de ejercicios.

Incluye:
- Dockerfile: validación sintáctica usando dockerfile-parse.
- Command: validación de parseo con shlex.
- Conceptual: passthrough (siempre válido).
"""
from .dockerfile import validate_dockerfile, DockerfileValidationResult  # noqa: F401
from .command import validate_command, validate_conceptual, CommandValidationResult  # noqa: F401
