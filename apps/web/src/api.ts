const BASE = import.meta.env.VITE_API_BASE as string;

export async function login(email: string, password: string) {
  const r = await fetch(`${BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!r.ok) throw new Error(String(r.status));
  return r.json();
}

export async function listTrackers(token: string) {
  const r = await fetch(`${BASE}/trackers`, { headers: { Authorization: `Bearer ${token}` }});
  if (!r.ok) throw new Error(String(r.status));
  return r.json();
}

export async function createTracker(token: string, body: {name:string;base_url:string;api_key?:string;enabled?:boolean}) {
  const r = await fetch(`${BASE}/trackers`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ type: "torznab", enabled: true, ...body }),
  });
  if (!r.ok) throw new Error(String(r.status));
  return r.json();
}

export async function updateTracker(token: string, id: number, body: Partial<{name:string;base_url:string;api_key:string;enabled:boolean}>) {
  const r = await fetch(`${BASE}/trackers/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(String(r.status));
  return r.json();
}

export async function deleteTracker(token: string, id: number) {
  const r = await fetch(`${BASE}/trackers/${id}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok && r.status !== 204) throw new Error(String(r.status));
}

export async function testTracker(token: string, id: number) {
  const r = await fetch(`${BASE}/trackers/${id}/test`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) throw new Error(String(r.status));
  return r.json();
}

