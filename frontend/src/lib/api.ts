export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api";

let csrfToken: string | null = null;

export async function fetchWithAuth(url: string, options: RequestInit = {}) {
  const method = options.method?.toUpperCase() || "GET";
  
  if (["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
    // Exclude login and register from requiring CSRF since they establish the session
    if (!csrfToken && url !== "/auth/token" && url !== "/auth/register") {
      try {
        const res = await fetch(`${API_BASE_URL}/auth/csrf`, { credentials: "include" });
        if (res.ok) {
          const data = await res.json();
          csrfToken = data.csrf_token;
        }
      } catch (e) {
        console.error("Failed to fetch CSRF token", e);
      }
    }
  }

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  
  if (csrfToken && ["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
    headers["X-CSRF-Token"] = csrfToken;
  }

  const response = await fetch(`${API_BASE_URL}${url}`, { 
    ...options, 
    headers,
    credentials: "include" // Important to send cookies
  });
  
  if (response.status === 403) {
    // If CSRF token is invalid, clear it so it can be re-fetched next time
    csrfToken = null;
  }

  if (response.status === 401 && url !== "/auth/token" && url !== "/auth/register") {
    // If not authenticated, redirect to login
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination
    window.location.href = "/login";
  }
  return response;
}
