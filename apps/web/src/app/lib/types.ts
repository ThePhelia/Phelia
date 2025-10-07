export type MediaKind = 'movie' | 'tv' | 'album';

export interface DiscoverItem {
  kind: MediaKind;
  id: string;
  title: string;
  subtitle?: string;
  year?: number;
  poster?: string;
  backdrop?: string;
  rating?: number;
  genres?: string[];
  badges?: string[];
  progress?: number;
  meta?: Record<string, unknown>;
}

export interface PaginatedResponse<T> {
  page: number;
  total_pages: number;
  items: T[];
}

export interface CastMember {
  name: string;
  role?: string;
  photo?: string;
}

export interface CrewMember {
  name: string;
  job?: string;
}

export interface TrackInfo {
  index: number;
  title: string;
  length?: number;
}

export interface EpisodeInfo {
  episode_number: number;
  title: string;
  watched?: boolean;
  runtime?: number;
}

export interface SeasonInfo {
  season_number: number;
  name?: string;
  episodes: EpisodeInfo[];
}

export interface AvailabilityInfo {
  streams?: Array<{ provider: string; quality?: string }>;
  torrents?: Array<{ provider: string; seeders?: number; size?: string }>;
}

export interface EnrichedProvider {
  name: string;
  used: boolean;
  extra?: Record<string, unknown> | null;
}

export interface SearchResultMeta {
  confidence?: number;
  needs_confirmation?: boolean;
  reasons?: string[];
  providers?: EnrichedProvider[];
  ids?: Record<string, unknown>;
  parsed?: Record<string, unknown> | null;
  source_title?: string;
  source_kind?: 'music' | 'movie' | 'tv' | 'other';
  [key: string]: unknown;
}

export interface SearchResultItem extends DiscoverItem {
  meta?: SearchResultMeta;
}

export interface SearchResponseMeta {
  message?: string;
  error?: string;
  [key: string]: unknown;
}

export interface SearchResponse extends PaginatedResponse<SearchResultItem>, SearchResponseMeta {}

export interface ExternalLink {
  label: string;
  url: string;
}

export interface DetailResponse {
  id: string;
  kind: MediaKind;
  title: string;
  year?: number;
  tagline?: string;
  overview?: string;
  poster?: string;
  backdrop?: string;
  rating?: number;
  genres?: string[];
  cast?: CastMember[];
  crew?: CrewMember[];
  tracks?: TrackInfo[];
  seasons?: SeasonInfo[];
  similar?: DiscoverItem[];
  recommended?: DiscoverItem[];
  links?: {
    play?: string;
    jellyfin?: string;
    external?: ExternalLink[];
  };
  availability?: AvailabilityInfo;
  musicbrainz?: MusicBrainzInfo | null;
}

export interface MusicBrainzInfo {
  artist_id?: string | null;
  artist_name?: string | null;
  release_group_id?: string | null;
}

export interface SimilarArtist {
  mbid?: string | null;
  name?: string | null;
  score?: number | null;
}

export interface SearchParams {
  q: string;
  kind?: 'all' | 'movie' | 'tv' | 'music';
  page?: number;
}

export interface DiscoverParams {
  sort?: 'trending' | 'popular' | 'new' | 'az';
  genre?: string;
  year?: string;
  language?: string;
  country?: string;
  providers?: string;
  type?: 'album' | 'ep' | 'single';
  style?: string;
  artist?: string;
  page?: number;
}

export interface LibraryItemSummary {
  watchlist: DiscoverItem[];
  favorites: DiscoverItem[];
  playlists: Array<{ id: string; title: string; items: DiscoverItem[] }>;
}


export interface DownloadItem {
  id: number;
  name?: string | null;
  magnet?: string | null;
  hash?: string | null;
  progress?: number | null;
  status?: string | null;
  eta?: number | null;
  dlspeed?: number | null;
  upspeed?: number | null;
  save_path?: string | null;
}
export interface CapabilitiesResponse {
  services: Record<string, boolean>;
  version: string;
  links?: Record<string, string | undefined>;
  plugins?: {
    upload: boolean;
    urlInstall: boolean;
    phexOnly: boolean;
  };
}

export interface ListMutationInput {
  action: 'add' | 'remove';
  list: 'watchlist' | 'favorites' | 'playlist';
  item: { kind: MediaKind; id: string };
}

export interface PluginSettingFieldSchema {
  type?: string | string[];
  title?: string;
  description?: string;
  enum?: Array<string | number | boolean | null>;
  format?: string;
  default?: unknown;
  [key: string]: unknown;
}

export interface PluginSettingsSchema {
  type?: string;
  title?: string;
  description?: string;
  properties?: Record<string, PluginSettingFieldSchema>;
  required?: string[];
  [key: string]: unknown;
}

export interface PluginSettingsSummary {
  id: string;
  name: string;
  contributes_settings: boolean;
  settings_schema?: PluginSettingsSchema | null;
}

export interface PluginSettingsListResponse {
  plugins: PluginSettingsSummary[];
}

export interface PluginSettingsValuesResponse {
  values: Record<string, unknown>;
}

export interface PluginSettingsUpdateRequest {
  values: Record<string, unknown>;
}
