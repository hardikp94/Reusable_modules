# Authentication and sessions

```python
from reusable_foundations.store import Store
from reusable_foundations.identity import Identity, IdentityError

store = Store("application.sqlite3")
identity = Identity(store, access_ttl=1800, session_ttl=604800)
user = identity.register("member@example.test", "long-example-password")
session = identity.login("member@example.test", "long-example-password")
current = identity.authenticate(session["access_token"])
renewed_access = identity.refresh(session["refresh_token"])
identity.logout(session["refresh_token"])
```

Direct calls return a raw refresh token to trusted server code. Do not return that field in a browser JSON response. The [FastAPI adapter](../quickstart.md) sets it as an HttpOnly, Secure, SameSite=Lax cookie and returns only access token/user information. Access is an opaque random bearer token; only token hashes are stored. This is deliberately not a JWT library. Database availability is required for every authentication.

`authenticate` rejects expired/revoked sessions, inactive users and stale user versions. Refresh issues another short-lived access token without extending the original session expiry. Refresh tokens are persistent for that fixed lifetime; rotation and refresh-token reuse detection are not implemented. Password change/reset and contact replacement increment user version and invalidate existing sessions. `logout` revokes the specific session.

Use `authenticated_user(identity)` as a FastAPI dependency. For other frameworks, obtain the bearer token, call `authenticate`, and map `IdentityError` to 401. Apply admission budgets before expensive password hashing, configure exact browser-origin checks, and never infer identity from a supplied user ID.

PBKDF2-SHA256 hashes use a random salt and 600,000 iterations. Choose a password policy and verification requirement for your product. `register` accepts only profile data passed by trusted code; public routes deliberately do not accept arbitrary profile/role/active fields. The default login permits unverified emails: applications requiring verification must enforce that policy before issuing a session.

`change_password(uid, old, new)` requires current-password proof. Linking contacts and recovery are covered in [registration](registration.md). Account deletion, MFA, enterprise SSO, passkeys, signing-key management and administrative account management are extension work. Clear expired rows with a reviewed retention job; the reference Store has no automatic TTL deletion.
