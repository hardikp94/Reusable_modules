"""Durable at-least-once jobs with leases and bounded retries."""
import hashlib
import json
import secrets
import time


class Jobs:
    def __init__(self, store, *, clock=time.time):
        self.store, self.clock = store, clock

    def enqueue(self, kind, payload, *, key, run_at=None, max_attempts=3):
        if max_attempts < 1:
            raise ValueError("Invalid attempt limit")
        jid = hashlib.sha256(json.dumps([kind, key]).encode()).hexdigest()
        with self.store.transaction():
            old = self.store.get("jobs", jid)
            if old:
                if old["payload"] != payload:
                    raise ValueError("Job key conflict")
                return old
            row = {"id": jid, "kind": kind, "payload": payload, "state": "queued", "run_at": self.clock() if run_at is None else run_at, "attempts": 0, "max_attempts": max_attempts, "lease_until": 0, "lease": None}
            self.store.put("jobs", jid, row)
        return row

    def claim(self, *, lease_seconds=60):
        if lease_seconds <= 0:
            raise ValueError("Invalid lease")
        with self.store.transaction():
            now = self.clock()
            for row in sorted(self.store.all("jobs"), key=lambda r: r["run_at"]):
                eligible = row["state"] == "queued" and row["run_at"] <= now or row["state"] == "running" and row["lease_until"] <= now
                if not eligible:
                    continue
                if row["attempts"] >= row["max_attempts"]:
                    row["state"] = "failed"
                    self.store.put("jobs", row["id"], row)
                    continue
                row.update(state="running", lease=secrets.token_hex(16), lease_until=now + lease_seconds, attempts=row["attempts"] + 1)
                self.store.put("jobs", row["id"], row)
                return row

    def finish(self, job_id, lease, *, success):
        with self.store.transaction():
            row = self.store.get("jobs", job_id)
            if not row or row["state"] != "running" or row["lease"] != lease or row["lease_until"] <= self.clock():
                raise ValueError("Expired or stale job lease")
            row["state"] = "done" if success else ("failed" if row["attempts"] >= row["max_attempts"] else "queued")
            row["run_at"] = self.clock() + min(3600, 2 ** row["attempts"])
            row["lease"] = None
            self.store.put("jobs", job_id, row)

    def run_once(self, handlers):
        row = self.claim()
        if not row:
            return False
        try:
            handlers[row["kind"]](row["payload"], row["id"])
        except Exception:
            self.finish(row["id"], row["lease"], success=False)
            raise
        self.finish(row["id"], row["lease"], success=True)
        return True
