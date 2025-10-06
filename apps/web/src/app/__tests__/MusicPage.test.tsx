import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import MusicPage from '@/app/routes/music';
import { renderWithProviders } from '@/app/test-utils';

const { toastErrorMock, toastMock } = vi.hoisted(() => {
  const toastErrorMock = vi.fn();
  const toastMock = { error: toastErrorMock } as const;
  return { toastErrorMock, toastMock };
});

vi.mock('sonner', () => ({
  toast: toastMock,
}));

const discoverMock = vi.hoisted(() =>
  vi.fn(() => ({
    data: { pages: [{ items: [] }] },
    isLoading: false,
    isFetching: false,
    hasNextPage: false,
    fetchNextPage: vi.fn(),
  })),
);

const searchMock = vi.hoisted(() =>
  vi.fn(() => ({
    data: { pages: [{ items: [] }] },
    isLoading: false,
    isFetching: false,
    hasNextPage: false,
    fetchNextPage: vi.fn(),
  })),
);

const mutateListMock = vi.hoisted(() => vi.fn(() => ({ mutateAsync: vi.fn() })));

vi.mock('@/app/lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/app/lib/api')>();
  return {
    ...actual,
    useDiscover: discoverMock,
    useSearch: searchMock,
    useMutateList: mutateListMock,
  };
});

describe('MusicPage', () => {
  const fetchMock = vi.fn();

  function createResponse(data: unknown, ok = true, status = 200) {
    return Promise.resolve({
      ok,
      status,
      json: async () => data,
    } as Response);
  }

  beforeEach(() => {
    vi.stubEnv('VITE_API_BASE', 'http://phelia.test/api/v1');
    fetchMock.mockReset();
    toastErrorMock.mockReset();
    discoverMock.mockClear();
    searchMock.mockClear();
    mutateListMock.mockClear();
    (global as unknown as { IntersectionObserver?: unknown }).IntersectionObserver = vi.fn(() => ({
      observe: vi.fn(),
      disconnect: vi.fn(),
      unobserve: vi.fn(),
    }));
    global.fetch = fetchMock;
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('renders curated genres from the API', async () => {
    fetchMock.mockImplementation((input: RequestInfo) => {
      const url = typeof input === 'string' ? input : (input as Request).url;
      if (url.includes('/genres')) {
        return createResponse({
          genres: [
            { key: 'techno', label: 'Techno', appleGenreId: 1 },
            { key: 'house', label: 'House', appleGenreId: 2 },
          ],
        });
      }
      return createResponse({ items: [] });
    });

    renderWithProviders(<MusicPage />);

    expect(await screen.findByRole('button', { name: /techno/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /house/i })).toBeInTheDocument();
  });

  it('loads rails when selecting a genre', async () => {
    const user = userEvent.setup();
    const calls: string[] = [];
    fetchMock.mockImplementation((input: RequestInfo) => {
      const url = typeof input === 'string' ? input : (input as Request).url;
      calls.push(url);
      if (url.includes('/genres')) {
        return createResponse({
          genres: [
            { key: 'techno', label: 'Techno', appleGenreId: 1 },
            { key: 'ambient', label: 'Ambient', appleGenreId: 2 },
          ],
        });
      }
      if (url.includes('/new')) {
        const params = new URL(url, 'http://localhost');
        if (params.searchParams.get('genre') === 'ambient') {
          return createResponse({
            items: [
              {
                mbid: 'mb2',
                title: 'Deep Drift',
                artist: 'Atmos Duo',
                firstReleaseDate: '2024-05-01',
                primaryType: 'Album',
                secondaryTypes: ['Live'],
              },
            ],
          });
        }
        return createResponse({ items: [] });
      }
      if (url.includes('/top')) {
        const params = new URL(url, 'http://localhost');
        if (params.searchParams.get('genre_id') === '2') {
          return createResponse({
            items: [
              {
                id: 'apple1',
                title: 'Ambient Flow',
                artist: 'Sky City',
                artwork: 'https://example.com/art.jpg',
                releaseDate: '2024-04-20',
              },
            ],
          });
        }
        return createResponse({ items: [] });
      }
      return createResponse({ items: [] });
    });

    renderWithProviders(<MusicPage />);

    const ambientButton = await screen.findByRole('button', { name: /ambient/i });
    await user.click(ambientButton);

    await waitFor(() => {
      expect(screen.getByText('Deep Drift')).toBeInTheDocument();
      expect(screen.getByText('Ambient Flow')).toBeInTheDocument();
    });

    const newReleaseUrl = calls.find((url) => url.includes('/discovery/new') && url.includes('genre=ambient'));
    expect(newReleaseUrl).toBeDefined();
    expect(newReleaseUrl).toBe('http://phelia.test/api/v1/discovery/new?genre=ambient&limit=30&days=30');
    expect(calls.some((url) => url.includes('/top'))).toBe(true);
  });

  it('falls back to curated genres when the API fails', async () => {
    fetchMock.mockRejectedValue(new Error('network error'));

    renderWithProviders(<MusicPage />);

    expect(await screen.findByRole('button', { name: /techno/i })).toBeInTheDocument();
    expect(toastErrorMock).not.toHaveBeenCalled();
  });
});
