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
      prowlarr: { url: 'http://prowlarr:9696', api_key_configured: false },
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
  useUpdateProwlarrSettings: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useUpdateQbittorrentSettings: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useUpdateDownloadSettings: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

describe('SettingsPage services tab', () => {
  beforeEach(() => {
    capabilitiesState.data = { version: '1.2.3', services: { torrent_search: false } };
    apiKeysState.data = { api_keys: [{ provider: 'omdb', configured: false }] };
    serviceSettingsState.data = {
      prowlarr: { url: 'http://prowlarr:9696', api_key_configured: false },
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

  it('shows Prowlarr fields with missing API key state', async () => {
    const user = userEvent.setup();
    renderWithProviders(<SettingsPage />);

    await user.click(screen.getByRole('button', { name: /services/i }));

    expect(screen.getByLabelText('Prowlarr URL')).toHaveValue('http://prowlarr:9696');
    expect(screen.getByLabelText('Prowlarr API Key')).toHaveAttribute('placeholder', 'Enter API key');
    expect(screen.queryByRole('button', { name: 'Clear API key' })).not.toBeInTheDocument();
  });

  it('renders clear action and replacement placeholder when API key is configured', async () => {
    serviceSettingsState.data = {
      ...serviceSettingsState.data,
      prowlarr: { url: 'http://prowlarr:9696', api_key_configured: true },
    };

    const user = userEvent.setup();
    renderWithProviders(<SettingsPage />);

    await user.click(screen.getByRole('button', { name: /services/i }));

    expect(screen.getByText('API key configured')).toBeInTheDocument();
    expect(screen.getByLabelText('Prowlarr API Key')).toHaveAttribute(
      'placeholder',
      'Enter new API key to replace',
    );
    expect(screen.getByRole('button', { name: 'Clear API key' })).toBeInTheDocument();
  });
});
