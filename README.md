# Reusable modules

Generic Python and React modules that you can import into new or existing projects. Each application supplies its own branding, credentials, products, plans and business rules.

Start with the [integration guide](docs/quickstart.md), browse the [module catalogue](docs/architecture.md#module-ownership), and read [configuration](docs/configuration.md) and [security boundaries](docs/security.md).

## Install

Clone this repository beside your application:

```powershell
git clone https://github.com/hardikp94/Reusable_modules.git
```

From your application's Python virtual environment:

```powershell
python -m pip install "../Reusable_modules[api]"
```

From your React application:

```powershell
npm install "../Reusable_modules/packages/react"
```

Adjust paths to your clone. Python core modules need no third-party runtime dependencies. The optional FastAPI adapter is installed by `[api]`. React 18/19 is a peer dependency.

```python
from reusable_foundations.store import Store
from reusable_foundations.identity import Identity

store = Store("application.sqlite3")
identity = Identity(store)
```

```jsx
import {AuthProvider, LoginForm} from "@reusable-foundations/react";
import {createClient} from "@reusable-foundations/react/client";
import "@reusable-foundations/react/styles.css";

const client = createClient();
export default function App() {
  return <AuthProvider client={client}><LoginForm /></AuthProvider>;
}
```

The React form requires the matching backend identity routes; see the integration guide.

## Included capabilities

| Capability | Guide |
|---|---|
| Authentication and sessions | [Identity](docs/modules/identity.md) |
| Registration, verification and recovery | [Registration](docs/modules/registration.md) |
| Firebase phone OTP | [Phone OTP](docs/modules/phone-otp.md) |
| Razorpay payments | [Payments](docs/modules/payments.md) |
| Subscriptions and feature access | [Subscriptions](docs/modules/subscriptions.md) |
| Quotas, trials and credits | [Quotas](docs/modules/quotas.md) |
| Transactional email | [Email](docs/modules/email.md) |
| Background jobs | [Jobs](docs/modules/jobs.md) |
| Notifications | [Notifications](docs/modules/notifications.md) |
| Permissions and tenancy | [Permissions](docs/modules/permissions.md) |
| Frontend API client | [API client](docs/modules/api-client.md) |
| React UI components | [UI](docs/modules/ui.md) |
| Audit events | [Audit](docs/modules/audit.md) |
| Analytics | [Analytics](docs/modules/analytics.md) |
| Private file storage | [Storage](docs/modules/storage.md) |

## Repository layout

```text
src/reusable_foundations/   Python services and framework/provider adapters
packages/react/            React components and standalone JavaScript entry points
docs/                      Integration guides and module documentation
examples/                  Small examples showing how to wire imports
pyproject.toml             Python package definition
```

This repository contains modules, package definitions and usage documentation/examples. Internal tooling, test suites, build artifacts, environment files and application data are excluded. No project credentials, existing application's source or account data are included.

Version 0.1.0 is an initial foundation, not a production certification. Live provider integration, application-specific authorization, subscription reconciliation, storage validation/scanning and operational configuration must be completed in the consuming project. The module guides state each boundary. The owner has not selected a redistribution license; the React package is marked UNLICENSED.
