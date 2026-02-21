import { resolveApiBase } from '@/app/lib/api';

describe('resolveApiBase', () => {
  const originalLocation = window.location;

  afterEach(() => {
    Object.defineProperty(window, 'location', {
      value: originalLocation,
      writable: true,
    });
  });

  it('rewrites localhost API base to current host when app is not served from localhost', () => {
    Object.defineProperty(window, 'location', {
      value: {
        ...window.location,
        hostname: '192.168.1.50',
      },
      writable: true,
    });

    expect(resolveApiBase('http://localhost:8000/api/v1')).toBe('http://192.168.1.50:8000/api/v1');
    expect(resolveApiBase('http://127.0.0.1:8000/api/v1')).toBe('http://192.168.1.50:8000/api/v1');
  });

  it('keeps localhost API base when app is served from localhost', () => {
    Object.defineProperty(window, 'location', {
      value: {
        ...window.location,
        hostname: 'localhost',
      },
      writable: true,
    });

    expect(resolveApiBase('http://localhost:8000/api/v1')).toBe('http://localhost:8000/api/v1');
  });
});
