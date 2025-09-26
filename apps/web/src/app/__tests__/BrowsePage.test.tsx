import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import BrowsePage from '@/app/routes/browse';
import { renderWithProviders } from '@/app/test-utils';

const { toastErrorMock, toastMock } = vi.hoisted(() => {
  const toastErrorMock = vi.fn();
  const toastMock = { error: toastErrorMock } as const;
  return { toastErrorMock, toastMock };
});

vi.mock('sonner', () => ({
  toast: toastMock,
}));

describe('BrowsePage', () => {
  const fetchMock = vi.fn();

  function createResponse(data: unknown, ok = true, status = 200) {
    return Promise.resolve({
      ok,
      status,
      json: async () => data,
    } as Response);
  }

  beforeEach(() => {
    fetchMock.mockReset();
    toastErrorMock.mockReset();
    global.fetch = fetchMock;
  });

  it('renders curated genres', async () => {
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

    renderWithProviders(<BrowsePage />);

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

    renderWithProviders(<BrowsePage />);

    const ambientButton = await screen.findByRole('button', { name: /ambient/i });
    await user.click(ambientButton);

    await waitFor(() => {
      expect(screen.getByText('Deep Drift')).toBeInTheDocument();
      expect(screen.getByText('Ambient Flow')).toBeInTheDocument();
    });

    expect(calls.some((url) => url.includes('/new?genre=ambient'))).toBe(true);
    expect(calls.some((url) => url.includes('/top'))).toBe(true);
  });

  it('shows toasts on fetch errors but keeps UI responsive', async () => {
    fetchMock.mockImplementation((input: RequestInfo) => {
      const url = typeof input === 'string' ? input : (input as Request).url;
      if (url.includes('/genres')) {
        return createResponse({
          genres: [{ key: 'rock', label: 'Rock', appleGenreId: 21 }],
        });
      }
      if (url.includes('/new')) {
        return createResponse({ message: 'upstream error' }, false, 502);
      }
      if (url.includes('/top')) {
        return createResponse({
          items: [
            {
              id: 'apple42',
              title: 'Guitar Echoes',
              artist: 'Ampersand',
              releaseDate: '2024-03-01',
            },
          ],
        });
      }
      return createResponse({ items: [] });
    });

    renderWithProviders(<BrowsePage />);

    await waitFor(() => {
      expect(toastErrorMock).toHaveBeenCalledWith('Unable to load new releases.');
    });

    const headers = await screen.findAllByText(/Most Recent/i);
    expect(headers.length).toBeGreaterThan(0);
    expect(screen.queryByText('Guitar Echoes')).toBeInTheDocument();
  });
});
