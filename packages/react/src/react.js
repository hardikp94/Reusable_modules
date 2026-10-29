import React, {createContext, useContext, useEffect, useRef, useState, useId} from "react";
const h = React.createElement;
const AuthContext = createContext(null);

export function AuthProvider({client, children}) {
  const [state, setState] = useState({status: "loading", user: null, error: null});
  const sequence = useRef(0);
  async function restore() {
    const current = ++sequence.current;
    setState({status: "loading", user: null, error: null});
    try {
      const result = await client.refresh();
      if (current === sequence.current) setState({status: "authenticated", user: result.user, error: null});
    } catch (error) {
      if (current === sequence.current) setState({status: error.status === 401 ? "anonymous" : "error", user: null, error});
    }
  }
  useEffect(() => { restore(); return () => { ++sequence.current; }; }, [client]);
  async function signIn(method, ...args) {
    const current = ++sequence.current;
    const user = await client[method](...args);
    if (current === sequence.current) setState({status: "authenticated", user, error: null});
    return user;
  }
  async function logout() {
    ++sequence.current;
    try { await client.logout(); setState({status: "anonymous", user: null, error: null}); }
    catch (error) { setState({status: "error", user: null, error}); throw error; }
  }
  return h(AuthContext.Provider, {value: {...state, client, retry: restore, login: (...args) => signIn("login", ...args), phoneVerify: (...args) => signIn("phoneVerify", ...args), logout}}, children);
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("Wrap the application in AuthProvider");
  return value;
}

export function Button({busy = false, children, disabled, ...props}) {
  return h("button", {...props, className: "rf-button " + (props.className || ""), disabled: disabled || busy, "aria-busy": busy}, busy ? "Please wait…" : children);
}

export function Field({label, error, ...props}) {
  const generated = useId(), id = props.id || generated;
  return h("div", {className: "rf-field"}, h("label", {htmlFor: id}, label), h("input", {...props, id, "aria-invalid": !!error, "aria-describedby": error ? id + "-error" : undefined}), error && h("span", {id: id + "-error", role: "alert"}, error));
}

export function Status({error, loading, children}) {
  return error ? h("p", {role: "alert"}, error.message || String(error)) : loading ? h("p", {role: "status"}, "Loading…") : children;
}

export function Dialog({open, title, onClose, children}) {
  const ref = useRef(null), id = useId();
  useEffect(() => {
    if (open && !ref.current.open) ref.current.showModal();
    else if (!open && ref.current.open) ref.current.close();
  }, [open]);
  return h("dialog", {ref, "aria-labelledby": id, onCancel: onClose, onClose}, h("h2", {id}, title), children, h(Button, {type: "button", onClick: onClose}, "Close"));
}

export function LoginForm({onSuccess, mode = "login"}) {
  const auth = useAuth();
  const [email, setEmail] = useState(""), [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false), [error, setError] = useState(null);
  async function submit(event) {
    event.preventDefault(); if (busy) return;
    setBusy(true); setError(null);
    try {
      const user = mode === "register" ? await auth.client.register(email, password) : await auth.login(email, password);
      onSuccess?.(user); // Registration does not implicitly create a session.
    } catch (failure) { setError(failure); }
    finally { setBusy(false); }
  }
  return h("form", {onSubmit: submit, className: "rf-form"},
    h(Field, {label: "Email", type: "email", autoComplete: "email", required: true, maxLength: 254, value: email, disabled: busy, onChange: e => setEmail(e.target.value)}),
    h(Field, {label: "Password", type: "password", autoComplete: mode === "register" ? "new-password" : "current-password", minLength: mode === "register" ? 12 : undefined, maxLength: 1024, required: true, value: password, disabled: busy, onChange: e => setPassword(e.target.value)}),
    h(Status, {error}), h(Button, {type: "submit", busy}, mode === "register" ? "Create account" : "Sign in"));
}

export function PhoneLoginForm({provider, onSuccess, resendSeconds = 60}) {
  const auth = useAuth();
  const [phone, setPhone] = useState(""), [code, setCode] = useState("");
  const [challenge, setChallenge] = useState(null), [busy, setBusy] = useState(false);
  const [error, setError] = useState(null), [remaining, setRemaining] = useState(0);
  const version = useRef(0);
  useEffect(() => () => { ++version.current; provider.cancel?.(); }, [provider]);
  useEffect(() => {
    if (!remaining) return;
    const timer = setTimeout(() => setRemaining(n => Math.max(0, n - 1)), 1000);
    return () => clearTimeout(timer);
  }, [remaining]);
  async function send() {
    if (busy || remaining) return;
    const current = ++version.current;
    setBusy(true); setError(null);
    try {
      const result = await auth.client.phoneStart(phone);
      await provider.send(phone);
      if (current === version.current) { setChallenge(result.challenge); setRemaining(resendSeconds); }
    } catch (failure) { if (current === version.current) setError(failure); }
    finally { if (current === version.current) setBusy(false); }
  }
  async function submit(event) {
    event.preventDefault(); if (busy) return;
    if (!challenge) return send();
    const current = ++version.current;
    setBusy(true); setError(null);
    try {
      const token = await provider.confirm(code);
      if (current !== version.current) return;
      const user = await auth.phoneVerify(challenge, token);
      if (current === version.current) onSuccess?.(user);
    } catch (failure) { if (current === version.current) setError(failure); }
    finally { if (current === version.current) setBusy(false); }
  }
  return h("form", {onSubmit: submit, className: "rf-form"},
    h(Field, {label: "Phone number including country code", type: "tel", autoComplete: "tel", placeholder: "+12025550123", required: true, value: phone, disabled: busy || !!challenge, onChange: e => setPhone(e.target.value)}),
    challenge && h(Field, {label: "Verification code", inputMode: "numeric", autoComplete: "one-time-code", pattern: "[0-9]{6}", maxLength: 6, required: true, value: code, disabled: busy, onChange: e => setCode(e.target.value)}),
    h(Status, {error}), h(Button, {type: "submit", busy}, challenge ? "Verify code" : "Send code"),
    challenge && h(Button, {type: "button", disabled: busy || remaining > 0, onClick: send}, remaining ? `Resend in ${remaining}s` : "Resend code"),
    challenge && h(Button, {type: "button", disabled: busy, onClick: () => { ++version.current; provider.cancel?.(); setChallenge(null); setCode(""); setError(null); }}, "Change number"));
}
