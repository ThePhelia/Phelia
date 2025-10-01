export type MetaItemType = 'movie' | 'tv' | 'album';

export interface MetaSearchItem {
  type: MetaItemType;
  provider: string;
  id: string;
  title: string;
  subtitle?: string;
  year?: number;
  poster?: string;
  extra?: Record<string, unknown>;
}

export interface MetaSearchResponse {
  items: MetaSearchItem[];
}

export interface MetaCastMember {
  name: string;
  character?: string | null;
}

export interface MetaTVInfo {
  seasons?: number | null;
  episodes?: number | null;
}

export interface MetaTrack {
  position?: string | null;
  title: string;
  duration?: string | null;
}

export interface MetaAlbumInfo {
  artist: string;
  album: string;
  year?: number | null;
  styles: string[];
  tracklist: MetaTrack[];
}

export interface CanonicalMovie {
  title: string;
  year?: number | null;
}

export interface CanonicalTV {
  title: string;
  season?: number | null;
  episode?: number | null;
}

export interface CanonicalAlbum {
  artist: string;
  album: string;
  year?: number | null;
}

export interface CanonicalPayload {
  query: string;
  movie?: CanonicalMovie | null;
  tv?: CanonicalTV | null;
  album?: CanonicalAlbum | null;
}

export interface MetaDetail {
  type: MetaItemType;
  title: string;
  year?: number | null;
  poster?: string | null;
  backdrop?: string | null;
  synopsis?: string | null;
  genres: string[];
  runtime?: number | null;
  rating?: number | null;
  cast: MetaCastMember[];
  tv?: MetaTVInfo | null;
  album?: MetaAlbumInfo | null;
  canonical: CanonicalPayload;
}

