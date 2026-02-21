import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SettingsPage from '@/app/routes/settings';
import { renderWithProviders } from '@/app/test-utils';

const { capabilitiesState, apiKeysState, serviceSettingsState, integrationSettingsState, updateIntegrationsMutate } = vi.hoisted(() => {
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

  const integrationSettingsState = {
    data: {
      integrations: [
        {
          key: 'tmdb.api_key',
          label: 'TMDb API Key',
          required: false,
          masked_at_rest: true,
          validation_rule: 'min_length:16',
          configured: true,
          value: '••••••••',
        },
      ],
    },
    isLoading: false,
    isError: false,
    error: null as Error | null,
    refetch: vi.fn(),
  };

  const updateIntegrationsMutate = vi.fn();

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

  return { capabilitiesState, apiKeysState, serviceSettingsState, integrationSettingsState, updateIntegrationsMutate };
});

vi.mock('@/app/lib/api', () => ({
  useCapabilities: () => capabilitiesState,
  useApiKeys: () => apiKeysState,
  useServiceSettings: () => serviceSettingsState,
  useUpdateProwlarrSettings: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useUpdateQbittorrentSettings: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useUpdateDownloadSettings: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useIntegrationSettings: () => integrationSettingsState,
  useUpdateIntegrationSettings: () => ({ mutateAsync: updateIntegrationsMutate, isPending: false }),
}));

describe('SettingsPage services tab', () => {
  beforeEach(() => {
    capabilitiesState.data = { version: '1.2.3', services: { torrent_search: false } };
    apiKeysState.data = { api_keys: [{ provider: 'omdb', configured: false }] };
    integrationSettingsState.data = {
      integrations: [
        {
          key: 'tmdb.api_key',
          label: 'TMDb API Key',
          required: false,
          masked_at_rest: true,
          validation_rule: 'min_length:16',
          configured: true,
          value: '••••••••',
        },
      ],
    };
    updateIntegrationsMutate.mockReset();
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

    await waitFor(() => expect(screen.getByLabelText('Prowlarr URL')).toHaveValue('http://prowlarr:9696'));
    expect(screen.getByLabelText('Prowlarr API Key')).toHaveAttribute('placeholder', 'Enter API key');
    expect(screen.queryByRole('button', { name: 'Clear API key' })).not.toBeInTheDocument();
  });

  it('renders integrations and validates before save', async () => {
    const user = userEvent.setup();
    updateIntegrationsMutate.mockResolvedValue({ integrations: [] });

    renderWithProviders(<SettingsPage />);
    await user.click(screen.getByRole('button', { name: /services/i }));

    const saveButton = screen.getByRole('button', { name: 'Save Integrations' });
    expect(saveButton).toBeDisabled();

    const integrationInput = screen.getByLabelText('TMDb API Key');
    await user.type(integrationInput, 'short');

    expect(screen.getByText('TMDb API Key must be at least 16 characters.')).toBeInTheDocument();
    expect(saveButton).toBeDisabled();

    await user.clear(integrationInput);
    await user.type(integrationInput, '1234567890123456');
    expect(saveButton).toBeEnabled();

    await user.click(saveButton);
    expect(updateIntegrationsMutate).toHaveBeenCalledWith({ integrations: { 'tmdb.api_key': '1234567890123456' } });
  });
});
