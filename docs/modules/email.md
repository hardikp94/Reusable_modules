# Transactional email

```python
from reusable_foundations.messaging import Emailer, FileEmail

emailer = Emailer(FileEmail("local-mail"), sender="service@example.test", templates={
    "welcome": ("Welcome, $name", "Hello $name, your account is ready.")
})
emailer.send("member@example.test", "welcome", {"name": "Member"}, key="welcome:user-id")
```

Templates are Python `string.Template` subject/text pairs; missing variables raise rather than silently omit content. Text-only output avoids an implicit HTML-sanitization policy. EmailMessage handles header validation; newline injection is rejected. The stable key sets a deterministic Message-ID. FileEmail writes one `.eml` per hashed key, useful for local integration without real delivery.

For SMTP: `SMTPEmail(host, port=587, username=..., password=...)` always uses STARTTLS with certificate verification. For SES: `SESEmail(explicit_boto3_ses_client)`. Pass the chosen transport to Emailer. The caller must configure authorized sender/region/credentials, consent, recipient ownership and provider timeouts. SES sandbox/identity verification and SMTP authentication are external prerequisites.

Use a background handler such as `lambda payload, job_id: emailer.send(payload['recipient'], payload['template'], payload['variables'], key=job_id)`. Accepted send does not prove inbox delivery. SMTP/SES do not deduplicate solely by Message-ID; a crash after provider acceptance can cause duplicate email. Do not send from incidental tests. Email/job payloads contain personal data and require private storage and retention policy.
