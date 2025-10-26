"""Validación estructural para ejercicios tipo 'compose' (docker-compose.yaml).

Alcance (limitado a sintaxis):
- Parseo YAML válido.
- Verificación de estructura básica de docker-compose.
- No ejecuta ni valida semánticamente los servicios.

Ejemplo rápido:
    from app.validators.compose import validate_compose
    res = validate_compose(yaml_content)
    if res.is_valid:
        ...
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any
import yaml

@dataclass(slots=True)
class ComposeValidationResult:
    is_valid: bool
    errors: List[str]
    warnings: List[str]

class ComposeValidator:
    """Validador de archivos docker-compose.yaml basado en parsing YAML."""
    
    def __init__(self):
        self.required_root_keys = {'services'}  # 'services' es obligatorio
        self.valid_root_keys = {'version', 'services', 'volumes', 'networks', 'configs', 'secrets'}
    
    def validate(self, content: str) -> ComposeValidationResult:
        errors = []
        warnings = []
        
        # 1. Contenido vacío o solo espacios
        if not content.strip():
            errors.append("Archivo docker-compose vacío")
            return ComposeValidationResult(is_valid=False, errors=errors, warnings=warnings)
        
        # 2. Parseo YAML
        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            errors.append(f"YAML inválido: {str(e)}")
            return ComposeValidationResult(is_valid=False, errors=errors, warnings=warnings)
        
        # 3. Debe ser un diccionario
        if not isinstance(data, dict):
            errors.append("El archivo debe contener un objeto YAML válido")
            return ComposeValidationResult(is_valid=False, errors=errors, warnings=warnings)
        
        # 4. Verificar claves requeridas
        for required_key in self.required_root_keys:
            if required_key not in data:
                errors.append(f"Falta la sección requerida '{required_key}'")
        
        # 5. Verificar claves válidas en root
        for key in data.keys():
            if key not in self.valid_root_keys:
                warnings.append(f"Clave desconocida en raíz: '{key}'")
        
        # 6. Validar sección services si existe
        if 'services' in data:
            services = data['services']
            if not isinstance(services, dict):
                errors.append("La sección 'services' debe ser un objeto")
            elif not services:
                errors.append("La sección 'services' no puede estar vacía")
            else:
                # Validar cada servicio
                for service_name, service_config in services.items():
                    if not isinstance(service_config, dict):
                        errors.append(f"El servicio '{service_name}' debe ser un objeto")
                        continue
                    
                    # Verificar que tenga al menos una forma de especificar la imagen
                    if 'image' not in service_config and 'build' not in service_config:
                        errors.append(f"El servicio '{service_name}' debe tener 'image' o 'build'")
        
        # 7. Advertencias adicionales
        if 'version' not in data:
            warnings.append("Se recomienda especificar la versión del formato compose")
        elif data['version'] in ['1', '1.0']:
            warnings.append("La versión 1.x de docker-compose está obsoleta")
        
        is_valid = len(errors) == 0
        return ComposeValidationResult(is_valid=is_valid, errors=errors, warnings=warnings)

_default_compose_validator = ComposeValidator()

def validate_compose(compose_content: str) -> ComposeValidationResult:
    """Función de conveniencia para validar docker-compose usando el validador por defecto."""
    return _default_compose_validator.validate(compose_content)