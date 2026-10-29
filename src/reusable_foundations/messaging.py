"""Transactional text email, queued notifications and recipient-owned inbox."""
from email.message import EmailMessage
from pathlib import Path
from string import Template
import hashlib
import json
import smtplib
import ssl
import time


class FileEmail:
    def __init__(self, directory):
        self.root = Path(directory).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def send(self, message, key):
        # Test transport only. Stable key avoids multiple local files on replay.
        path = self.root / (hashlib.sha256(key.encode()).hexdigest() + ".eml")
        path.write_bytes(message.as_bytes())
        return str(path)


class SMTPEmail:
    def __init__(self, host, *, port=587, username=None, password=None):
        self.host, self.port, self.username, self.password = host, port, username, password

    def send(self, message, key):
        with smtplib.SMTP(self.host, self.port, timeout=15) as client:
            client.starttls(context=ssl.create_default_context())
            if self.username:
                client.login(self.username, self.password)
            client.send_message(message)
        return key  # SMTP does not guarantee deduplication by Message-ID.


class SESEmail:
    def __init__(self, client):
        self.client = client

    def send(self, message, key):
        return self.client.send_raw_email(RawMessage={"Data": message.as_bytes()})["MessageId"]


class Emailer:
    def __init__(self, transport, *, sender, templates):
        self.transport, self.sender, self.templates = transport, sender, templates

    def send(self, recipient, template, variables, *, key):
        subject, body = self.templates[template]
        message = EmailMessage()
        message["From"], message["To"] = self.sender, recipient
        message["Subject"] = Template(subject).substitute(variables)
        message["Message-ID"] = "<" + hashlib.sha256(key.encode()).hexdigest() + "@reusable.local>"
        message.set_content(Template(body).substitute(variables))
        return self.transport.send(message, key)


class Notifications:
    def __init__(self, store, jobs, *, clock=time.time):
        self.store, self.jobs, self.clock = store, jobs, clock

    def preferences(self, owner, channels):
        self.store.put("notification_preferences", owner, {"channels": list(channels)})

    def publish(self, recipient, template, variables, *, key, channels=("in_app",), run_at=None):
        nid = hashlib.sha256(json.dumps([recipient, key]).encode()).hexdigest()
        selected = self.store.get("notification_preferences", recipient)
        selected = selected["channels"] if selected else channels
        row = {"id": nid, "owner": recipient, "template": template, "variables": variables, "read": False, "created": self.clock(), "visible_at": self.clock() if run_at is None else run_at}
        with self.store.transaction():
            old = self.store.get("notifications", nid)
            if old:
                if old["template"] != template or old["variables"] != variables:
                    raise ValueError("Notification key conflict")
                row = old
            else:
                self.store.put("notifications", nid, row)
        # Replay repairs a crash between inbox persistence and enqueue.
        for channel in channels:
            if channel != "in_app" and channel in selected:
                self.jobs.enqueue("notification:" + channel, {"recipient": recipient, "template": template, "variables": variables}, key=nid, run_at=run_at)
        return row

    def inbox(self, owner):
        return [r for r in self.store.all("notifications") if r["owner"] == owner and r["visible_at"] <= self.clock()]

    def mark_read(self, owner, notification_id):
        with self.store.transaction():
            row = self.store.get("notifications", notification_id)
            if not row or row["owner"] != owner:
                raise PermissionError("Notification not found")
            row["read"] = True
            self.store.put("notifications", notification_id, row)
