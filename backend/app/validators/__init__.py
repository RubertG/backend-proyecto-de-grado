"""Paquete de validadores estructurales de ejercicios.

Incluye:
- Dockerfile: validación sintáctica usando dockerfile-parse.
- Command: validación de parseo con shlex.
- Compose: validación de docker-compose.yaml usando PyYAML.
- Conceptual: passthrough (siempre válido).
"""
from .dockerfile import validate_dockerfile, DockerfileValidationResult  # noqa: F401
from .command import validate_command, validate_conceptual, CommandValidationResult  # noqa: F401
from .compose import validate_compose, ComposeValidationResult  # noqa: F401
