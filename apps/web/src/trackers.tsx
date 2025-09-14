import React, { useEffect, useState } from "react";
import {
  listTrackers,
  createTracker,
  updateTracker,
  deleteTracker,
  testTracker,
  fetchJackettDefault,
  fetchJackettIndexers,
} from "./api";

export function Trackers({ token }: { token: string }) {
  const [items, setItems] = useState<any[]>([]);
  const [name, setName] = useState("");
  const [jackettId, setJackettId] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [info, setInfo] = useState("");
  const [jackettIndexers, setJackettIndexers] = useState<any[]>([]);
  const [jackettSel, setJackettSel] = useState("");

  async function load() {
    setLoading(true);
    try {
      const data = await listTrackers(token);
      setItems(data || []);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (token) load();
  }, [token]);

  async function add() {
    try {
      await createTracker(token, {
        name,
        jackett_id: jackettId,
        username: username || undefined,
        password: password || undefined,
      });
      setName("");
      setJackettId("");
      setUsername("");
      setPassword("");
      setInfo("Created");
      await load();
    } catch (e: any) {
      setInfo(e.message || String(e));
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
      const def = await fetchJackettDefault(token);
      setJackettId(def.api_key);
      const idx = await fetchJackettIndexers(token);
      setJackettIndexers(idx || []);
    } catch (e: any) {
      alert(e.message || String(e));
    }
  }

  function onJackettIndexer(e: React.ChangeEvent<HTMLInputElement>) {
    const value = e.target.value;
    setJackettSel(value);
    const found = jackettIndexers.find((it) => it.name === value);
    if (found) setJackettId(found.id);
  }

  return (
    <div style={{ padding: 12 }}>
      <h3>Trackers</h3>
      <div style={{ marginBottom: 8 }}>
        <input
          placeholder="name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <input
          placeholder="jackett_id"
          value={jackettId}
          onChange={(e) => setJackettId(e.target.value)}
          style={{ width: 180, marginLeft: 6 }}
        />
        <input
          placeholder="username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          style={{ marginLeft: 6 }}
        />
        <input
          placeholder="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          style={{ marginLeft: 6 }}
        />
        {jackettIndexers.length > 0 && (
          <>
            <input
              placeholder="Jackett indexer"
              list="jackett-indexers"
              value={jackettSel}
              onChange={onJackettIndexer}
              style={{ marginLeft: 6 }}
            />
            <datalist id="jackett-indexers">
              {jackettIndexers.map((it) => (
                <option
                  key={it.id}
                  value={it.name}
                  label={it.description}
                />
              ))}
            </datalist>
          </>
        )}
        <button onClick={fetchFromJackett} style={{ marginLeft: 6 }}>
          Jackett
        </button>
        <button onClick={add} style={{ marginLeft: 6 }}>
          Add
        </button>
        {info && (
          <span style={{ marginLeft: 6, color: "#555" }}>{info}</span>
        )}
      </div>
      <table cellPadding={6} style={{ borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th>ID</th>
            <th>Name</th>
            <th>URL</th>
            <th>Creds</th>
            <th>Enabled</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {items.map((it) => (
            <tr key={it.id}>
              <td>{it.id}</td>
              <td>{it.name}</td>
              <td
                style={{
                  maxWidth: 500,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {it.base_url}
              </td>
              <td>{(it.username || it.api_key) ? "Yes" : "No"}</td>
              <td>{String(it.enabled)}</td>
              <td>
                <button onClick={() => toggle(it.id, it.enabled)}>
                  Toggle
                </button>{" "}
                <button onClick={() => test(it.id)}>Test</button>{" "}
                <button onClick={() => remove(it.id)}>Delete</button>
              </td>
            </tr>
          ))}
          {loading && (
            <tr>
              <td colSpan={6}>Loading...</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
