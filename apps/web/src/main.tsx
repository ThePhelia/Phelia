import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import axios from "axios";
import {
  login as apiLogin,
  register as apiRegister,
  searchApi,
  listDownloads,
  createDownload,
} from "./api";

const API_BASE = (import.meta as any).env.VITE_API_BASE || "http://localhost:8000/api/v1";
const WS_BASE = (import.meta as any).env.VITE_WS_BASE || "ws://localhost:8000";

function App() {
  const [token, setToken] = useState<string>(localStorage.getItem("token") || "");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [magnet, setMagnet] = useState("");
  const [downloads, setDownloads] = useState<any[]>([]);

  const [query, setQuery] = useState("");
  const [results, setResults] = useState<any[]>([]);
  const [busy, setBusy] = useState(false);
  const [showJackettHelp, setShowJackettHelp] = useState(false);

  const jackettUrl = useMemo(() => {
    if (typeof window === "undefined") return "http://localhost:9117";
    const protocol = window.location?.protocol || "http:";
    const hostname = window.location?.hostname || "localhost";
    return `${protocol}//${hostname}:9117`;
  }, []);

  const ax = useMemo(() => {
    const i = axios.create({ baseURL: API_BASE });
    i.interceptors.request.use((cfg) => {
      if (token) cfg.headers.Authorization = `Bearer ${token}`;
      return cfg;
    });
    return i;
  }, [token]);

  async function doLogin() {
    const data = await apiLogin(email, password);
    const t = data?.access_token || data?.token;
    if (!t) throw new Error("no token");
    localStorage.setItem("token", t);
    setToken(t);
  }

  async function doRegister() {
    const data = await apiRegister(email, password);
    const t = data?.access_token || data?.token;
    if (!t) throw new Error("no token");
    localStorage.setItem("token", t);
    setToken(t);
  }

  async function refreshDownloads() {
    const r = await listDownloads();
    const arr = r?.items || r || [];
    setDownloads(arr);
  }

  useEffect(() => {
    if (token) refreshDownloads();
  }, [token]);

  async function addDownload() {
    const body: any = {};
    if (magnet && magnet.startsWith("magnet:")) {
      body.magnet = magnet;
    } else if (magnet) {
      body.url = magnet;
    } else {
      alert("No magnet or URL specified");
      return;
    }
    await createDownload(body);
    setMagnet("");
    await refreshDownloads();
  }

  async function doSearch() {
    setBusy(true);
    try {
      const data = await searchApi(query);
      const items = data?.items ?? data ?? [];
      setResults(items);
    } finally {
      setBusy(false);
    }
  }

  function openJackett() {
    window.open(jackettUrl, "_blank", "noopener,noreferrer");
  }

  function attachWS(id: string) {
    try {
      const ws = new WebSocket(`${WS_BASE.replace(/\/+$/,"")}/ws/downloads/${encodeURIComponent(id)}`);
      ws.onmessage = (ev) => console.log("WS", id, ev.data);
      ws.onopen = () => console.log("WS open", id);
      ws.onerror = (e) => console.warn("WS error", e);
      ws.onclose = () => console.log("WS close", id);
    } catch (e) {
      console.warn("WS not available", e);
    }
  }

  return (
    <div style={{ padding: 16, fontFamily: "ui-sans-serif, system-ui, -apple-system" }}>
      <h1>Phelia</h1>

      {!token && (
        <div style={{ marginBottom: 16 }}>
          <h2>Auth</h2>
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            <input placeholder="email" value={email} onChange={(e) => setEmail(e.target.value)} />
            <input placeholder="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
            <button onClick={doLogin}>Login</button>
            <button onClick={doRegister}>Register</button>
          </div>
        </div>
      )}

      {token && (
        <>
          <div style={{ marginBottom: 16 }}>
            <h2>Jackett</h2>
            <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
              <button onClick={openJackett}>Open Jackett</button>
              <button onClick={() => setShowJackettHelp((v) => !v)}>
                {showJackettHelp ? "Hide help" : "Help"}
              </button>
            </div>
            {showJackettHelp && (
              <div
                style={{
                  marginTop: 12,
                  padding: 12,
                  border: "1px solid #ddd",
                  borderRadius: 4,
                  maxWidth: 520,
                  background: "#fafafa",
                }}
              >
                <strong>How to add indexers in Jackett</strong>
                <ol style={{ marginTop: 8, marginBottom: 0, paddingLeft: 20 }}>
                  <li>Click "Open Jackett" to launch the Jackett dashboard.</li>
                  <li>Use the search bar to find the indexer you want to add.</li>
                  <li>
                    Press <em>Add Indexer</em>, then fill in any required credentials or API keys requested by the
                    indexer.
                  </li>
                  <li>
                    Hit <em>Test</em> to verify the connection, then <em>Save</em> to persist the indexer in Jackett.
                  </li>
                  <li>
                    Repeat for each tracker you need. Saved indexers automatically become available for Phelia to use
                    during searches.
                  </li>
                </ol>
              </div>
            )}
          </div>

          <div style={{ marginBottom: 16 }}>
            <h2>Add download</h2>
            <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
              <input
                placeholder="magnet or direct URL"
                value={magnet}
                onChange={(e) => setMagnet(e.target.value)}
                style={{ minWidth: 360 }}
              />
              <button onClick={addDownload}>Add</button>
            </div>
          </div>

          <div style={{ marginBottom: 16 }}>
            <h2>Search</h2>
            <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
              <input
                placeholder="search query"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                style={{ minWidth: 360 }}
              />
              <button disabled={busy} onClick={doSearch}>Search</button>
            </div>

            <ul>
              {results.map((r: any) => (
                <li key={r.id || r.guid || r.link}>
                  {r.title || r.name || r.link}
                  {" "}
                  <button onClick={() => {
                    const m = r.magnet || r.url || r.link;
                    if (m) setMagnet(String(m));
                    else alert("Tracker returned no magnet or URL");
                  }}>Use magnet</button>
                </li>
              ))}
            </ul>
          </div>

          <div style={{ marginBottom: 16 }}>
            <h2>Downloads</h2>
            <table cellPadding={6} style={{ borderCollapse: "collapse", minWidth: 480 }}>
              <thead>
                <tr>
                  <th align="left">ID</th>
                  <th align="left">Name</th>
                  <th align="left">Status</th>
                  <th align="left">Actions</th>
                </tr>
              </thead>
              <tbody>
                {downloads.map((d: any) => (
                  <tr key={d.id}>
                    <td>{d.id}</td>
                    <td>{d.name || d.title || d.hash}</td>
                    <td>{d.status || d.state}</td>
                    <td><button onClick={() => attachWS(d.id)}>WS</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Trackers manager (providers + configured trackers) */}
          <Trackers token={token} />
        </>
      )}
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
