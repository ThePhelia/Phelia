import axios, { AxiosInstance } from "axios";

// Base URLs
const RAW_API_BASE = (import.meta as any).env.VITE_API_BASE || "http://localhost:8000/api/v1";

function joinUrl(base: string, path: string) {
  const b = String(base || "").replace(/\/+$/, "");
  const p = String(path || "").replace(/^\/+/, "");
  return `${b}/${p}`;
}

export const API_BASE = RAW_API_BASE.replace(/\/+$/, "");

const http: AxiosInstance = axios.create({
  baseURL: API_BASE,
  withCredentials: false,
});

function normalizeAuthToken(token: string) {
  return token.startsWith("Bearer ") ? token : `Bearer ${token}`;
}

function authConfig(token?: string | null) {
  const trimmed = token?.trim();
  if (!trimmed) return undefined;
  return {
    headers: {
      Authorization: normalizeAuthToken(trimmed),
    },
  };
}

export function setToken(token?: string | null) {
  const cfg = authConfig(token);
  if (cfg?.headers.Authorization) {
    http.defaults.headers.common.Authorization = cfg.headers.Authorization;
  } else {
    delete http.defaults.headers.common.Authorization;
  }
}


// ---------- Auth ----------
export async function login(email: string, password: string) {
  const { data } = await http.post(joinUrl(API_BASE, "/auth/login"), { email, password });
  return data;
}

export async function register(email: string, password: string) {
  const { data } = await http.post(joinUrl(API_BASE, "/auth/register"), { email, password });
  return data;
}

// ---------- Trackers (configured in our DB) ----------
export async function listTrackers(token?: string | null) {
  const { data } = await http.get(joinUrl(API_BASE, "/trackers"), authConfig(token));
  return data;
}

export async function toggleTracker(id: string | number, token?: string | null) {
  const { data } = await http.post(
    joinUrl(API_BASE, `/trackers/${encodeURIComponent(id)}/toggle`),
    undefined,
    authConfig(token)
  );
  return data;
}

export async function testTracker(id: string | number, token?: string | null) {
  const { data } = await http.post(
    joinUrl(API_BASE, `/trackers/${encodeURIComponent(id)}/test`),
    undefined,
    authConfig(token)
  );
  return data;
}

export async function deleteTracker(id: string | number, token?: string | null) {
  const { data } = await http.delete(
    joinUrl(API_BASE, `/trackers/${encodeURIComponent(id)}`),
    authConfig(token)
  );
  return data;
}

// ---------- Providers from Jackett (indexers we can add) ----------
export async function listProviders(token?: string | null) {
  const { data } = await http.get(joinUrl(API_BASE, "/trackers/providers"), authConfig(token));
  return data;
}

export async function connectProvider(
  slug: string,
  creds?: Record<string, any>,
  token?: string | null
) {
  // Adds the provider as a configured tracker using given credentials
  const { data } = await http.post(
    joinUrl(API_BASE, `/trackers/providers/${encodeURIComponent(slug)}/connect`),
    creds || {},
    authConfig(token)
  );
  return data;
}

// ---------- Search & Downloads ----------
export async function searchApi(q: string, trackers?: string[]) {
  // Backend accepts GET /search?query=... (optionally with trackers list in body or query — keep it simple GET for now)
  const url = joinUrl(API_BASE, `/search?query=${encodeURIComponent(q)}`);
  const { data } = await http.get(url);
  return data;
}

export async function listDownloads() {
  const { data } = await http.get(joinUrl(API_BASE, "/downloads"));
  return data;
}

export async function createDownload(body: {
  magnet?: string;
  url?: string;
  savePath?: string;
  category?: string;
}) {
  // Body can contain either magnet or url (Jackett result link)
  const payload: any = { ...body };
  if (!payload.magnet && !payload.url) {
    throw new Error("Either magnet or url must be provided");
  }
  const { data } = await http.post(joinUrl(API_BASE, "/downloads"), payload);
  return data;
}

export async function getMagnetFromRelease(indexerId: string, releaseId: string) {
  // Optional helper if backend supports a direct magnet endpoint per release
  const url = joinUrl(API_BASE, `/trackers/${encodeURIComponent(indexerId)}/magnet/${encodeURIComponent(releaseId)}`);
  const { data } = await http.get(url);
  return data;
}
