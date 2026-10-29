# Explicit configuration

Core modules accept constructor arguments; they never read dotenv or discover credentials automatically. Environment variable names below are suggested consuming-application names, not mandatory names hidden in the library.

| Setting/object | Used by | Requirement |
|---|---|---|
| `APP_DATABASE_FILE` | Store | Absolute durable SQLite filename in private storage; directory exists |
| `APP_ORIGIN` | identity/payment router | Exact HTTPS frontend origin, no trailing slash/path |
| `APP_RATE_LIMIT_SECRET` | RateLimiter | Persistent random secret, at least 32 bytes |
| `APP_ACCESS_TTL`, `APP_SESSION_TTL` | Identity | Defaults 1800/604800 seconds; positive access ≤ session |
| Firebase Admin App | FirebasePhone | Explicit initialized App for the project's Firebase tenant/project |
| Firebase web auth + reCAPTCHA verifier | frontend adapter | Explicit modular SDK objects; phone provider enabled |
| Razorpay SDK client | Razorpay | Explicit server-side client and finite HTTP timeout |
| `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET` | Razorpay | Matching selected test/live account; secret server-side |
| `RAZORPAY_WEBHOOK_SECRET` | Razorpay | Separate signing secret; no browser exposure |
| `mode` | Razorpay | Explicit `test` (default) or `live`; public key prefix checked |
| product catalogue | Payments | Product → integer minor-unit amount and ISO currency |
| plan catalogue | Subscriptions | Plan → provider plan ID, total count, amount, currency, features |
| SMTP/SES client, sender and templates | Emailer | Explicit transport; file transport for local tests |
| local directory/S3 client and bucket | Files | Private storage and explicit content-validation function |
| event/property allowlist | Analytics | Define allowed event names and property names |
| roles map | Permissions | Role → explicit permission strings |

Supply secrets from the new project's secret manager or server process environment. Browser Firebase configuration and Razorpay key ID are public identifiers; service-account credentials, gateway secrets, SMTP passwords and AWS credentials are server-only. Do not log proof tokens, refresh tokens or provider payloads.

Create separate test/live provider accounts/keys, database locations and webhook endpoints. Mode prefixes separate local payment identifiers, but sharing a database between environments is still discouraged. No values from TrailPulse have been copied.
