"""Explicit authorization and persistent admission budgets."""
import hashlib
import hmac
import time
import json


class Forbidden(PermissionError):
    pass


class RateLimited(ValueError):
    def __init__(self, retry_after):
        self.retry_after = max(1, int(retry_after) + 1)
        super().__init__("Too many requests")


class RateLimiter:
    def __init__(self, store, secret, *, clock=time.time):
        if len(secret) < 32:
            raise ValueError("Use a persistent secret of at least 32 bytes")
        self.store, self.secret, self.clock = store, secret, clock

    def admit(self, bucket, identifier, *, limit=10, window=900):
        if limit < 1 or window <= 0:
            raise ValueError("Invalid budget")
        key = hmac.new(self.secret, (bucket + ":" + identifier).encode(), hashlib.sha256).hexdigest()
        with self.store.transaction():
            now = self.clock()
            row = self.store.get("limits", key)
            if not row or row["end"] <= now:
                row = {"count": 0, "end": now + window}
            if row["count"] >= limit:
                raise RateLimited(row["end"] - now)
            row["count"] += 1
            self.store.put("limits", key, row)


class Permissions:
    def __init__(self, store, roles):
        self.store, self.roles = store, {k: frozenset(v) for k, v in roles.items()}

    def grant(self, tenant, user, role):
        if role not in self.roles:
            raise ValueError("Unknown role")
        # Trusted provisioning API; do not expose directly to end users.
        self.store.put("memberships", json.dumps([tenant, user]), {"role": role})

    def require(self, tenant, user, permission, *, resource_tenant=None):
        member = self.store.get("memberships", json.dumps([tenant, user]))
        if resource_tenant is not None and resource_tenant != tenant:
            raise Forbidden("Wrong tenant")
        if not member or permission not in self.roles.get(member["role"], ()):
            raise Forbidden("Permission denied")


def safe_redirect(value, fallback="/"):
    if isinstance(value, str) and value.startswith("/") and not value.startswith("//") and not any(c in value for c in ("\\", "\r", "\n")):
        return value
    return fallback
