"""Optional FastAPI adapter. Explicit same-origin writes and HttpOnly refresh cookie."""
from urllib.parse import urlsplit
from fastapi import APIRouter, HTTPException, Request, Response, Depends
from pydantic import BaseModel, Field, ConfigDict
from .identity import IdentityError, normalize_phone
from .security import RateLimited


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=1024)


class PhoneStart(BaseModel):
    phone: str = Field(min_length=8, max_length=32)


class PhoneVerify(BaseModel):
    challenge: str = Field(max_length=128)
    id_token: str = Field(max_length=8192)


def identity_router(identity, limiter, *, origin, phone_provider=None, secure=True, prefix="/auth"):
    parsed = urlsplit(origin)
    if parsed.scheme not in {"https", "http"} or not parsed.netloc or parsed.path or parsed.query or parsed.fragment or parsed.username:
        raise ValueError("Origin must be scheme://host[:port]")
    if parsed.scheme != "https" and (secure or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}):
        raise ValueError("HTTP allowed only for explicit loopback development")
    router = APIRouter(prefix=prefix, tags=["identity"])
    cookie = "rf_refresh"

    def no_cache(response):
        response.headers["Cache-Control"] = "no-store"

    def guard(request, response, *, bucket, identifier=""):
        no_cache(response)
        if request.headers.get("origin") != origin or request.headers.get("x-foundations-request") != "1":
            raise HTTPException(403, "Untrusted browser request")
        source = request.client.host if request.client else "unknown"
        # Deliberately ignores arbitrary X-Forwarded-For. Configure trusted proxy middleware externally.
        try:
            limiter.admit(bucket + ":source", source, limit=30)
            if identifier:
                limiter.admit(bucket + ":account", identifier, limit=10)
        except RateLimited as error:
            raise HTTPException(429, "Too many requests", headers={"Retry-After": str(error.retry_after)}) from None

    def session_response(result, response):
        no_cache(response)
        token = result.pop("refresh_token", None)
        if token:
            response.set_cookie(cookie, token, max_age=identity.session_ttl, httponly=True, secure=secure, samesite="lax", path=prefix)
        return result

    @router.post("/register", status_code=201)
    def register(body: Credentials, request: Request, response: Response):
        guard(request, response, bucket="register", identifier=body.email.strip().casefold())
        try:
            return identity.register(body.email, body.password)
        except IdentityError as error:
            raise HTTPException(400, str(error)) from None

    @router.post("/login")
    def login(body: Credentials, request: Request, response: Response):
        guard(request, response, bucket="login", identifier=body.email.strip().casefold())
        try:
            return session_response(identity.login(body.email, body.password), response)
        except IdentityError:
            raise HTTPException(401, "Invalid credentials") from None

    @router.post("/refresh")
    def refresh(request: Request, response: Response):
        guard(request, response, bucket="refresh")
        try:
            return session_response(identity.refresh(request.cookies.get(cookie, "")), response)
        except IdentityError:
            raise HTTPException(401, "Session expired") from None

    @router.post("/logout", status_code=204)
    def logout(request: Request, response: Response):
        guard(request, response, bucket="logout")
        identity.logout(request.cookies.get(cookie, ""))
        response.delete_cookie(cookie, path=prefix, secure=secure, httponly=True, samesite="lax")

    @router.get("/me")
    def me(request: Request, response: Response):
        no_cache(response)
        return authenticated_user(identity)(request)

    if phone_provider is not None:
        @router.post("/phone/start")
        def phone_start(body: PhoneStart, request: Request, response: Response):
            try:
                phone = normalize_phone(body.phone)
                guard(request, response, bucket="phone-start", identifier=phone)
                return {"challenge": identity.challenge(phone, "phone_signin")}
            except IdentityError as error:
                raise HTTPException(400, str(error)) from None

        @router.post("/phone/verify")
        def phone_verify(body: PhoneVerify, request: Request, response: Response):
            guard(request, response, bucket="phone-verify")
            try:
                return session_response(identity.phone_signin(body.challenge, body.id_token, phone_provider), response)
            except (IdentityError, ValueError):
                raise HTTPException(401, "Invalid phone proof") from None
    return router


def authenticated_user(identity):
    def current(request: Request):
        scheme, _, token = request.headers.get("authorization", "").partition(" ")
        if scheme.lower() != "bearer":
            raise HTTPException(401, "Authentication required")
        try:
            return identity.authenticate(token)
        except IdentityError:
            raise HTTPException(401, "Session expired") from None
    return current


def payment_router(payments, identity, limiter, *, origin, prefix="/billing"):
    router = APIRouter(prefix=prefix, tags=["billing"])
    current = authenticated_user(identity)

    class Checkout(BaseModel):
        product: str = Field(max_length=100)
        request_id: str = Field(min_length=1, max_length=128)

    class Confirmation(BaseModel):
        order_id: str = Field(max_length=100)
        payment_id: str = Field(max_length=100)
        signature: str = Field(max_length=128)

    def guard(request, user):
        if request.headers.get("origin") != origin or request.headers.get("x-foundations-request") != "1":
            raise HTTPException(403, "Untrusted browser request")
        try:
            limiter.admit("checkout", user["id"], limit=20)
        except RateLimited as error:
            raise HTTPException(429, "Too many requests", headers={"Retry-After": str(error.retry_after)}) from None

    @router.post("/checkout")
    def checkout(body: Checkout, request: Request, response: Response, user=Depends(current)):
        from .payments import PaymentError
        response.headers["Cache-Control"] = "no-store"
        guard(request, user)
        try:
            return payments.checkout(user["id"], body.product, body.request_id)
        except PaymentError as error:
            raise HTTPException(400, str(error)) from None

    @router.post("/confirm")
    def confirm(body: Confirmation, request: Request, response: Response, user=Depends(current)):
        from .payments import PaymentError
        response.headers["Cache-Control"] = "no-store"
        guard(request, user)
        try:
            return payments.confirm(user["id"], body.order_id, body.payment_id, body.signature)
        except PaymentError as error:
            raise HTTPException(400, str(error)) from None

    @router.post("/webhook")
    async def webhook(request: Request):
        from .payments import PaymentError
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 262144:
                raise HTTPException(413, "Webhook too large")
        try:
            return payments.receive_webhook(bytes(body), request.headers.get("x-razorpay-signature", ""))
        except (PaymentError, ValueError, KeyError, TypeError):
            raise HTTPException(400, "Invalid webhook") from None
    return router
