import React, {useMemo, useState} from "react";
import {AuthProvider, LoginForm, useAuth, Button} from "@reusable-foundations/react";
import {createClient} from "@reusable-foundations/react/client";
import "@reusable-foundations/react/styles.css";

function Screen() {
  const auth = useAuth();
  const [mode, setMode] = useState("login");
  if (auth.status === "loading") return <p role="status">Restoring session…</p>;
  if (auth.status === "error") return <><p role="alert">Session service unavailable</p><Button onClick={auth.retry}>Retry</Button></>;
  if (auth.user) return <><p>Signed in as {auth.user.email || auth.user.phone}</p><Button onClick={() => auth.logout().catch(() => {})}>Sign out</Button></>;
  return <><LoginForm key={mode} mode={mode} onSuccess={() => setMode("login")} /><Button onClick={() => setMode(mode === "login" ? "register" : "login")}>{mode === "login" ? "Create account" : "Back to sign in"}</Button></>;
}

export default function App() {
  const client = useMemo(() => createClient({baseUrl: "http://localhost:8000"}), []);
  return <AuthProvider client={client}><Screen /></AuthProvider>;
}
