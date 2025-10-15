"""Script rápido para obtener un access token de Supabase Auth vía REST Admin (solo para pruebas locales).

Advertencia:
 - Usa la SERVICE ROLE KEY: NO subir este script con la clave a repos públicos.
 - Para pruebas de endpoints protegidos: generar un usuario, insertar en Auth y recuperar su token de sesión iniciando sesión normal.

Flujo alternativo (sin frontend):
1. Crear usuario con signUp (anon key) -> obtiene confirmation email (si disabled email confirmations) o inmediato.
2. Hacer login con email/password y obtener token.

Este script implementa login para obtener access_token y luego llamar al backend.
"""
from __future__ import annotations
import os
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv

# Cargar .env (busca en el directorio backend)
env_path = Path(__file__).resolve().parent.parent / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")
EMAIL = os.environ.get("TEST_EMAIL", "test_user@example.com")
PASSWORD = os.environ.get("TEST_PASSWORD", "Test1234!")
BACKEND_BASE = os.environ.get("BACKEND_BASE", "http://localhost:8000/api/v1")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    print("Faltan SUPABASE_URL / SUPABASE_ANON_KEY en entorno.")
    sys.exit(1)

auth_url = f"{SUPABASE_URL}/auth/v1"

# 1. Sign up (idempotente: si ya existe dará error 422, lo ignoramos)
print("[+] Intentando signup...")
resp = requests.post(
    f"{auth_url}/signup",
    headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
    json={"email": EMAIL, "password": PASSWORD, "data": {"name": "Test User"}},
    timeout=15,
)
if resp.status_code not in (200, 201, 422):
    print("Error signup:", resp.status_code, resp.text)
    sys.exit(1)

# 2. Login
print("[+] Login...")
resp = requests.post(
    f"{auth_url}/token?grant_type=password",
    headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
    json={"email": EMAIL, "password": PASSWORD},
    timeout=15,
)
if resp.status_code != 200:
    print("Error login:", resp.status_code, resp.text)
    sys.exit(1)

data = resp.json()
access_token = data.get("access_token")
print("[+] Access token obtenido (truncado):", access_token)

# 3. Llamar endpoint protegido /users/me
print("[+] Llamando backend /users/me ...")
resp = requests.get(
    f"{BACKEND_BASE}/users/me",
    headers={"Authorization": f"Bearer {access_token}"},
    timeout=15,
)
print("Status:", resp.status_code)
print("Body:", resp.text)
