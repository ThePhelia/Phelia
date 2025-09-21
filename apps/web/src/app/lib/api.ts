// Basic API helper for your Vite/React app.
// Uses axios with a typed wrapper and clean braces/semicolons to avoid TS1005/TS1109.

import axios, { AxiosInstance } from "axios";

export const API_BASE: string =
  (import.meta as any).env?.VITE_API_BASE ?? "http://localhost:8000/api/v1";

const http: AxiosInstance = axios.create({
  baseURL: API_BASE,
  withCredentials: false,
  headers: {
    "Content-Type": "application/json",
  },
});

// ---- Types ----
export type LoginPayload = { username: string; password: string };
export type RegisterPayload = { username: string; password: string; email?: string };

export type SearchResult = {
  id: string | number;
  title: string;
  subtitle?: string;
  year?: string | number;
  coverUrl?: string;
  description?: string;
};

export type TrackerProvider = {
  id: string;
  name: string;
  public: boolean;
};

export type ConnectTrackerPayload = {
  providerId: string;
  username?: string;
  password?: string;
  apikey?: string;
};

export type DownloadItem = {
  id: string | number;
  name: string;
  progress: number; // 0..100
  state: string;
};

// ---- Helpers ----
const ok = <T,>(v: T): T => v;

// ---- Auth ----
export async function login(payload: LoginPayload): Promise<void> {
  await http.post("/auth/login", payload);
}

export async function register(payload: RegisterPayload): Promise<void> {
  await http.post("/auth/register", payload);
}

// ---- Search ----
export async function searchApi(q: string, limit = 40): Promise<SearchResult[]> {
  const res = await http.get("/search", { params: { q, limit } });
  return ok(res.data as SearchResult[]);
}

// ---- Trackers ----
export async function getTrackers(): Promise<TrackerProvider[]> {
  const res = await http.get("/trackers/providers");
  return ok(res.data as TrackerProvider[]);
}

export async function connectTracker(
  payload: ConnectTrackerPayload
): Promise<{ ok: true }> {
  await http.post("/trackers/connect", payload);
  return { ok: true };
}

// ---- Downloads ----
export async function listDownloads(): Promise<DownloadItem[]> {
  const res = await http.get("/downloads");
  return ok(res.data as DownloadItem[]);
}

// ---- Utility: jackett ping (optional) ----
export async function jackettIndexers(): Promise<any> {
  const res = await http.get("/trackers");
  return res.data;
}

