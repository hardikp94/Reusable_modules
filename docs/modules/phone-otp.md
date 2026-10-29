# Phone OTP

Install the `[firebase]` extra in your backend and the modular Firebase SDK in the frontend. Initialize both with the NEW project's Firebase configuration. Enable Phone Authentication, authorized domains and appropriate SMS policy in that Firebase account.

```python
import firebase_admin
from reusable_foundations.identity import FirebasePhone
from reusable_foundations.fastapi import identity_router

# Configure ADC/service credentials in the server environment, never in browser code.
firebase_app = firebase_admin.initialize_app()
provider = FirebasePhone(firebase_app)
app.include_router(identity_router(identity, limiter, origin=app_origin, phone_provider=provider))
```

`FirebasePhone.verify` delegates signature/project/issuer checks to Admin SDK verification with `check_revoked=True`. It additionally requires phone sign-in, a normalized phone and authentication within five minutes. `phone_signin` requires an unexpired challenge for that exact phone; it creates an account only after proof or reuses the existing identity. It does not merge separate phone/email identities.

```jsx
import {signInWithPhoneNumber, RecaptchaVerifier, setPersistence, inMemoryPersistence} from "firebase/auth";
import {firebasePhoneAdapter} from "@reusable-foundations/react/firebase";
import {PhoneLoginForm} from "@reusable-foundations/react";

await setPersistence(firebaseAuth, inMemoryPersistence);
const verifier = new RecaptchaVerifier(firebaseAuth, "recaptcha-container", {size: "invisible"});
const provider = firebasePhoneAdapter({auth: firebaseAuth, signInWithPhoneNumber, verifier});
// Keep provider stable; render within AuthProvider and supply the container.
// <><div id="recaptcha-container" /><PhoneLoginForm provider={provider} /></>
```

The form requests a backend challenge, sends through the explicit browser adapter, confirms OTP, then sends Firebase ID token + challenge to the backend. A backend start response is not a claim of SMS delivery. The form handles resend countdown, duplicate submission and changing the number. `provider.cancel()` ignores stale confirmations; it cannot retract an SMS already accepted by Firebase. Clean up reCAPTCHA and sign out the Firebase client session in your application's lifecycle as appropriate.

Input accepts explicit international phone numbers (`+` plus country code). It removes spaces/parentheses/hyphens and checks E.164-shaped length; it does not provide a country catalogue or prove a number is SMS reachable. Use a pinned phone-number parsing library if you need national input/country selection. Never implement public OTP verification with a local fixed code or a test provider.

Real Firebase verification and SMS delivery were not exercised in offline tests. Follow [Firebase token verification](https://firebase.google.com/docs/auth/admin/verify-id-tokens) and [web phone auth](https://firebase.google.com/docs/auth/web/phone-auth) for project-specific setup.
