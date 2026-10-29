# @reusable-foundations/react

Install this directory into a React 18/19 application with `npm install ../Reusable_modules/packages/react`. React is a peer dependency; do not bundle a second copy. Plain ESM source needs no JSX transform.

Exports:

- `@reusable-foundations/react`: AuthProvider, useAuth, LoginForm, PhoneLoginForm, Button, Field, Status, Dialog.
- `/client`: createClient, ApiError. Standalone fetch client; no React dependency.
- `/checkout`: checkout, loadRazorpay. Server-confirmed one-time Razorpay Checkout.
- `/firebase`: firebasePhoneAdapter. Inject the new application's modular Firebase SDK functions.
- `/styles.css`: optional component styling.

See the toolkit's [quick start](../../docs/quickstart.md), [API client](../../docs/modules/api-client.md), [UI](../../docs/modules/ui.md), [phone](../../docs/modules/phone-otp.md) and [payment guide](../../docs/modules/payments.md) for complete integration. Those repository guides are not included in the small npm tarball; retain the toolkit documentation alongside your release artifact.

This repository publishes modules and integration documentation only. Provider credentials and live account configuration belong to the consuming application. Package publication and licensing are owner decisions; the initial package is marked UNLICENSED.
