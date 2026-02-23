export function safeString(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback;
}

export function safeTrimmedString(value: unknown, fallback = ''): string {
  return safeString(value, fallback).trim();
}

export function safeList<T>(value: unknown, guard?: (item: unknown) => item is T): T[] {
  if (!Array.isArray(value)) {
    return [];
  }

  if (!guard) {
    return value as T[];
  }

  return value.filter((item): item is T => guard(item));
}

export function normalizeStringList(value: unknown): string[] {
  return safeList(value, (item): item is string => typeof item === 'string')
    .map((item) => item.trim())
    .filter(Boolean);
}
