const SPEED_UNITS = ['B/s', 'KiB/s', 'MiB/s', 'GiB/s', 'TiB/s'];
const PAUSED_KEYWORDS = ['paused', 'stopped'];
const STATUS_LABELS = {
    checkingDL: 'Checking',
    checkingUP: 'Checking',
    downloading: 'Downloading',
    forcedDL: 'Downloading',
    forcedUP: 'Seeding',
    metaDL: 'Fetching metadata',
    pausedDL: 'Paused',
    pausedUP: 'Paused',
    queuedDL: 'Queued',
    queuedUP: 'Queued',
    stalledDL: 'Stalled',
    stalledUP: 'Stalled',
    uploading: 'Seeding',
    missingFiles: 'Missing files',
    error: 'Error',
};
export function formatDownloadProgress(item) {
    const percent = Math.round((item.progress ?? 0) * 100);
    return `${percent}%`;
}
export function formatDownloadSpeed(speed) {
    if (speed === undefined || speed === null) {
        return '—';
    }
    const safeSpeed = Math.max(0, Number(speed));
    if (!Number.isFinite(safeSpeed)) {
        return '—';
    }
    if (safeSpeed === 0) {
        return '0 B/s';
    }
    let value = safeSpeed;
    let unitIndex = 0;
    while (value >= 1024 && unitIndex < SPEED_UNITS.length - 1) {
        value /= 1024;
        unitIndex += 1;
    }
    const formatted = value >= 10 ? value.toFixed(0) : value.toFixed(1);
    return `${formatted} ${SPEED_UNITS[unitIndex]}`;
}
export function formatDownloadEta(eta) {
    if (eta === undefined || eta === null) {
        return '—';
    }
    const totalSeconds = Math.max(0, Math.floor(eta));
    if (!Number.isFinite(totalSeconds) || totalSeconds === 0) {
        return '—';
    }
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    const parts = [];
    if (hours > 0) {
        parts.push(`${hours}h`);
    }
    if (minutes > 0) {
        parts.push(`${minutes}m`);
    }
    if (parts.length === 0) {
        parts.push(`${seconds}s`);
    }
    return parts.slice(0, 2).join(' ');
}
export function formatDownloadStatus(status) {
    if (!status) {
        return 'Queued';
    }
    const normalized = status.trim();
    if (!normalized) {
        return 'Queued';
    }
    const key = normalized.replace(/\s+/g, '');
    const mapped = STATUS_LABELS[key];
    if (mapped) {
        return mapped;
    }
    return normalized
        .replace(/([a-z])([A-Z])/g, '$1 $2')
        .replace(/DL$/, ' Download')
        .replace(/UP$/, ' Upload')
        .replace(/\b\w/g, (match) => match.toUpperCase());
}
export function isDownloadPaused(status) {
    if (!status) {
        return false;
    }
    const normalized = status.toLowerCase();
    return PAUSED_KEYWORDS.some((keyword) => normalized.includes(keyword));
}
