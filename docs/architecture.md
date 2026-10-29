# Architecture and boundaries

Version 0.1.0 is a standalone toolkit. Python 3.11+ is required; React 18/19 is a peer dependency. Backend code has no mandatory external dependencies. FastAPI, Firebase Admin, Razorpay and AWS SDKs are optional adapters, installed by the consuming application.

```text
New application's routes, product rules and configuration
              |                         |
   reusable_foundations            React package
   identity/payments/quotas         forms/session client
   jobs/messaging/files            checkout adapter
              |
   Store transaction interface + explicit provider objects
              |
   SQLite / Firebase / Razorpay / SES / SMTP / S3
```

One Python distribution contains independently importable modules. One npm distribution exposes independent client, React, checkout and Firebase entry points. This avoids maintaining many tiny package versions while allowing selective imports. These are application libraries, not separately hosted microservices.

## Storage contract

`Store(path)` persists JSON records in SQLite using `(namespace,key)` as a primary key. `Store()` defaults to memory for tests; explicitly pass a durable absolute filename in applications. Parent directories must already exist. All instances writing a given SQLite database serialize through `BEGIN IMMEDIATE`, with a five-second busy timeout. A process-local reentrant lock protects the connection. Keep one long-lived Store per application process and close it at shutdown.

A replacement store must implement `get(namespace,key)`, `put`, `delete`, `all`, `transaction` and `close`. `get`/`all` must return detached JSON values. `transaction()` must atomically commit or roll back and serialize competing writers, including across processes. Nested transactions are unsupported. Provider calls must stay outside write transactions. Do not replace this with unguarded Mongo upserts: concurrency guarantees depend on the entire transaction boundary.

SQLite is a practical single-host starting adapter. `all()` scans a namespace: the reference implementation is unsuitable for large-scale reporting, large queues or many millions of sessions. Build indexed repositories/SQL tables or a transactional server database adapter before that scale. SQLite files need private permissions, backups and restore testing. Multiple hosts should not share an SQLite file over a network filesystem.

## Module ownership

| Capability | Python import / npm entry | Integration guide |
|---|---|---|
| Authentication and sessions | `reusable_foundations.identity.Identity` | [Identity](modules/identity.md) |
| Registration, verification and recovery | `Identity` proof methods | [Registration](modules/registration.md) |
| Phone OTP | `FirebasePhone`, `./firebase`, `PhoneLoginForm` | [Phone OTP](modules/phone-otp.md) |
| Razorpay payments | `payments.Payments`, `payments.Razorpay`, `./checkout` | [Payments](modules/payments.md) |
| Subscriptions and entitlements | `entitlements.Subscriptions` | [Subscriptions](modules/subscriptions.md) |
| Quotas, trials and credits | `entitlements.Quotas` | [Quotas](modules/quotas.md) |
| Transactional email | `messaging.Emailer` | [Email](modules/email.md) |
| Background jobs | `jobs.Jobs` | [Jobs](modules/jobs.md) |
| Notifications | `messaging.Notifications` | [Notifications](modules/notifications.md) |
| Permissions and tenancy | `security.Permissions` | [Permissions](modules/permissions.md) |
| Frontend API client | `@reusable-foundations/react/client` | [API client](modules/api-client.md) |
| UI components | `@reusable-foundations/react` | [UI](modules/ui.md) |
| Audit | `observability.Audit` | [Audit](modules/audit.md) |
| Analytics | `observability.Analytics` | [Analytics](modules/analytics.md) |
| Private file storage | `storage.Files` | [Storage](modules/storage.md) |

The toolkit does not depend on TrailPulse imports, flight routes, its dotenv files, plan IDs, database, copied account records or providers. This is a generic implementation, not an automatic migration of any existing application.

## Delivery and consistency

Database changes are transactional inside each service operation. External provider actions and local commits are not one transaction. Jobs are at least once; handlers must deduplicate using their job ID. Unknown payment/subscription creation remains `creating` until an operator reconciles it with provider records. Do not delete those rows to retry blindly.

Receipts and quota grants are separate. Business code maps a verified receipt to a stable grant ID, applies a specific product's benefits, and revokes the grant after refund/dispute. It must recheck receipt state on access or use durable reconciliation; observing a paid receipt once is insufficient forever. No automatic tax, invoice-compliance, dispute, chargeback or refund initiation product is provided.

## Extension and versioning

Keep project-specific callbacks, catalogues, role maps and templates in the consuming application. Pin released package versions; change public interfaces with semantic versioning. The initial 0.1 series is experimental, so pin exact versions. A deployment should select and lock SDK versions independently and run the adapter tests against those versions. No package was published to a registry by this task.
