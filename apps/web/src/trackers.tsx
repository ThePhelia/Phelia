import React, { useEffect, useState } from "react";
import {
  listProviders,
  connectProvider,
  listTrackers,
  toggleTracker,
  testTracker,
  deleteTracker,
} from "./api";

export function Trackers({ token }: { token: string }) {
  const [providers, setProviders] = useState<any[]>([]);
  const [trackers, setTrackers] = useState<any[]>([]);
  const [loadingProviders, setLoadingProviders] = useState(false);
  const [loadingTrackers, setLoadingTrackers] = useState(false);
  const [credProvider, setCredProvider] = useState<any | null>(null);
  const [credValues, setCredValues] = useState<Record<string, string>>({});

  async function loadProviders() {
    setLoadingProviders(true);
    try {
      const data = await listProviders(token);
      setProviders(data || []);
    } finally {
      setLoadingProviders(false);
    }
  }

  async function loadTrackers() {
    setLoadingTrackers(true);
    try {
      const data = await listTrackers(token);
      setTrackers(data || []);
    } finally {
      setLoadingTrackers(false);
    }
  }

  useEffect(() => {
    if (token) {
      loadProviders();
      loadTrackers();
    }
  }, [token]);

  function startConnect(p: any) {
    if (p.needs && p.needs.length > 0) {
      const vals: Record<string, string> = {};
      for (const f of p.needs) vals[f] = "";
      setCredProvider(p);
      setCredValues(vals);
    } else {
      handleConnect(p.slug, undefined);
    }
  }

  async function handleConnect(slug: string, body: any) {
    try {
      await connectProvider(token, slug, body);
      await loadProviders();
      await loadTrackers();
    } catch (e: any) {
      alert(e.message || String(e));
    }
  }

  function submitCreds() {
    if (!credProvider) return;
    handleConnect(credProvider.slug, credValues);
    setCredProvider(null);
    setCredValues({});
  }

  async function onToggle(id: number) {
    await toggleTracker(token, id);
    await loadTrackers();
  }

  async function onDelete(id: number) {
    await deleteTracker(token, id);
    await loadTrackers();
  }

  async function onTest(id: number) {
    try {
      const r = await testTracker(token, id);
      alert(`ok=${r.ok} latency=${r.latency_ms ?? "?"}`);
    } catch (e: any) {
      alert(e.message || String(e));
    }
  }

  return (
    <div style={{ padding: 12 }}>
      <h3>Provider Catalog</h3>
      <ul>
        {providers.map((p) => (
          <li key={p.slug}>
            {p.name} ({p.type}) {p.configured ? "✓" : ""}{" "}
            <button onClick={() => startConnect(p)}>Connect</button>
          </li>
        ))}
        {loadingProviders && <li>Loading...</li>}
      </ul>

      <h3>My Trackers</h3>
      <table cellPadding={6} style={{ borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th>ID</th>
            <th>Name</th>
            <th>URL</th>
            <th>Enabled</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {trackers.map((it) => (
            <tr key={it.id}>
              <td>{it.id}</td>
              <td>{it.name}</td>
              <td style={{ maxWidth: 400, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {it.torznab_url}
              </td>
              <td>{String(it.enabled)}</td>
              <td>
                <button onClick={() => onToggle(it.id)}>Toggle</button>{" "}
                <button onClick={() => onTest(it.id)}>Test</button>{" "}
                <button onClick={() => onDelete(it.id)}>Delete</button>
              </td>
            </tr>
          ))}
          {loadingTrackers && (
            <tr>
              <td colSpan={5}>Loading...</td>
            </tr>
          )}
        </tbody>
      </table>
      {credProvider && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0,0,0,0.3)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <div style={{ background: "#fff", padding: 20, minWidth: 300 }}>
            <h4>Connect {credProvider.name}</h4>
            {credProvider.needs.map((f: string) => (
              <div key={f} style={{ marginBottom: 8 }}>
                <label>{f}</label>
                <input
                  type={f.toLowerCase().includes("password") ? "password" : "text"}
                  value={credValues[f] || ""}
                  onChange={(e) =>
                    setCredValues({ ...credValues, [f]: e.target.value })
                  }
                />
              </div>
            ))}
            <button onClick={submitCreds}>Connect</button>{" "}
            <button onClick={() => setCredProvider(null)}>Cancel</button>
          </div>
        </div>
      )}
    </div>
  );
}
