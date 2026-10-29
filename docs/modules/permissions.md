# Permissions and tenancy

```python
from reusable_foundations.security import Permissions, Forbidden

permissions = Permissions(store, {
    "reader": ["documents:read"],
    "manager": ["documents:read", "documents:write", "audit:read"],
})
# Trusted provisioning only, after checking the grantor's authority:
permissions.grant("company-1", user_id, "reader")
permissions.require("company-1", user_id, "documents:read", resource_tenant=document["tenant"])
```

The membership key safely encodes tenant/user separately; caller-controlled delimiters cannot collide. One effective role per user/tenant is supported. Unknown roles and missing permissions fail closed. There is no wildcard permission or implicit platform-admin bypass. Define each project's role map without copying TrailPulse roles.

Always authenticate first, look up the resource, then check its actual stored tenant. Passing only a requested tenant is insufficient. The module authorizes operations; it does not automatically filter every application database query. Add owner checks for personal resources and tenant predicates to every list/read/write route.

Provisioning and membership administration are trusted APIs; do not expose `grant` publicly. Invitations, role hierarchies, multiple roles, ABAC, organization CRUD, ownership transfer and removal APIs are not included. A current membership row can be removed using an authorized host service and Store.delete. The authorization test suite exercises wrong-tenant and missing-permission paths.
