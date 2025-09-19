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

// ---------- Auth ----------
export async function login(email: string, password: string) {
  const { data } = await http.post(joinUrl(API_BASE, "/auth/login"), { email, password });
  return data;
}

export async function register(email: string, password: string) {
  const { data } = await http.post(joinUrl(API_BASE, "/auth/register"), { email, password });
  return data;
}

// ---------- Search & Downloads ----------
export interface EnrichedProvider {
  name: string;
  used: boolean;
  extra?: Record<string, any> | null;
}

export interface EnrichedCard {
  media_type: "music" | "movie" | "tv" | "other";
  confidence: number;
  title: string;
  parsed?: Record<string, any> | null;
  ids: Record<string, any>;
  details: Record<string, any>;
  providers: EnrichedProvider[];
  reasons: string[];
  needs_confirmation: boolean;
}

export interface SearchResponse {
  items: EnrichedCard[];
  jackett_ui_url?: string;
  message?: string;
  error?: string;
}

export interface LookupBody {
  title: string;
  hint: "music" | "movie" | "tv" | "other" | "auto";
}

export async function searchMetadata(q: string, limit = 40): Promise<SearchResponse> {
  const url = joinUrl(API_BASE, `/search?q=${encodeURIComponent(q)}&limit=${limit}`);
  const { data } = await http.get(url);
  return data as SearchResponse;
}

export async function lookupMetadata(body: LookupBody): Promise<EnrichedCard> {
  const { data } = await http.post(joinUrl(API_BASE, "/meta/lookup"), body);
  return data as EnrichedCard;
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

export async function pauseDownload(id: string) {
  const { data } = await http.post(
    joinUrl(API_BASE, `/downloads/${encodeURIComponent(id)}/pause`),
    {}
  );
  return data;
}

export async function resumeDownload(id: string) {
  const { data } = await http.post(
    joinUrl(API_BASE, `/downloads/${encodeURIComponent(id)}/resume`),
    {}
  );
  return data;
}

export async function deleteDownload(
  id: string,
  options: { withFiles?: boolean } = {}
) {
  const baseUrl = joinUrl(API_BASE, `/downloads/${encodeURIComponent(id)}`);
  const url =
    typeof options.withFiles === "boolean"
      ? `${baseUrl}?withFiles=${options.withFiles ? "true" : "false"}`
      : baseUrl;
  const { data } = await http.delete(url);
  return data;
}
