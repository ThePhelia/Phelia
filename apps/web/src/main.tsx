import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import axios from "axios";
import {
  login as apiLogin,
  register as apiRegister,
  searchMetadata,
  lookupMetadata,
  listDownloads,
  createDownload,
  pauseDownload,
  resumeDownload,
  deleteDownload,
  type EnrichedCard,
} from "./api";
import OpenJackettCard from "./components/OpenJackettCard";
import ResultCard from "./components/ResultCard";

const API_BASE = (import.meta as any).env.VITE_API_BASE || "http://localhost:8000/api/v1";

type DownloadActionKey = "pause" | "resume" | "delete";

function normalizeErrorDetail(detail: unknown): string | null {
  if (!detail) return null;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => {
        if (!item) return null;
        if (typeof item === "string") return item;
        if (typeof item === "object") {
          const msg = (item as any)?.msg || (item as any)?.message || (item as any)?.detail;
          const loc = (item as any)?.loc;
          const locText = Array.isArray(loc) ? loc.join(".") : loc;
          if (msg && locText) return `${locText}: ${msg}`;
          if (msg) return msg;
          try {
            return JSON.stringify(item);
          } catch {
            return String(item);
          }
        }
        return String(item);
      })
      .filter((part): part is string => Boolean(part));
    if (parts.length) return parts.join("; ");
    return null;
  }
  if (typeof detail === "object") {
    const nested =
      (detail as any)?.message || (detail as any)?.msg || normalizeErrorDetail((detail as any)?.detail);
    if (nested) return nested;
    try {
      return JSON.stringify(detail);
    } catch {
      return String(detail);
    }
  }
  return String(detail);
}

function App() {
  const [token, setToken] = useState<string>(localStorage.getItem("token") || "");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [magnet, setMagnet] = useState("");
  const [downloads, setDownloads] = useState<any[]>([]);

  const [query, setQuery] = useState("");
  const [results, setResults] = useState<EnrichedCard[]>([]);
  const [busy, setBusy] = useState(false);
  const [jackettNotice, setJackettNotice] = useState<{ url?: string; message?: string } | null>(
    null,
  );
  const [resultBusyIndex, setResultBusyIndex] = useState<number | null>(null);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [actionBusy, setActionBusy] = useState<
    Record<string, Partial<Record<DownloadActionKey, boolean>>>
  >({});
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; name?: string } | null>(null);
  const [deleteWithFiles, setDeleteWithFiles] = useState(false);

  const fallbackJackettUrl = useMemo(() => {
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
    setSearchError(null);
    try {
      const data = await searchMetadata(query);
      setResults(data?.items ?? []);
      setJackettNotice({ url: data?.jackett_ui_url, message: data?.message });
      if (data?.error) {
        setSearchError(data.error);
      }
    } catch (error: any) {
      console.error(error);
      setResults([]);
      const detailMessage = normalizeErrorDetail(error?.response?.data?.detail);
      const fallback = typeof error?.message === "string" ? error.message : null;
      setSearchError(detailMessage || fallback || "Search failed");
    } finally {
      setBusy(false);
    }
  }

  async function reclassifyResult(index: number, hint: "music" | "movie" | "tv" | "other") {
    const card = results[index];
    if (!card) return;
    setResultBusyIndex(index);
    try {
      const titleForLookup = card.details?.jackett?.title || card.title;
      const updated = await lookupMetadata({ title: titleForLookup, hint });
      const merged: EnrichedCard = {
        ...updated,
        details: {
          ...updated.details,
          jackett: card.details?.jackett,
        },
        reasons: [...updated.reasons, `manual_hint:${hint}`],
      };
      setResults((prev) => {
        const next = [...prev];
        next[index] = merged;
        return next;
      });
    } catch (error: any) {
      console.error(error);
      window.alert(
        error?.response?.data?.detail || error?.message || "Failed to refresh metadata",
      );
    } finally {
      setResultBusyIndex(null);
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
    const target = jackettNotice?.url || fallbackJackettUrl;
    window.open(target, "_blank", "noopener,noreferrer");
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
              <button onClick={openJackett}>Open Jackett</button>
            </div>

            {jackettNotice?.url && (
              <OpenJackettCard
                jackettUrl={jackettNotice.url || fallbackJackettUrl}
                message={jackettNotice.message}
              />
            )}
            {searchError && (
              <div style={{ color: "#d32f2f", marginTop: 8 }}>{searchError}</div>
            )}

            <div style={{ marginTop: 16 }}>
              {results.map((card, index) => (
                <ResultCard
                  key={`${card.title}-${index}`}
                  card={card}
                  busy={resultBusyIndex === index}
                  onReclassify={(hint) => reclassifyResult(index, hint)}
                  onUseMagnet={(magnet) => magnet && setMagnet(String(magnet))}
                />
              ))}
              {results.length === 0 && !busy && <p style={{ color: "#57606a" }}>No results yet.</p>}
            </div>
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
