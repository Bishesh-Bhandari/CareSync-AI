"""
services/main.py
----------------
FastAPI entry point.

Routes:
  POST /auth/register  — create account, store in DB
  POST /auth/login     — check credentials, return session token
  GET  /auth/me        — verify token, return user info
  POST /analyze        — run AI symptom check (authenticated)
  GET  /history        — return past logs for this user (authenticated)

Run:
  uvicorn services.main:app --reload
  (from the healthsync/ root folder)
"""

import json
import os
import sys

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

# ── make sure the database package is importable ──────────────────────────────
# This lets you run:  uvicorn services.main:app  from the healthsync/ folder
#sys.path.append(os.path.join(os.path.dirname(__file__), ".."))


# correct — goes up TWO levels: services/ → backend/ → health_ai/
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.services.database.db import (
    init_db,
    create_user,
    verify_password,
    get_user_by_id,
    save_symptom_log,
    get_logs_for_user,
)
 

import secrets

# token -> user_id
SESSION_STORE = {}

def create_session(user_id: int) -> str:
    """
    Create a random token and remember which user owns it.
    """
    token = secrets.token_hex(32)
    SESSION_STORE[token] = user_id
    return token


def get_user_from_token(token: str):
    """
    Convert token -> user.
    Returns user dict or None.
    """
    user_id = SESSION_STORE.get(token)

    if user_id is None:
        return None

    return get_user_by_id(user_id)

# ── App setup ─────────────────────────────────────────────────────────────────
app = FastAPI(title="HealthSync AI API")

# Allow the HTML files (served from file:// or localhost:5500) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten this in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create tables on startup if they don't exist yet
@app.on_event("startup")
def startup():
    init_db()
    print("[HealthSync] Database initialised.")


# ── Pydantic models (FastAPI uses these to validate incoming JSON) ─────────────

class RegisterBody(BaseModel):
    first_name: str
    last_name:  str
    email:      str          # EmailStr needs email-validator package; plain str is fine here
    password:   str

class LoginBody(BaseModel):
    email:    str
    password: str

class AnalyzeBody(BaseModel):
    symptoms: str


# ── Helper: get authenticated user or raise 401 ───────────────────────────────
def require_auth(authorization: str = Header(None)):
    """
    Reads the  Authorization: Bearer <token>  header.
    Returns the user dict or raises HTTP 401.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated.")
    token = authorization.split(" ", 1)[1]
    user  = get_user_from_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Session expired. Please log in again.")
    return user


# ─────────────────────────────────────────────────────────────────────────────
#  Routes
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/auth/register")
def register(body: RegisterBody):
    """
    Browser → login.html → script.js → POST /auth/register
    1. Pydantic validates the JSON body
    2. create_user() hashes the password and inserts the row
    3. A session token is returned so the user is logged in immediately
    """
    if len(body.password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters.")

    try:
        user_id = create_user(
            first_name=body.first_name.strip(),
            last_name=body.last_name.strip(),
            email=body.email,
            plain_password=body.password,
        )
    except ValueError as e:
        # email already taken
        raise HTTPException(status_code=409, detail=str(e))

    token = create_session(user_id)
    return {
        "message": "Account created.",
        "token":   token,
        "user": {
            "id":         user_id,
            "first_name": body.first_name.strip(),
            "last_name":  body.last_name.strip(),
            "email":      body.email.lower().strip(),
        }
    }


@app.post("/auth/login")
def login(body: LoginBody):
    """
    Browser → login.html → script.js → POST /auth/login
    1. verify_password() checks the hash in SQLite
    2. On success a session token is returned
    3. JS stores it in localStorage and redirects to dashboard.html
    """
    user = verify_password(body.email, body.password)
    if not user:
        # same message for "no account" and "wrong password" — security best practice
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = create_session(user["id"])
    return {
        "message": "Login successful.",
        "token":   token,
        "user": {
            "id":         user["id"],
            "first_name": user["first_name"],
            "last_name":  user["last_name"],
            "email":      user["email"],
        }
    }


@app.get("/auth/me")
def me(authorization: str = Header(None)):
    """
    dashboard.html calls this on load to check if the stored token is still valid.
    If it is, return user info. If not, JS redirects to login.html.
    """
    user = require_auth(authorization)
    return {
        "id":         user["id"],
        "first_name": user["first_name"],
        "last_name":  user["last_name"],
        "email":      user["email"],
    }


@app.post("/analyze")
def analyze(body: AnalyzeBody, authorization: str = Header(None)):
    """
    dashboard.html → script.js → POST /analyze
    1. Auth check
    2. Call Gemini AI (imported from ai_summary.py)
    3. Save result to symptom_logs table
    4. Return result to frontend
    """
    user = require_auth(authorization)

    if not body.symptoms.strip():
        raise HTTPException(status_code=422, detail="Symptoms cannot be empty.")

    # Import here to avoid circular imports
    from backend.ai_summary import get_ai_analysis
    result = get_ai_analysis(body.symptoms)

    # Save to DB so the user can see their history
    save_symptom_log(
        user_id=user["id"],
        symptoms=body.symptoms,
        condition=result.get("condition", "Unknown"),
        severity=result.get("severity", "Unknown"),
        recommendations=json.dumps(result.get("recommendations", [])),
    )

    return result


@app.get("/history")
def history(authorization: str = Header(None)):
    """
    dashboard.html fetches this to show past symptom checks.
    """
    user = require_auth(authorization)
    logs = get_logs_for_user(user["id"])

    # recommendations is stored as a JSON string — parse it back to a list
    for log in logs:
        try:
            log["recommendations"] = json.loads(log["recommendations"] or "[]")
        except (json.JSONDecodeError, TypeError):
            log["recommendations"] = []

    return {"logs": logs}