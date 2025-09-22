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

export interface JackettTorrentDetails {
  magnet?: string | null;
  url?: string | null;
  size?: string | number | null;
  seeders?: number | null;
  leechers?: number | null;
  tracker?: string | null;
  indexer?: string | Record<string, unknown> | null;
  category?: string | string[] | null;
  title?: string | null;
}

export interface JackettSearchItem {
  media_type: 'music' | 'movie' | 'tv' | 'other';
  confidence: number;
  title: string;
  parsed?: Record<string, unknown> | null;
  ids: Record<string, unknown>;
  details: Record<string, unknown> & { jackett?: JackettTorrentDetails };
  providers: EnrichedProvider[];
  reasons: string[];
  needs_confirmation: boolean;
}

export interface JackettSearchResponseMeta {
  message?: string;
  jackett_ui_url?: string;
  error?: string;
  [key: string]: unknown;
}

export interface JackettSearchResponse extends JackettSearchResponseMeta {
  items: JackettSearchItem[];
}

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
  id: string;
  name: string;
  provider?: string;
  progress?: number;
  status?: string;
  eta?: string;
  speed?: string;
  size?: string;
}
export interface CapabilitiesResponse {
  services: Record<string, boolean>;
  version: string;
  links?: {
    jackett?: string;
    [key: string]: string | undefined;
  };
  jackettUrl?: string;
}

export interface ListMutationInput {
  action: 'add' | 'remove';
  list: 'watchlist' | 'favorites' | 'playlist';
  item: { kind: MediaKind; id: string };
}

export type MetadataProviderSlug =
  | 'tmdb'
  | 'omdb'
  | 'discogs'
  | 'lastfm'
  | 'musicbrainz'
  | (string & {});

export interface ProviderSettingSummary {
  configured: boolean;
  preview?: string | null;
}

export interface ProviderSettingStatus extends ProviderSettingSummary {
  provider: MetadataProviderSlug;
}

export type ProviderSettingsApiResponse =
  | { providers: ProviderSettingStatus[] }
  | { providers: Record<string, ProviderSettingSummary | ProviderSettingStatus> }
  | Record<string, ProviderSettingSummary | ProviderSettingStatus>;

export interface ProviderSettingMutationVariables {
  provider: MetadataProviderSlug;
  api_key: string | null;
}

export interface ProviderSettingUpdateRequest {
  api_key: string | null;
}
