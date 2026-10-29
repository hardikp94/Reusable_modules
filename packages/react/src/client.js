export class ApiError extends Error {
  constructor(status, detail, retryAfter) {
    super(typeof detail === "string" ? detail : "Request failed");
    this.status = status; this.detail = detail; this.retryAfter = retryAfter;
  }
}

export function createClient({baseUrl = "", authPath = "/auth", fetchImpl = globalThis.fetch} = {}) {
  let access = null, refreshPromise = null, generation = 0;
  async function send(path, {method = "GET", body, signal, authenticated = true} = {}) {
    if (!path.startsWith("/") || path.startsWith("//") || /[\\\u0000-\u0020\u007f]/.test(path)) throw new Error("Use a local API path");
    const response = await fetchImpl(baseUrl.replace(/\/$/, "") + path, {
      method, credentials: "include", signal, cache: "no-store",
      headers: {"Content-Type": "application/json", "X-Foundations-Request": "1", ...(authenticated && access ? {Authorization: `Bearer ${access}`} : {})},
      ...(body === undefined ? {} : {body: JSON.stringify(body)}),
    });
    const data = response.status === 204 ? null : await response.json();
    if (!response.ok) throw new ApiError(response.status, data?.detail, response.headers.get("Retry-After"));
    return data;
  }
  async function refresh() {
    if (!refreshPromise) {
      const current = generation;
      refreshPromise = send(authPath + "/refresh", {method: "POST", authenticated: false})
        .then(result => { if (current === generation) access = result.access_token; return result; })
        .catch(error => { if (error.status === 401 && current === generation) access = null; throw error; })
        .finally(() => { refreshPromise = null; });
    }
    return refreshPromise;
  }
  return {
    async request(path, options = {}) {
      const current = generation;
      try { return await send(path, options); }
      catch (error) {
        if (error.status !== 401 || options.authenticated === false || current !== generation) throw error;
        await refresh();
        if (current !== generation) throw new Error("Identity changed during request");
        return send(path, options); // One retry only; host mutations still need idempotency keys.
      }
    },
    refresh,
    async login(email, password) {
      const current = ++generation;
      const result = await send(authPath + "/login", {method: "POST", body: {email, password}, authenticated: false});
      if (current === generation) access = result.access_token;
      return result.user;
    },
    register: (email, password) => send(authPath + "/register", {method: "POST", body: {email, password}, authenticated: false}),
    phoneStart: phone => send(authPath + "/phone/start", {method: "POST", body: {phone}, authenticated: false}),
    async phoneVerify(challenge, idToken) {
      const current = ++generation;
      const result = await send(authPath + "/phone/verify", {method: "POST", body: {challenge, id_token: idToken}, authenticated: false});
      if (current === generation) access = result.access_token;
      return result.user;
    },
    async logout() {
      ++generation; access = null;
      await send(authPath + "/logout", {method: "POST", authenticated: false});
    },
  };
}
