export const API_BASE_URL = "http://localhost:8000/api";

export async function fetchWithAuth(url: string, options: RequestInit = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...options.headers,
  };
  const response = await fetch(`${API_BASE_URL}${url}`, { 
    ...options, 
    headers,
    credentials: "include" // Important to send cookies
  });
  
  if (response.status === 401 && url !== "/auth/login") {
    // If not authenticated, redirect to login
    window.location.href = "/login";
  }
  return response;
}
