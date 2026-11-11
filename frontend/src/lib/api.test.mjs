import test from "node:test";
import assert from "node:assert/strict";

const calls = [];
let fetchImpl;

globalThis.fetch = (...args) => {
  calls.push(args);
  return fetchImpl(...args);
};
globalThis.window = { location: { href: "/" } };

process.env.NEXT_PUBLIC_API_BASE_URL = "http://api.test/api";
const { API_BASE_URL, fetchCsrfToken, resetCsrfToken, fetchWithAuth } =
  await import("./api.ts");

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function setup() {
  calls.length = 0;
  resetCsrfToken();
  // eslint-disable-next-line @next/next/no-location-assign-relative-destination -- test stub, not a real navigation
  window.location.href = "/";
  fetchImpl = async () => jsonResponse({ csrf_token: "token-1" });
}

test("uses the configured API base URL", () => {
  assert.equal(API_BASE_URL, "http://api.test/api");
});

test("fetches and caches the CSRF token", async () => {
  setup();
  assert.equal(await fetchCsrfToken(), "token-1");
  assert.equal(await fetchCsrfToken(), "token-1");
  assert.equal(calls.length, 1);
  assert.equal(calls[0][0], "http://api.test/api/auth/csrf");
  assert.equal(calls[0][1].credentials, "include");
});

test("forceRefresh bypasses the cached token", async () => {
  setup();
  await fetchCsrfToken();
  fetchImpl = async () => jsonResponse({ csrf_token: "token-2" });
  assert.equal(await fetchCsrfToken(true), "token-2");
  assert.equal(calls.length, 2);
});

test("resetCsrfToken makes the next call fetch again", async () => {
  setup();
  await fetchCsrfToken();
  resetCsrfToken();
  await fetchCsrfToken();
  assert.equal(calls.length, 2);
});

test("GET sends cookies and no CSRF header", async () => {
  setup();
  fetchImpl = async () => jsonResponse({ ok: true });
  const response = await fetchWithAuth("/conversations/");
  assert.equal(response.status, 200);
  const [url, options] = calls[0];
  assert.equal(url, "http://api.test/api/conversations/");
  assert.equal(options.method, undefined);
  assert.equal(options.credentials, "include");
  assert.equal(options.headers["X-CSRF-Token"], undefined);
  assert.equal(options.headers["Content-Type"], "application/json");
});

test("POST fetches a token first and sends it as a header", async () => {
  setup();
  fetchImpl = async (url) =>
    url.endsWith("/auth/csrf") ? jsonResponse({ csrf_token: "token-1" }) : jsonResponse({ ok: true });
  await fetchWithAuth("/chat/", { method: "post", body: "{}" });
  assert.equal(calls.length, 2);
  const [url, options] = calls[1];
  assert.equal(url, "http://api.test/api/chat/");
  assert.equal(options.headers["X-CSRF-Token"], "token-1");
});

test("a 403 clears the cached token so the next POST re-fetches it", async () => {
  setup();
  fetchImpl = async (url) =>
    url.endsWith("/auth/csrf")
      ? jsonResponse({ csrf_token: "token-1" })
      : jsonResponse({ detail: "CSRF" }, 403);
  const response = await fetchWithAuth("/keys/", { method: "DELETE" });
  assert.equal(response.status, 403);
  fetchImpl = async (url) =>
    url.endsWith("/auth/csrf") ? jsonResponse({ csrf_token: "token-2" }) : jsonResponse({ ok: true });
  await fetchWithAuth("/keys/", { method: "DELETE" });
  assert.equal(calls.length, 4);
  assert.equal(calls[3][1].headers["X-CSRF-Token"], "token-2");
});

test("a 401 on a protected route redirects to login", async () => {
  setup();
  fetchImpl = async () => jsonResponse({ detail: "Unauthorized" }, 401);
  await fetchWithAuth("/conversations/");
  assert.equal(window.location.href, "/login");
});

test("a 401 from login or register does not redirect", async () => {
  setup();
  fetchImpl = async () => jsonResponse({ detail: "Unauthorized" }, 401);
  await fetchWithAuth("/auth/token", { method: "POST" });
  assert.equal(window.location.href, "/");
  await fetchWithAuth("/auth/register", { method: "POST" });
  assert.equal(window.location.href, "/");
});
