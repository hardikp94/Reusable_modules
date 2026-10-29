# Frontend API client

```javascript
import {createClient, ApiError} from "@reusable-foundations/react/client";
const client = createClient({baseUrl: "", authPath: "/auth"});
await client.login(email, password);
const profile = await client.request("/private");
await client.logout();
```

The standalone ESM client needs fetch, Headers and browser-standard APIs. It has no React dependency when imported through `/client`. `fetchImpl` can be injected for tests. It adds the custom write-protection header, JSON Content-Type, `credentials: include` and an in-memory bearer token. It never writes localStorage/sessionStorage.

On a 401 from an authenticated request, it coordinates one shared refresh across concurrent callers, then retries the request once. Non-authenticated requests can set `authenticated:false`. 403/429/500/503 are not treated as expired sessions. `ApiError` exposes status, detail and Retry-After. Network/invalid-JSON errors propagate; the host decides user-facing messages.

`request(path,{method,body,signal})` supports an AbortSignal. Use local paths beginning with `/`; protocol-relative URLs and backslashes are rejected. `baseUrl` is trusted application configuration, never user input. Response bodies must be JSON, except 204. Raw downloads/streaming require a host adapter.

Refresh does not rotate the persistent cookie or slide its expiry. Logout clears access immediately and asks the backend to revoke the cookie session; if the server is unreachable it reports an error because the browser cookie may still be valid. A late refresh cannot restore the client's bearer token after logout. Same-tab coordination does not synchronize different tabs.

The retry mechanism does not supply idempotency for your mutation endpoints. Use stable operation IDs and server-side deduplication where a request can have side effects. To restore a session use `client.refresh()` or React AuthProvider. Keep client identity stable across renders.
