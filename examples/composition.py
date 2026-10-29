"""Run after installing the package: python examples/composition.py. No network."""
import io
from pathlib import Path
import time
from reusable_foundations.store import Store
from reusable_foundations.identity import Identity
from reusable_foundations.entitlements import Quotas
from reusable_foundations.jobs import Jobs
from reusable_foundations.messaging import Notifications, Emailer, FileEmail
from reusable_foundations.observability import Audit, Analytics
from reusable_foundations.security import Permissions
from reusable_foundations.storage import Files, LocalBlobs


def main():
    root = Path(".test-tmp/composition")
    root.mkdir(parents=True, exist_ok=True)
    store = Store() # Intentionally ephemeral identity data in this local example.
    try:
        auth = Identity(store)
        user = auth.register("member@example.test", "long-example-password")
        uid = user["id"]
        session = auth.login(user["email"], "long-example-password")
        assert auth.authenticate(session["access_token"])["id"] == uid
        roles = Permissions(store, {"reader": ["notes:read"]})
        roles.grant("demo", uid, "reader")
        roles.require("demo", uid, "notes:read", resource_tenant="demo")
        quotas = Quotas(store)
        quotas.grant(uid, "trial:" + uid, 2, expires=int(time.time()) + 3600, kind="trial")
        reservation = quotas.reserve(uid, "operation-1")
        quotas.settle(uid, reservation["id"], success=True)
        jobs = Jobs(store)
        notices = Notifications(store, jobs)
        notices.publish(uid, "welcome", {"name": "Member"}, key="welcome", channels=["in_app", "email"])
        mail = Emailer(FileEmail(root / "mail"), sender="service@example.test", templates={"welcome": ("Hello $name", "Your account is ready, $name.")})
        def deliver(payload, job_id):
            # Resolve account-owned delivery contact server-side.
            mail.send(user["email"], payload["template"], payload["variables"], key=job_id)
        jobs.run_once({"notification:email": deliver})
        files = Files(store, LocalBlobs(root / "files"), validate=lambda b, t: t == "text/plain" and b == b"demo")
        record = files.upload(uid, io.BytesIO(b"demo"), filename="demo.txt", content_type="text/plain")
        assert files.download(uid, record["id"])[1] == b"demo"
        files.delete(uid, record["id"])
        audit = Audit(store); audit.record("demo", uid, "demo.completed", "example")
        analytics = Analytics(store, {"demo_completed": []})
        analytics.track("demo_completed", {}, consent=True)
        auth.logout(session["refresh_token"])
        print({"result": "PASS", "remaining_units": quotas.balance(uid), "inbox_count": len(notices.inbox(uid)), "analytics": analytics.counts()})
    finally:
        store.close()


if __name__ == "__main__": main()
