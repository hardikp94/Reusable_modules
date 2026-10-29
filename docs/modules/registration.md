# Registration, contact verification and recovery

The core supports email/password registration, purpose-bound proof tokens, email verification, password reset, current-password change and verified contact linking. The base HTTP adapter mounts register/login/refresh/logout/me and optional phone sign-in. Recovery and contact-link endpoints are intentionally composed in the host application so it controls delivery, step-up proof, public responses and verification policy.

## Verify an email

```python
token = identity.challenge("member@example.test", "verify_email", ttl=900)
# Server: email the token/link to that address through your configured Emailer.
# Never return the token from a public verification-request endpoint.
identity.verify_email(token_from_recipient, "member@example.test")
```

## Reset a password

```python
token = identity.challenge("member@example.test", "reset_password", ttl=900)
# Server: deliver a reset link only to the account's saved email address.
identity.reset_password(token_from_recipient, "member@example.test", "new-long-password")
```

The token is random, stored hashed, expires, and is consumed atomically with the account change. A verification token cannot reset a password; replay is rejected. A successful password reset invalidates prior sessions. The raw token must travel only through the intended verification channel. Rate-limit both requests and proof submissions. Request routes should respond generically whether the account exists and queue delivery to reduce timing leaks. Put tokens in a URL fragment when practical, then POST them, avoid third-party scripts on the reset page, use Referrer-Policy, and do not log URLs/tokens.

## Link or replace a contact

```python
# user_id must come from authenticated server context. Require recent step-up proof.
token = identity.challenge("new@example.test", "link_email", user_id=user_id)
# Deliver to the NEW address; the caller then submits its received token.
identity.link_contact(user_id, token, "new@example.test", kind="email")
```

For phone linking use `purpose="link_phone"`, then `link_contact(user_id, challenge, phone, kind="phone", provider=phone_provider, id_token=firebase_token)`. Both fresh provider phone proof and the user-bound challenge are required. Challenges for sign-in cannot link contacts. Contacts already owned by another identity are rejected; accounts are never merged. Replacement removes the old login identifier and invalidates sessions.

The host must require recent authentication/step-up before issuing a link challenge, notify old/new contacts and implement its recovery/support policy. The core does not guess those business rules. Re-authenticate after password/contact changes. Keep permissions and billing references tied to stable user IDs rather than emails or phones.
