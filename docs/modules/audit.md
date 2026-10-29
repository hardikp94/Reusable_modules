# Audit events

```python
from reusable_foundations.observability import Audit
audit = Audit(store)
audit.record(tenant_id, actor_id, "document.updated", document_id,
    {"changed_fields": ["title"], "request_id": request_id})
# Require audit:read through Permissions before query:
events = audit.query(tenant_id)
```

Events have a random ID, tenant, actor, action, resource, timestamp and recursively redacted metadata. Redaction removes values under common password/token/secret/credential/email/phone keys and masks email-shaped text. It cannot identify every possible secret or phone number hidden in arbitrary text. Supply small allowlisted metadata, never raw request/provider payloads.

Tenant filtering does not authenticate the caller or check its permission. Protect the query in your server. The returned records are intended for diagnostics and accountability; database administrators can still alter them. This is not cryptographic signing, write-once storage, a legal retention scheme or a certified compliance audit system.

Choose retention, restricted access, immutable export/storage and backup policy in the consuming project. Avoid user names/contact details in action/resource identifiers. Event insertion is not automatically atomic with unrelated application writes; use an outbox when required.
