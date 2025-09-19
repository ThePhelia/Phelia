import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import axios from "axios";
import {
  login as apiLogin,
  register as apiRegister,
  searchApi,
  listDownloads,
  createDownload,
  pauseDownload,
  resumeDownload,
  deleteDownload,
} from "./api";

const API_BASE = (import.meta as any).env.VITE_API_BASE || "http://localhost:8000/api/v1";

type DownloadActionKey = "pause" | "resume" | "delete";

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
  const [actionBusy, setActionBusy] = useState<
    Record<string, Partial<Record<DownloadActionKey, boolean>>>
  >({});
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; name?: string } | null>(null);
  const [deleteWithFiles, setDeleteWithFiles] = useState(false);

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

  function updateActionBusy(id: string, key: DownloadActionKey, value: boolean) {
    setActionBusy((prev) => {
      const prevEntry = prev[id] || {};
      if (value) {
        return { ...prev, [id]: { ...prevEntry, [key]: true } };
      }
      const nextEntry = { ...prevEntry };
      delete nextEntry[key];
      if (Object.keys(nextEntry).length === 0) {
        const { [id]: _removed, ...rest } = prev;
        return rest;
      }
      return { ...prev, [id]: nextEntry };
    });
  }

  async function handleAction(
    id: string,
    key: DownloadActionKey,
    action: () => Promise<any>
  ) {
    updateActionBusy(id, key, true);
    try {
      await action();
      await refreshDownloads();
    } catch (error: any) {
      console.error(error);
      const message =
        error?.response?.data?.detail || error?.message || "Unknown error";
      window.alert(`Failed to ${key} download: ${message}`);
    } finally {
      updateActionBusy(id, key, false);
    }
  }

  function requestPause(id: string) {
    void handleAction(id, "pause", () => pauseDownload(id));
  }

  function requestResume(id: string) {
    void handleAction(id, "resume", () => resumeDownload(id));
  }

  function openDeleteModal(id: string, name?: string) {
    setDeleteTarget({ id, name });
    setDeleteWithFiles(false);
  }

  function closeDeleteModal() {
    setDeleteTarget(null);
    setDeleteWithFiles(false);
  }

  async function confirmDelete() {
    if (!deleteTarget) return;
    const id = deleteTarget.id;
    try {
      await handleAction(id, "delete", () =>
        deleteDownload(id, { withFiles: deleteWithFiles })
      );
    } finally {
      closeDeleteModal();
    }
  }

  function openJackett() {
    window.open(jackettUrl, "_blank", "noopener,noreferrer");
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
                  <li>Press <em> Add Indexers</em> button then use the search bar to find the indexer you want to add.</li>
                  <li>
                    Press <em>"+"</em> for public trackers to add them, or press settings button and fill in any required 
                      credentials for private an semi-private indexers.
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
                    <td>
                      <div style={{ display: "flex", gap: 6 }}>
                        <button
                          disabled={!!actionBusy[d.id]?.pause}
                          onClick={() => requestPause(String(d.id))}
                        >
                          Pause
                        </button>
                        <button
                          disabled={!!actionBusy[d.id]?.resume}
                          onClick={() => requestResume(String(d.id))}
                        >
                          Stop
                        </button>
                        <button
                          disabled={!!actionBusy[d.id]?.delete}
                          onClick={() =>
                            openDeleteModal(String(d.id), d.name || d.title || d.hash)
                          }
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {deleteTarget && (
            <div
              style={{
                position: "fixed",
                inset: 0,
                background: "rgba(0, 0, 0, 0.4)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                zIndex: 999,
              }}
            >
              <div
                style={{
                  background: "#fff",
                  padding: 20,
                  borderRadius: 8,
                  boxShadow: "0 10px 24px rgba(0,0,0,0.2)",
                  minWidth: 320,
                  maxWidth: "90vw",
                }}
              >
                <h3 style={{ marginTop: 0 }}>Delete download</h3>
                <p style={{ marginTop: 8 }}>
                  Are you sure you want to delete
                  {" "}
                  <strong>{deleteTarget.name || deleteTarget.id}</strong>?
                </p>
                <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <input
                    type="checkbox"
                    checked={deleteWithFiles}
                    onChange={(e) => setDeleteWithFiles(e.target.checked)}
                  />
                  Also delete downloaded files
                </label>
                <div style={{ marginTop: 16, display: "flex", gap: 8, justifyContent: "flex-end" }}>
                  <button onClick={closeDeleteModal} disabled={!!actionBusy[deleteTarget.id]?.delete}>
                    Cancel
                  </button>
                  <button
                    onClick={confirmDelete}
                    disabled={!!actionBusy[deleteTarget.id]?.delete}
                    style={{ background: "#d32f2f", color: "white", border: "none", padding: "6px 12px" }}
                  >
                    Confirm
                  </button>
                </div>
              </div>
            </div>
          )}

        </>
      )}
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
