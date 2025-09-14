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

export async function register(email: string, password: string) {
  const r = await fetch(`${BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!r.ok) throw new Error(String(r.status));
  return r.json() as Promise<{ accessToken: string; tokenType: string }>;
}

// ---------------------------------------------------------------------------
// Trackers API
// ---------------------------------------------------------------------------

export async function listProviders(token: string) {
  const r = await fetch(`${BASE}/trackers/providers`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) throw new Error(String(r.status));
  return r.json();
}

export async function connectProvider(
  token: string,
  slug: string,
  body: Record<string, any> | undefined = undefined,
) {
  const r = await fetch(`${BASE}/trackers/providers/${slug}/connect`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await r.text();
  if (!r.ok) {
    try {
      const data = JSON.parse(text);
      throw new Error(data.error || text || String(r.status));
    } catch {
      throw new Error(text || String(r.status));
    }
  }
  return JSON.parse(text);
}

export async function listTrackers(token: string) {
  const r = await fetch(`${BASE}/trackers`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) throw new Error(String(r.status));
  return r.json();
}

export async function toggleTracker(token: string, id: number) {
  const r = await fetch(`${BASE}/trackers/${id}/toggle`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) throw new Error(String(r.status));
  return r.json();
}

export async function testTracker(token: string, id: number) {
  const r = await fetch(`${BASE}/trackers/${id}/test`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) throw new Error(String(r.status));
  return r.json();
}

export async function deleteTracker(token: string, id: number) {
  const r = await fetch(`${BASE}/trackers/${id}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok && r.status !== 200 && r.status !== 204)
    throw new Error(String(r.status));
}

// ---------------------------------------------------------------------------
// Misc existing API helpers
// ---------------------------------------------------------------------------

export async function searchApi(q: string) {
  const r = await fetch(`${BASE}/search?query=${encodeURIComponent(q)}`);
  if (!r.ok) throw new Error(`search ${r.status}`);
  return r.json() as Promise<{
    total: number;
    items: Array<{ title: string; magnet?: string }>;
  }>;
}

export async function createDownload(
  token: string,
  magnet: string,
  savePath = "/downloads",
) {
  try {
    const r = await fetch(`${BASE}/downloads`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ magnet, savePath }),
    });
    if (!r.ok) {
      const body = await r.text().catch(() => "");
      throw new Error(`createDownload ${r.status} ${body}`.trim());
    }
    return r.json() as Promise<{ id: number }>;
  } catch (e) {
    throw new Error(String(e));
  }
}
