# Security model and known limits

This release supplies reusable foundations; it is not a production security certification. Configure and validate the consuming application before processing real identities, payments or private documents.

## Identity and browser boundary

Opaque access tokens live in memory; refresh tokens use HttpOnly, Secure, SameSite=Lax cookies in the FastAPI adapter. Tokens are hashed in storage. Session lifetime is fixed, sessions can be revoked, and account version changes invalidate old sessions. Password reset/contact proofs expire, are hashed and consumed atomically. Proofs are purpose-bound; link proofs are also user-bound. Reset/verify proofs cannot move to a reassigned email identity.

Write endpoints require the exact configured Origin plus `X-Foundations-Request: 1`. This is the supplied same-origin CSRF defense; there is no separate synchronizer-token API. Enforce HTTPS, trusted origins and restrictive CORS. Custom routes must apply equivalent controls. Trusted reverse proxies must overwrite untrusted forwarding headers; the module itself uses the direct peer address. Naive proxy configuration can put all users behind one rate-limit bucket.

Default registration permits login before email verification. Configure host policy if your application requires verified email. Public endpoints need anti-enumeration/product-specific abuse controls beyond the supplied generic budgets. MFA, passkeys, refresh rotation/reuse detection, breach-password checks and a full administrative identity product are not included. Contact replacement needs recent step-up authentication in the host. Firebase phone input validates shape, not number assignment/reachability.

## Payment and entitlement boundary

Prices originate in server configuration. Checkout signatures, captured payments, ownership, amounts and currencies are checked; webhook signatures cover raw bytes. Mode namespaces separate identifiers. Unknown create results stay blocked for reconciliation. Refund revocations prevent later capture reactivation. Never grant from a browser callback alone.

The host must durably map receipts to benefits and process revocations. The one-time payment router does not wire recurring subscription webhooks. Subscription receipt intake verifies provider invoice/payment data; restrictions and refunds must be reconciled. SDK client timeouts, webhook-secret rotation, provider event subscription, reconciliation monitoring, chargebacks, disputes, tax and legal invoicing need application-specific integration. Test/live provider behavior was not exercised by offline tests.

## Persistence and background operations

SQLite write transactions serialize local competing writers. The reference `all()` implementation scans namespaces and needs replacement/indexing at scale. No SQL encryption, automatic schema migration, backup or recovery procedure is supplied. Protect the database, local mail and uploads from public access. Expired sessions/challenges/rate rows and job/payment history do not purge automatically. Define reviewed retention jobs.

Jobs are at least once; provider acceptance and local success persistence can split across a crash. Deduplicate handlers and monitor failed/expired work. Same-operation quota reservations prevent overspending but do not deduplicate execution. Pending reservations need reconciliation against actual operations, not a blind timeout refund.

## Files, audit and analytics

Uploads require an explicit byte-validation/scanning policy, size limits, ownership and private storage. No antivirus product is embedded. Downloads need safe response headers and attachment policy in the host. S3 IAM/encryption, filesystem permissions and consistent backups are external configuration.

Audit redaction is a safety aid, not universal sensitive-data detection. Use allowlisted metadata; audit records are not tamper-proof. Analytics consent is an explicit input; clients can forge analytics and it must never authorize access or establish payment. The host owns consent, property-value validation and deletion/access policies.

## Validation boundary

Offline tests cover selected synthetic behavioral contracts. Real provider SDK/account compatibility, SMTP/SES/S3 delivery, Firebase certificate/revocation requests, gateway dashboard setup, concurrency across hosts, responsive/browser accessibility and operational recovery remain unverified. No production service was accessed or deployed.
