import type {
  CapabilitiesResponse,
  IntegrationField,
  IntegrationSettingsResponse,
  ProwlarrIndexer,
  ProwlarrIndexerField,
  ProwlarrIndexerTemplate,
  ServiceSettingsResponse,
} from './types';

function toRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : {};
}

function toString(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback;
}

function toBoolean(value: unknown, fallback = false): boolean {
  return typeof value === 'boolean' ? value : fallback;
}

function toNumber(value: unknown, fallback = 0): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
}

function toNullableNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function toStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === 'string').map((item) => item.trim()).filter(Boolean);
}

function normalizeIndexerField(input: unknown): ProwlarrIndexerField {
  const record = toRecord(input);
  return {
    name: toString(record.name),
    label: toString(record.label),
    value: record.value,
    type: typeof record.type === 'string' ? record.type : null,
    required: toBoolean(record.required),
    help_text: typeof record.help_text === 'string' ? record.help_text : null,
    options: Array.isArray(record.options)
      ? record.options.filter((option): option is Record<string, unknown> => Boolean(option && typeof option === 'object'))
      : [],
  };
}

function normalizeIndexer(input: unknown): ProwlarrIndexer {
  const record = toRecord(input);
  return {
    id: toNumber(record.id),
    name: toString(record.name, 'Unnamed indexer'),
    enable: toBoolean(record.enable, true),
    implementation: typeof record.implementation === 'string' ? record.implementation : null,
    implementation_name: typeof record.implementation_name === 'string' ? record.implementation_name : null,
    protocol: typeof record.protocol === 'string' ? record.protocol : null,
    app_profile_id: toNullableNumber(record.app_profile_id),
    priority: toNullableNumber(record.priority),
    fields: Array.isArray(record.fields) ? record.fields.map(normalizeIndexerField).filter((field) => Boolean(field.name)) : [],
  };
}

function normalizeIndexerTemplate(input: unknown): ProwlarrIndexerTemplate {
  const record = toRecord(input);
  return {
    id: toNumber(record.id),
    name: toString(record.name, 'Unnamed template'),
    implementation: typeof record.implementation === 'string' ? record.implementation : null,
    implementation_name: typeof record.implementation_name === 'string' ? record.implementation_name : null,
    protocol: typeof record.protocol === 'string' ? record.protocol : null,
    fields: Array.isArray(record.fields) ? record.fields.map(normalizeIndexerField).filter((field) => Boolean(field.name)) : [],
  };
}

export function normalizeCapabilitiesResponse(input: unknown): CapabilitiesResponse {
  const record = toRecord(input);
  const services = toRecord(record.services);
  const links = toRecord(record.links);
  return {
    version: toString(record.version, 'unknown'),
    services: Object.fromEntries(Object.entries(services).map(([key, value]) => [key, toBoolean(value)])),
    links: Object.entries(links).reduce<Record<string, string | undefined>>((acc, [key, value]) => {
      if (typeof value === 'string') {
        acc[key] = value;
      }
      return acc;
    }, {}),
  };
}

export function normalizeApiKeysResponse(input: unknown): { api_keys: Array<{ provider: string; configured: boolean; value?: string }> } {
  const record = toRecord(input);
  const apiKeys = Array.isArray(record.api_keys) ? record.api_keys : [];

  return {
    api_keys: apiKeys
      .map((entry) => {
        const item = toRecord(entry);
        const provider = toString(item.provider);
        if (!provider) return null;
        return {
          provider,
          configured: toBoolean(item.configured),
          ...(typeof item.value === 'string' ? { value: item.value } : {}),
        };
      })
      .filter((entry): entry is { provider: string; configured: boolean; value?: string } => Boolean(entry)),
  };
}

export function normalizeServiceSettingsResponse(input: unknown): ServiceSettingsResponse {
  const record = toRecord(input);
  const prowlarr = toRecord(record.prowlarr);
  const qbittorrent = toRecord(record.qbittorrent);
  const downloads = toRecord(record.downloads);

  return {
    prowlarr: {
      url: toString(prowlarr.url),
      api_key_configured: toBoolean(prowlarr.api_key_configured),
    },
    qbittorrent: {
      url: toString(qbittorrent.url),
      username: toString(qbittorrent.username),
      password_configured: toBoolean(qbittorrent.password_configured),
    },
    downloads: {
      allowed_dirs: toStringArray(downloads.allowed_dirs),
      default_dir: toString(downloads.default_dir),
    },
  };
}

function normalizeIntegrationField(input: unknown): IntegrationField | null {
  const record = toRecord(input);
  const key = toString(record.key);
  if (!key) return null;

  return {
    key,
    label: toString(record.label, key),
    required: toBoolean(record.required),
    masked_at_rest: toBoolean(record.masked_at_rest),
    validation_rule: toString(record.validation_rule, 'optional'),
    configured: toBoolean(record.configured),
    value: typeof record.value === 'string' ? record.value : null,
  };
}

export function normalizeIntegrationSettingsResponse(input: unknown): IntegrationSettingsResponse {
  const record = toRecord(input);
  const integrations = Array.isArray(record.integrations) ? record.integrations : [];
  return {
    integrations: integrations
      .map(normalizeIntegrationField)
      .filter((field): field is IntegrationField => Boolean(field)),
  };
}

export function normalizeProwlarrIndexersResponse(input: unknown): { indexers: ProwlarrIndexer[] } {
  const record = toRecord(input);
  const indexers = Array.isArray(record.indexers) ? record.indexers : [];
  return {
    indexers: indexers.map(normalizeIndexer).filter((indexer) => indexer.id > 0),
  };
}

export function normalizeProwlarrIndexerTemplatesResponse(input: unknown): { templates: ProwlarrIndexerTemplate[] } {
  const record = toRecord(input);
  const templates = Array.isArray(record.templates) ? record.templates : [];
  return {
    templates: templates.map(normalizeIndexerTemplate).filter((template) => template.id > 0),
  };
}
