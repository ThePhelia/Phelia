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

export async function createTracker(
  token: string,
  body: {
    name:string;
    base_url:string;
    api_key?:string;
    enabled?:boolean;
    username?:string;
    password?:string;
  }
) {
  const r = await fetch(`${BASE}/trackers`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ type: "torznab", enabled: true, ...body }),
  });
  const text = await r.text();
  if (!r.ok) {
    try {
      const data = JSON.parse(text);
      throw new Error(data.detail || text || String(r.status));
    } catch {
      throw new Error(text || String(r.status));
    }
  }
  return JSON.parse(text);
}

<<<<<<< ours
export async function updateTracker(token: string, id: number, body: Partial<{name:string;base_url:string;api_key:string;username:string;password:string;enabled:boolean}>) {
=======
export async function updateTracker(
  token: string,
  id: number,
  body: Partial<{
    name:string;
    base_url:string;
    api_key:string;
    enabled:boolean;
    username:string;
    password:string;
  }>
) {
>>>>>>> theirs
  const r = await fetch(`${BASE}/trackers/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(String(r.status));
  return r.json();
}


export async function searchApi(q: string) {
  const r = await fetch(`${BASE}/search?query=${encodeURIComponent(q)}`);
  if (!r.ok) throw new Error(`search ${r.status}`);
  return r.json() as Promise<{ total: number; items: Array<{ title: string; magnet?: string }> }>;
}



export async function createDownload(token: string, magnet: string, savePath = "/downloads") {
  try {
    const r = await fetch(`${BASE}/downloads`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
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
  const text = await r.text();
  if (!r.ok) {
    try {
      const data = JSON.parse(text);
      throw new Error(data.detail || text || String(r.status));
    } catch {
      throw new Error(text || String(r.status));
    }
  }
  return JSON.parse(text);
}

