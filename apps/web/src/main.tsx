import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import axios from "axios";

const API_BASE = (import.meta as any).env.VITE_API_BASE || "http://localhost:8000/api/v1";
const WS_BASE = (import.meta as any).env.VITE_WS_BASE || "ws://localhost:8000";

function App() {
  const [magnet, setMagnet] = useState("");
  const [items, setItems] = useState<any[]>([]);
  const [token, setToken] = useState(localStorage.getItem("token") || "");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<any[]>([]);
  const ax = useMemo(() => {
    const i = axios.create({ baseURL: API_BASE });
    i.interceptors.request.use((cfg) => {
      if (token) cfg.headers.Authorization = `Bearer ${token}`;
      return cfg;
    });
    return i;
  }, [token]);

  useEffect(() => {
    if (token) list();
  }, [token]);

  async function login() {
    const r = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!r.ok) throw new Error(String(r.status));
    const data = await r.json();
    const t = data.accessToken || data.access_token || data.token;
    if (!t) throw new Error("no token");
    localStorage.setItem("token", t);
    setToken(t);
  }

  async function list() {
    const r = await ax.get("/downloads");
    const arr = r.data.items || r.data || [];
    setItems(arr);
    return arr;
  }

  async function add() {
    try {
      const r = await ax.post("/downloads", { magnet, savePath: "/downloads" });
      const id = r.data?.id;
      setMagnet("");
      const arr = await list();
      if (!arr.find((it: any) => it.id === id)) {
        alert("Download was not created");
      }
    } catch (e) {
      alert("Failed to add download: " + e);
    }
  }

  async function pause(id: number) {
    await ax.post(`/downloads/${id}/pause`);
    await list();
  }

  async function resume(id: number) {
    await ax.post(`/downloads/${id}/resume`);
    await list();
  }

  async function del(id: number, withFiles: boolean) {
    await ax.delete(`/downloads/${id}`, { params: { withFiles } });
    await list();
  }

  function attachWS(id: number) {
    const ws = new WebSocket(`${WS_BASE}/ws/downloads/${id}`);
    ws.onmessage = (e) => {
      try {
        const m = JSON.parse(e.data);
        if (!m || !m.id) return;
        setItems((prev) =>
          prev.map((x) => (x.id === m.id ? { ...x, ...m } : x))
        );
      } catch {}
    };
  }

  async function doSearch() {
    try {
      const r = await ax.get("/search", { params: { query } });
      setResults(r.data.items || []);
    } catch (e: any) {
      const msg =
        e?.response?.data?.detail || e?.message || String(e);
      alert("Search failed: " + msg);
      setResults([]);
    }
  }

  return (
    <div style={{ padding: 16, fontFamily: "sans-serif" }}>
      <h3>Auth</h3>
      {!token ? (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            login().catch((e) => alert("Login failed: " + e));
          }}
        >
          <input
            type="email"
            name="email"
            placeholder="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />{" "}
          <input
            type="password"
            name="password"
            placeholder="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />{" "}
          <button type="submit">Login</button>
        </form>
      ) : (
        <div>
          <code>{token.slice(0, 24)}...</code>{" "}
          <button
            onClick={() => {
              localStorage.removeItem("token");
              setToken("");
            }}
          >
            Logout
          </button>
        </div>
      )}

      <h3>Search</h3>
      <input
        placeholder="query"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />{" "}
      <button onClick={doSearch}>Search</button>
      <ul>
        {results.map((r, i) => (
          <li key={i}>
            {r.title}{" "}
            <button
              onClick={() => {
                const m = r.magnet || r.link;
                if (m) setMagnet(m);
              }}
            >
              Use magnet
            </button>
          </li>
        ))}
      </ul>

      <h3>Add</h3>
      <input
        placeholder="magnet"
        value={magnet}
        onChange={(e) => setMagnet(e.target.value)}
        style={{ width: 600 }}
      />{" "}
      <button onClick={add}>Add</button>

      <h3>Downloads</h3>
      <button onClick={list}>Refresh</button>
      <table cellPadding={6} style={{ borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th>ID</th>
            <th>Name</th>
            <th>Progress</th>
            <th>State</th>
            <th>DL</th>
            <th>UP</th>
            <th>ETA</th>
            <th>Actions</th>
            <th>WS</th>
          </tr>
        </thead>
        <tbody>
          {items.map((it: any) => (
            <tr key={it.id}>
              <td>{it.id}</td>
              <td>{it.name || it.title}</td>
              <td>{Math.round((it.progress || 0) * 100)}%</td>
              <td>{it.status}</td>
              <td>{it.dlspeed}</td>
              <td>{it.upspeed}</td>
              <td>{it.eta}</td>
              <td>
                <button onClick={() => pause(it.id)}>Pause</button>{" "}
                <button onClick={() => resume(it.id)}>Resume</button>{" "}
                <button onClick={() => del(it.id, false)}>Remove</button>{" "}
                <button onClick={() => del(it.id, true)}>Remove+Files</button>
              </td>
              <td>
                <button onClick={() => attachWS(it.id)}>WS</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<App />);

