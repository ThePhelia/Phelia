import { useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
export function useQueryParams(defaults) {
    const [searchParams, setSearchParams] = useSearchParams();
    const params = useMemo(() => {
        const entries = Object.entries(defaults).map(([key, defaultValue]) => {
            const values = searchParams.getAll(key);
            if (!values.length)
                return [key, defaultValue];
            if (Array.isArray(defaultValue))
                return [key, values];
            if (typeof defaultValue === 'number') {
                const parsed = Number(values[0]);
                return [key, Number.isNaN(parsed) ? defaultValue : parsed];
            }
            if (typeof defaultValue === 'boolean') {
                return [key, values[0] === 'true'];
            }
            return [key, values[0]];
        });
        return Object.fromEntries(entries);
    }, [defaults, searchParams]);
    const update = useCallback((next) => {
        const newParams = new URLSearchParams(searchParams.toString());
        Object.entries(next).forEach(([key, value]) => {
            newParams.delete(key);
            if (value === undefined || value === null || value === '' || value === false) {
                return;
            }
            if (Array.isArray(value)) {
                value.forEach((item) => {
                    if (item !== undefined && item !== null && item !== '') {
                        newParams.append(key, String(item));
                    }
                });
                return;
            }
            newParams.set(key, String(value));
        });
        setSearchParams(newParams, { replace: true });
    }, [searchParams, setSearchParams]);
    return [params, update];
}
