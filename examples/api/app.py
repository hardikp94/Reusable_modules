"""Loopback-only sample; no email, OTP or payment network operations."""
import os
from fastapi import FastAPI, Depends
from reusable_foundations.store import Store
from reusable_foundations.identity import Identity
from reusable_foundations.security import RateLimiter
from reusable_foundations.fastapi import identity_router, authenticated_user
from reusable_foundations.entitlements import Quotas

store = Store(os.environ.get("FOUNDATIONS_DB", "example.sqlite3"))
identity = Identity(store)
# Keep this secret persistent across restarts in a real deployment.
limiter = RateLimiter(store, b"loopback-example-only-not-for-production")
quotas = Quotas(store)
app = FastAPI(title="Reusable foundations example")
app.include_router(identity_router(identity, limiter, origin="http://localhost:5173", secure=False))

# Dev cross-port frontend only. For production use same-origin HTTPS proxying.
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_credentials=True, allow_methods=["GET", "POST"], allow_headers=["Content-Type", "Authorization", "X-Foundations-Request"])

@app.get("/private")
def private(user=Depends(authenticated_user(identity))):
    return {"message": "Authenticated using an imported package", "user_id": user["id"]}

@app.get("/balance")
def balance(user=Depends(authenticated_user(identity))):
    return {"remaining": quotas.balance(user["id"])}
