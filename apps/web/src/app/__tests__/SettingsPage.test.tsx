import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SettingsPage from '@/app/routes/settings';
import { renderWithProviders } from '@/app/test-utils';

const { capabilitiesState, apiKeysState, serviceSettingsState } = vi.hoisted(() => {
  const capabilitiesState = {
    data: { version: '1.2.3', services: { torrent_search: false } },
    isLoading: false,
  };

  const apiKeysState = {
    data: { api_keys: [{ provider: 'omdb', configured: false }] },
    isLoading: false,
    isError: false,
    error: null as Error | null,
    refetch: vi.fn(),
  };

  const serviceSettingsState = {
    data: {
      jackett: { url: 'http://jackett:9117', api_key_configured: false },
      qbittorrent: { url: 'http://qbittorrent:8080', username: 'admin', password_configured: false },
      downloads: { allowed_dirs: ['/downloads', '/music'], default_dir: '/downloads' },
    },
    isLoading: false,
    isError: false,
    error: null as Error | null,
  };

  return { capabilitiesState, apiKeysState, serviceSettingsState };
});

vi.mock('@/app/lib/api', () => ({
  useCapabilities: () => capabilitiesState,
  useApiKeys: () => apiKeysState,
  useServiceSettings: () => serviceSettingsState,
  useUpdateJackettSettings: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useUpdateQbittorrentSettings: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useUpdateDownloadSettings: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

describe('SettingsPage services tab', () => {
  beforeEach(() => {
    capabilitiesState.data = { version: '1.2.3', services: { torrent_search: false } };
    apiKeysState.data = { api_keys: [{ provider: 'omdb', configured: false }] };
    serviceSettingsState.data = {
      jackett: { url: 'http://jackett:9117', api_key_configured: false },
      qbittorrent: { url: 'http://qbittorrent:8080', username: 'admin', password_configured: false },
      downloads: { allowed_dirs: ['/downloads', '/music'], default_dir: '/downloads' },
    };
  });

  it('shows connected services and version info', async () => {
    const user = userEvent.setup();
    renderWithProviders(<SettingsPage />);

    await user.click(screen.getByRole('button', { name: /services/i }));

    expect(screen.getByText('Connected Services')).toBeInTheDocument();
    expect(screen.getByText(/Phelia version 1\.2\.3/)).toBeInTheDocument();
    expect(screen.getByLabelText(/OMDb API Key/i)).toBeInTheDocument();
  });
});
