import React, { useEffect, useState } from "react";
import { listTrackers, createTracker, updateTracker, deleteTracker, testTracker, fetchJackettDefault } from "./api";

export function Trackers({ token }: { token: string }) {
  const [items, setItems] = useState<any[]>([]);
  const [name, setName] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [info, setInfo] = useState("");

  async function load() {
    setLoading(true);
    try {
      const data = await listTrackers(token);
      setItems(data || []);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { if (token) load(); }, [token]);

  async function add() {
    try {
      await createTracker(token, { name, base_url: baseUrl, api_key: apiKey, username, password, enabled: true });
      setName(""); setBaseUrl(""); setApiKey(""); setUsername(""); setPassword("");
      await load();
    } catch (e: any) {
      alert(e.message || String(e));
    }
  }

  async function toggle(id: number, enabled: boolean) {
    await updateTracker(token, id, { enabled: !enabled });
    await load();
  }

  async function remove(id: number) {
    await deleteTracker(token, id);
    await load();
  }

  async function test(id: number) {
    try {
      const r = await testTracker(token, id);
      if (!r.ok && r.status === 100) {
        alert("Invalid API key");
      } else {
        alert(`ok=${r.ok} status=${r.status}`);
      }
    } catch (e: any) {
      alert(e.message || String(e));
    }
  }

  async function fetchFromJackett() {
    try {
      const data = await fetchJackettDefault(token);
      if (data.base_url) setBaseUrl(data.base_url);
      if (data.api_key) {
        setApiKey(data.api_key);
        setInfo("API key fetched from Jackett");
        setTimeout(() => setInfo(""), 3000);
      }
    } catch (e: any) {
      alert(e.message || String(e));
    }
  }

  function onBaseUrlChange(e: React.ChangeEvent<HTMLInputElement>) {
    const v = e.target.value;
    try {
      const u = new URL(v);
      let key = u.searchParams.get("apikey");
      if (key) {
        u.searchParams.delete("apikey");
      } else {
        const m = u.pathname.match(/\/(?:apikey\/)?([a-f0-9]{32})(?=\/|$)/i);
        if (m) {
          key = m[1];
          u.pathname = u.pathname.replace(m[0], "/").replace(/\/+/g, "/");
        }
      }
      if (key) {
        setApiKey(key);
        setInfo("API key auto-filled");
        setTimeout(() => setInfo(""), 3000);
      }
      const search = u.searchParams.toString();
      const normalized = u.origin + u.pathname + (search ? `?${search}` : "") + u.hash;
      setBaseUrl(normalized);
      return;
    } catch {
      // ignore parse errors and keep the raw value
    }
    setBaseUrl(v);
  }

  return (
    <div style={{ padding: 12 }}>
      <h3>Trackers</h3>
      <div style={{ marginBottom: 8 }}>
        <input placeholder="name" value={name} onChange={e=>setName(e.target.value)} />
        <input placeholder="base_url" value={baseUrl} onChange={onBaseUrlChange} style={{ width: 420, marginLeft: 6 }} />
        <input placeholder="api_key" value={apiKey} onChange={e=>setApiKey(e.target.value)} style={{ marginLeft: 6 }} />
        <input placeholder="username" value={username} onChange={e=>setUsername(e.target.value)} style={{ marginLeft: 6 }} />
        <input placeholder="password" type="password" value={password} onChange={e=>setPassword(e.target.value)} style={{ marginLeft: 6 }} />
        <button onClick={fetchFromJackett} style={{ marginLeft: 6 }}>Jackett</button>
        <button onClick={add} style={{ marginLeft: 6 }}>Add</button>
        {info && <span style={{ marginLeft: 6, color: '#555' }}>{info}</span>}
      </div>
      <table cellPadding={6} style={{ borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th>ID</th><th>Name</th><th>URL</th><th>Creds</th><th>Enabled</th><th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {items.map(it=>(
            <tr key={it.id}>
              <td>{it.id}</td>
              <td>{it.name}</td>
              <td style={{ maxWidth: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{it.base_url}</td>
              <td>{(it.username || it.api_key) ? "Yes" : "No"}</td>
              <td>{String(it.enabled)}</td>
              <td>
                <button onClick={()=>toggle(it.id, it.enabled)}>Toggle</button>{" "}
                <button onClick={()=>test(it.id)}>Test</button>{" "}
                <button onClick={()=>remove(it.id)}>Delete</button>
              </td>
            </tr>
          ))}
          {loading && <tr><td colSpan={6}>Loading...</td></tr>}
        </tbody>
      </table>
    </div>
  );
}

