"""Sanitized audit records and allowlisted analytics. Neither is tamper-proof."""
import secrets
import time
import re


def redact(value):
    if isinstance(value, dict):
        return {k: "[REDACTED]" if re.search(r"password|secret|token|authorization|cookie|email|phone|credential", k, re.I) else redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, str):
        return re.sub(r"[^\s@]+@[^\s@]+\.[^\s@]+", "[EMAIL]", value)[:2048]
    return value


class Audit:
    def __init__(self, store, *, clock=time.time):
        self.store, self.clock = store, clock

    def record(self, tenant, actor, action, resource, metadata=None):
        key = secrets.token_hex(16)
        row = {"id": key, "tenant": tenant, "actor": actor, "action": action, "resource": resource, "metadata": redact(metadata or {}), "created": self.clock()}
        self.store.put("audit", key, row)
        return key

    def query(self, tenant):
        # Caller must separately require audit:read for this tenant.
        return [r for r in self.store.all("audit") if r["tenant"] == tenant]


class Analytics:
    def __init__(self, store, events, *, clock=time.time, retention=15552000):
        self.store, self.events, self.clock, self.retention = store, events, clock, retention

    def track(self, name, properties, *, consent, event_id=None):
        if not consent:
            return False
        if name not in self.events or set(properties) - set(self.events[name]):
            raise ValueError("Unknown event or properties")
        key = event_id or secrets.token_hex(16)
        row = {"id": key, "name": name, "properties": redact(properties), "created": self.clock()}
        with self.store.transaction():
            if not self.store.get("analytics", key):
                self.store.put("analytics", key, row)
        return True

    def counts(self):
        result = {}
        for row in self.store.all("analytics"):
            if row["created"] > self.clock() - self.retention:
                result[row["name"]] = result.get(row["name"], 0) + 1
        return result

    def purge(self):
        with self.store.transaction():
            for row in self.store.all("analytics"):
                if row["created"] <= self.clock() - self.retention:
                    self.store.delete("analytics", row["id"])
