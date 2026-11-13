import { request } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

// The API validates Origin on every state-changing request (CSRF), so the
// setup calls it exactly as the browser would, from the app origin.
const APP_ORIGIN = process.env.E2E_APP_ORIGIN || "http://app.lvh.me:3003";
const API_URL = process.env.E2E_API_URL || "http://api.lvh.me:8003/api/";
const EMAIL = process.env.E2E_EMAIL || "e2e-smoke@alloyd-e2e.dev";
const PASSWORD = process.env.E2E_PASSWORD || "e2e-smoke-password-123";
const STATE_PATH = path.join(__dirname, ".auth", "user.json");

async function globalSetup() {
  fs.mkdirSync(path.dirname(STATE_PATH), { recursive: true });

  const api = await request.newContext({ baseURL: `${API_URL.replace(/\/+$/, "")}/` });
  const originHeaders = { Origin: APP_ORIGIN };

  const csrfResponse = await api.get("auth/csrf", { headers: originHeaders });
  if (!csrfResponse.ok()) {
    throw new Error(`CSRF handout failed: ${csrfResponse.status()}`);
  }
  const csrfToken = (await csrfResponse.json()).csrf_token as string;
  const headers = { ...originHeaders, "X-CSRF-Token": csrfToken };

  // Existing local accounts must not consume the registration quota on every run.
  const login = await api.post("auth/token", {
    headers,
    form: { username: EMAIL, password: PASSWORD },
  });
  if (login.status() === 401) {
    const register = await api.post("auth/register", {
      headers,
      data: { email: EMAIL, password: PASSWORD },
    });
    if (!register.ok()) {
      throw new Error(`Registration failed: ${register.status()}`);
    }
  } else if (!login.ok()) {
    throw new Error(`Login failed: ${login.status()}`);
  }

  const keyResponse = await api.post("keys/", {
    headers,
    data: { provider_name: "mock", key: "e2e-mock-key" },
  });
  if (!keyResponse.ok()) {
    const body = await keyResponse.text();
    if (body.includes("Invalid provider")) {
      throw new Error(
        "The mock provider is not registered. Start the backend with ENABLE_MOCK_PROVIDER=true."
      );
    }
    throw new Error(`Storing the mock key failed: ${keyResponse.status()}`);
  }

  await api.storageState({ path: STATE_PATH });
  await api.dispose();
}

export default globalSetup;
