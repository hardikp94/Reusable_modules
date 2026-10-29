"""Password/phone identity and revocable opaque-token sessions."""
import hashlib
import hmac
import secrets
import time
import re


class IdentityError(ValueError):
    pass


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def password_hash(password):
    if not isinstance(password, str) or not 12 <= len(password) <= 1024:
        raise IdentityError("Password must contain 12 to 1024 characters")
    salt = secrets.token_hex(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 600_000)
    return f"pbkdf2_sha256$600000${salt}${derived.hex()}"


def password_matches(password, encoded):
    try:
        algorithm, rounds, salt, expected = encoded.split("$")
        if algorithm != "pbkdf2_sha256" or len(password) > 1024:
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(rounds)).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError, AttributeError):
        return False


def normalize_phone(phone):
    # Explicit international input; country selection belongs to the UI.
    phone = re.sub(r"[\s()-]", "", phone)
    if not re.fullmatch(r"\+[1-9][0-9]{7,14}", phone):
        raise IdentityError("Use an international phone number, e.g. +12025550123")
    return phone


class Identity:
    def __init__(self, store, *, clock=time.time, access_ttl=1800, session_ttl=604800):
        self.store, self.clock = store, clock
        if not 0 < access_ttl <= session_ttl:
            raise ValueError("Invalid session lifetimes")
        self.access_ttl, self.session_ttl = access_ttl, session_ttl
        self._dummy = password_hash(secrets.token_urlsafe(32))

    def register(self, email, password, *, profile=None):
        email = email.strip().casefold()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
            raise IdentityError("Invalid email")
        encoded = password_hash(password)
        with self.store.transaction():
            if self.store.get("identifiers", "email:" + email):
                raise IdentityError("Registration unavailable")
            uid = secrets.token_hex(16)
            user = {"id": uid, "email": email, "password": encoded, "active": True, "version": 1, "profile": profile or {}, "email_verified": False}
            self.store.put("users", uid, user)
            self.store.put("identifiers", "email:" + email, {"id": uid})
        return self.public(user)

    @staticmethod
    def public(user):
        return {k: v for k, v in user.items() if k not in {"password", "version"}}

    def login(self, email, password):
        link = self.store.get("identifiers", "email:" + email.strip().casefold())
        user = self.store.get("users", link["id"]) if link else None
        valid = password_matches(password, user.get("password", self._dummy) if user else self._dummy)
        if not valid or not user or not user["active"]:
            raise IdentityError("Invalid credentials")
        return self.issue_session(user["id"])

    def issue_session(self, uid):
        with self.store.transaction():
            user = self.store.get("users", uid)
            if not user or not user["active"]:
                raise IdentityError("Account unavailable")
            now, sid = self.clock(), secrets.token_hex(16)
            access, refresh = secrets.token_urlsafe(32), secrets.token_urlsafe(48)
            self.store.put("sessions", sid, {"id": sid, "user": uid, "version": user["version"], "expires": now + self.session_ttl, "revoked": False})
            self.store.put("access", digest(access), {"session": sid, "expires": now + self.access_ttl})
            self.store.put("refresh", digest(refresh), {"session": sid})
        return {"access_token": access, "refresh_token": refresh, "expires_in": self.access_ttl, "user": self.public(user)}

    def _session(self, sid):
        session = self.store.get("sessions", sid)
        user = self.store.get("users", session["user"]) if session else None
        if not session or session["revoked"] or session["expires"] <= self.clock() or not user or not user["active"] or user["version"] != session["version"]:
            raise IdentityError("Session expired")
        return session, user

    def authenticate(self, token):
        record = self.store.get("access", digest(token))
        if not record or record["expires"] <= self.clock():
            raise IdentityError("Session expired")
        return self.public(self._session(record["session"])[1])

    def refresh(self, token):
        with self.store.transaction():
            record = self.store.get("refresh", digest(token))
            if not record:
                raise IdentityError("Session expired")
            session, user = self._session(record["session"])
            access = secrets.token_urlsafe(32)
            self.store.put("access", digest(access), {"session": session["id"], "expires": min(self.clock() + self.access_ttl, session["expires"])})
        return {"access_token": access, "expires_in": min(self.access_ttl, session["expires"] - self.clock()), "user": self.public(user)}

    def logout(self, refresh_token):
        with self.store.transaction():
            record = self.store.get("refresh", digest(refresh_token))
            if record:
                session = self.store.get("sessions", record["session"])
                session["revoked"] = True
                self.store.put("sessions", session["id"], session)

    def challenge(self, target, purpose, *, ttl=300, user_id=None):
        if purpose not in {"phone_signin", "verify_email", "reset_password", "link_phone", "link_email"}:
            raise IdentityError("Unsupported purpose")
        if ttl <= 0 or (purpose.startswith("link_") and not user_id):
            raise IdentityError("Invalid challenge binding")
        target = normalize_phone(target) if purpose in {"phone_signin", "link_phone"} else target.strip().casefold()
        token = secrets.token_urlsafe(32)
        link = self.store.get("identifiers", "email:" + target) if purpose in {"verify_email", "reset_password"} else None
        self.store.put("challenges", digest(token), {"target": target, "purpose": purpose, "user_id": user_id, "account_id": link["id"] if link else None, "expires": self.clock() + ttl, "used": False})
        return token

    def consume(self, token, purpose, target, *, user_id=None):
        # Caller must hold a transaction when combining this with other writes.
        record = self.store.get("challenges", digest(token))
        if not record or record["used"] or record["expires"] <= self.clock() or record["purpose"] != purpose or record["target"] != target or record.get("user_id") != user_id:
            raise IdentityError("Invalid or expired proof")
        if purpose in {"verify_email", "reset_password"}:
            link = self.store.get("identifiers", "email:" + target)
            if not link or record.get("account_id") != link["id"]:
                raise IdentityError("Proof account changed")
        record["used"] = True
        self.store.put("challenges", digest(token), record)

    def phone_signin(self, challenge, id_token, provider):
        phone = normalize_phone(provider.verify(id_token))
        with self.store.transaction():
            self.consume(challenge, "phone_signin", phone)
            link = self.store.get("identifiers", "phone:" + phone)
            if link:
                uid = link["id"]
                if not self.store.get("users", uid)["active"]:
                    raise IdentityError("Account unavailable")
            else:
                uid = secrets.token_hex(16)
                self.store.put("users", uid, {"id": uid, "phone": phone, "active": True, "version": 1, "profile": {}, "phone_verified": True})
                self.store.put("identifiers", "phone:" + phone, {"id": uid})
        return self.issue_session(uid)

    def verify_email(self, token, email):
        email = email.strip().casefold()
        with self.store.transaction():
            self.consume(token, "verify_email", email)
            link = self.store.get("identifiers", "email:" + email)
            if not link:
                raise IdentityError("Invalid proof")
            user = self.store.get("users", link["id"])
            user["email_verified"] = True
            self.store.put("users", user["id"], user)

    def change_password(self, uid, current_password, new_password):
        encoded = password_hash(new_password)
        with self.store.transaction():
            user = self.store.get("users", uid)
            if not user or not user["active"] or not password_matches(current_password, user.get("password", "")):
                raise IdentityError("Invalid credentials")
            user.update(password=encoded, version=user["version"] + 1)
            self.store.put("users", uid, user)

    def link_contact(self, uid, token, target, *, kind, provider=None, id_token=None):
        if kind not in {"email", "phone"}:
            raise IdentityError("Unsupported contact")
        target = normalize_phone(target) if kind == "phone" else target.strip().casefold()
        if kind == "phone" and (provider is None or normalize_phone(provider.verify(id_token)) != target):
            raise IdentityError("Phone proof mismatch")
        if kind == "email" and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", target):
            raise IdentityError("Invalid email")
        with self.store.transaction():
            self.consume(token, "link_" + kind, target, user_id=uid)
            user = self.store.get("users", uid)
            existing = self.store.get("identifiers", kind + ":" + target)
            if not user or not user["active"] or existing and existing["id"] != uid:
                raise IdentityError("Contact unavailable")
            if user.get(kind) and user[kind] != target:
                self.store.delete("identifiers", kind + ":" + user[kind])
            user[kind] = target
            user[kind + "_verified"] = True
            user["version"] += 1
            self.store.put("identifiers", kind + ":" + target, {"id": uid})
            self.store.put("users", uid, user)
        return self.public(user)

    def reset_password(self, token, email, password):
        email, encoded = email.strip().casefold(), password_hash(password)
        with self.store.transaction():
            self.consume(token, "reset_password", email)
            link = self.store.get("identifiers", "email:" + email)
            if not link:
                raise IdentityError("Invalid proof")
            user = self.store.get("users", link["id"])
            user.update(password=encoded, version=user["version"] + 1)
            self.store.put("users", user["id"], user)


class FirebasePhone:
    """Pass an explicitly initialized firebase_admin App; never loads dotenv."""
    def __init__(self, app, *, clock=time.time, max_age=300):
        self.app, self.clock, self.max_age = app, clock, max_age

    def verify(self, token):
        from firebase_admin import auth
        claims = auth.verify_id_token(token, app=self.app, check_revoked=True)
        age = self.clock() - claims.get("auth_time", 0)
        if claims.get("firebase", {}).get("sign_in_provider") != "phone" or not 0 <= age <= self.max_age:
            raise IdentityError("Fresh phone proof required")
        return normalize_phone(claims.get("phone_number", ""))
