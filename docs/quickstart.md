# Integrate into a new or existing project

## 1. Obtain and install the modules

```powershell
git clone https://github.com/hardikp94/Reusable_modules.git
```

Clone outside your application's source directory. For a new backend, create a virtual environment; for an existing backend, activate its existing environment and review dependency compatibility before installation. The examples below assume this repository is cloned at `../Reusable_modules` relative to your application.

```powershell
python -m venv .venv
.venv/Scripts/Activate.ps1
python -m pip install "../Reusable_modules[api]"
```

Linux/macOS activation is `source .venv/bin/activate`. If your environment already exists, skip its creation. For core Python services without FastAPI, omit `[api]`. Install additional provider adapters only when required:

```powershell
python -m pip install "../Reusable_modules[firebase,razorpay,ses]"
```

Keep the installation in your application environment; do not copy module files into every new project. For development use `pip install -e "../Reusable_modules[api]"`; for stable consumption pin a commit or built artifact. An alternative Python installation pinned to a commit is:

```powershell
python -m pip install "reusable-foundations[api] @ git+https://github.com/hardikp94/Reusable_modules.git@COMMIT_SHA"
```

Replace COMMIT_SHA with a real commit from this repository. Do not assume a release tag exists.

## 2. Mount backend identity routes

In a NEW application's `app.py`:

```python
import os
from fastapi import FastAPI, Depends
from reusable_foundations.store import Store
from reusable_foundations.identity import Identity
from reusable_foundations.security import RateLimiter
from reusable_foundations.fastapi import identity_router, authenticated_user

store = Store(os.environ["APP_DATABASE_FILE"])
identity = Identity(store)
limiter = RateLimiter(store, os.environ["APP_RATE_LIMIT_SECRET"].encode())
app = FastAPI()
app.include_router(identity_router(identity, limiter, origin="https://your-app.example"))

@app.get("/private")
def private(user=Depends(authenticated_user(identity))):
    return {"user_id": user["id"]}
```

Create the database's private parent directory first. Supply an absolute durable filename and a persistent random rate-limit secret of at least 32 bytes. Close Store in the application's shutdown/lifespan handler. Nothing automatically loads dotenv or copies another project's credentials.

In an EXISTING FastAPI application, reuse your `app` instead of creating another one and call `app.include_router(...)` during startup configuration. Check for route collisions. You can mount `identity_router(..., prefix="/foundation-auth")` and set the same `authPath` in the frontend. Existing CORS, trusted-proxy and authorization configuration must be reconciled explicitly.

The API adapter defaults to secure refresh cookies and exact HTTPS Origin checks plus its required custom request header. Serve frontend and API through the same origin when possible. HTTP is only permitted for explicitly configured loopback development. Do not weaken production security to make a local sample work.

For a local starting example, install `[api]`, then run from the repository root:

```powershell
python -m uvicorn examples.api.app:app --host 127.0.0.1 --port 8000
```

The example is configured for a frontend at `http://localhost:5173`; use that hostname consistently. It enables no real payment/OTP/email providers and creates an example SQLite file locally. Do not expose it unchanged as production.

## 3. Add the frontend package

From your React application directory:

```powershell
npm install "../Reusable_modules/packages/react"
```

React 18 or 19 must be available in your app. The package is not published to npm, so `npm install @reusable-foundations/react` alone will not work. No second copy of React should be bundled. Keep a lockfile in the consuming application.

```jsx
import React, {useMemo} from "react";
import {AuthProvider, LoginForm} from "@reusable-foundations/react";
import {createClient} from "@reusable-foundations/react/client";
import "@reusable-foundations/react/styles.css";

export default function App() {
  const client = useMemo(() => createClient({authPath: "/auth"}), []);
  return <AuthProvider client={client}><LoginForm /></AuthProvider>;
}
```

In an EXISTING React app, wrap only the part that uses this identity flow or deliberately integrate the provider into your existing session architecture. Do not run two competing session providers against the same identity without a plan. Use a unique route prefix if needed. The stylesheet is optional; override or replace it with the project's theme.

For separate local frontend/backend ports, use the exact allowed-origin configuration shown in [examples/api/app.py](../examples/api/app.py) and `createClient({baseUrl:"http://localhost:8000"})`. Production normally uses relative same-origin paths. The API base URL must be trusted application configuration.

The fuller [React example](../examples/react/App.jsx) shows registration/login switching, restoration, retry and logout. Registration does not automatically sign in or send verification email; add the host's verification policy using the [registration guide](modules/registration.md).

## 4. Add other modules selectively

Choose only the capabilities your product needs from the [module catalogue](architecture.md#module-ownership). Configure your own credentials, products, roles, templates and storage. Payment prices and subscription plans are application configuration, not fixed to a previous project. Quotas are optional. Components share behavior while each app chooses its styling.

For Razorpay use the [payments guide](modules/payments.md); for recurring billing follow the separate [subscriptions guide](modules/subscriptions.md), including provider reconciliation. Mount the payment router only after configuring its authenticated ownership and server-owned catalogue. A successful browser callback alone never grants access.

Keep privileged operations such as role grants, quota grants, proof issuance, subscription receipt writes and audit queries behind server-owned authorization. Never expose raw library methods as unrestricted public endpoints.

## 5. Adopt within an existing project safely

Installing a package does not migrate existing users, sessions, roles, billing records or files. The toolkit uses opaque session tokens, PBKDF2 password hashes and its Store interface. Existing JWT/bcrypt/other database schemas will need an explicit adapter or migration strategy. Do not point the example at existing application data.

Begin with a separate development database and a small isolated route. Map stable account IDs, verify ownership, plan any password/session migration, choose a rollback path, then exercise your existing application's affected journeys. Keep other modules optional until you need them. Live provider, browser, accessibility and operational validation belongs to the consuming project.

## 6. Build versioned local artifacts

Build the Python wheel from this clone:

```powershell
python -m pip install build
python -m build
```

For React:

```powershell
cd packages/react
npm pack
```

Install the resulting wheel or tarball into the consuming application and pin its version. A local npm path may be a link; a tarball gives an immutable snapshot. This source repository intentionally does not commit generated artifacts, test suites or internal tools. Publishing to a registry is a separate owner decision.
