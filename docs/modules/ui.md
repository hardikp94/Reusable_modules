# React UI components

```jsx
import {AuthProvider, LoginForm, PhoneLoginForm, useAuth,
  Button, Field, Status, Dialog} from "@reusable-foundations/react";
import "@reusable-foundations/react/styles.css";
```

`AuthProvider({client})` restores the session on mount. `useAuth()` returns `status`, `user`, `error`, `retry`, `login`, `phoneVerify`, `logout`, `client`. Status is `loading`, `authenticated`, `anonymous` (only an explicit 401), or `error`. Render a retry action on transient errors. Unmount/stale response guards prevent obsolete restoration from replacing a later action.

`LoginForm({mode:'login'|'register',onSuccess})` renders labelled email/password inputs and duplicate-submission protection. Registration invokes the register API but does not sign the account in. `onSuccess` receives the new user, so the host can display verification guidance or switch to login. No router dependency or branding is embedded.

`PhoneLoginForm({provider,onSuccess,resendSeconds=60})` supports explicit international input, OTP request/confirm, resend countdown and change-number. See [phone integration](phone-otp.md). It does not include a country dropdown or national-number metadata.

`Button` accepts `busy` and native button props. `Field` associates a label, input and optional error using useId. `Status` renders an alert or loading status. `Dialog` uses the native modal dialog element for focus containment/escape behavior; provide controlled `open`, `title`, `onClose`. Use explicit `type="button"` for non-submit buttons inside forms.

CSS is small, optional, theme-neutral and uses flexible sizing, visible focus and 44px button minimum height. Override styles in the consuming app. Component rendering tests do not establish keyboard, screen-reader, physical-device or responsive browser support. Validate those in the actual project; no visual baseline is supplied.
