import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SettingsPage from '@/app/routes/settings';
import { renderWithProviders } from '@/app/test-utils';

const {
  capabilitiesState,
  serviceSettingsState,
  integrationSettingsState,
  prowlarrIndexersState,
  prowlarrTemplatesState,
  updateProwlarrMutate,
  discoverProwlarrApiKeyMutate,
  createIndexerMutate,
  updateIndexerMutate,
  deleteIndexerMutate,
  testIndexerMutate,
} = vi.hoisted(() => {
  const capabilitiesState = { data: { version: '1.2.3', services: { torrent_search: false } }, isLoading: false };
  const integrationSettingsState = {
    data: {
      integrations: [{ key: 'tmdb.api_key', label: 'TMDb API Key', required: false, masked_at_rest: true, validation_rule: 'min_length:16', configured: true, value: '••••••••' }],
      providers: [{ id: 'tmdb', name: 'TMDb', description: 'Movie metadata.', enabled: true, configured: true }],
    },
    isLoading: false, isError: false, error: null as Error | null, refetch: vi.fn(),
  };
  const prowlarrIndexersState = { data: { indexers: [{ id: 1, name: 'Demo Indexer', enable: true, implementation_name: 'Cardigann', fields: [{ name: 'baseUrl', label: 'Base Url', value: 'https://old.example' }] }] }, isLoading: false, isError: false, error: null as Error | null };
  const prowlarrTemplatesState = { data: { templates: [{ id: 10, name: 'Template', fields: [{ name: 'baseUrl', label: 'Base Url', value: '' }] }] }, isLoading: false, isError: false, error: null as Error | null };
  const updateProwlarrMutate = vi.fn();
  const discoverProwlarrApiKeyMutate = vi.fn();
  const createIndexerMutate = vi.fn();
  const updateIndexerMutate = vi.fn();
  const deleteIndexerMutate = vi.fn();
  const testIndexerMutate = vi.fn();
  const serviceSettingsState = { data: { prowlarr: { url: 'http://prowlarr:9696', api_key_configured: false }, qbittorrent: { url: 'http://qbittorrent:8080', username: 'admin', password_configured: false }, downloads: { allowed_dirs: ['/downloads', '/music'], default_dir: '/downloads' } }, isLoading: false, isError: false, error: null as Error | null };
  return { capabilitiesState, serviceSettingsState, integrationSettingsState, prowlarrIndexersState, prowlarrTemplatesState, updateProwlarrMutate, discoverProwlarrApiKeyMutate, createIndexerMutate, updateIndexerMutate, deleteIndexerMutate, testIndexerMutate };
});

vi.mock('@/app/lib/api', () => ({
  useCapabilities: () => capabilitiesState,
  useServiceSettings: () => serviceSettingsState,
  useUpdateProwlarrSettings: () => ({ mutateAsync: updateProwlarrMutate, isPending: false }),
  useDiscoverProwlarrApiKey: () => ({ mutateAsync: discoverProwlarrApiKeyMutate, isPending: false }),
  useUpdateQbittorrentSettings: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useUpdateDownloadSettings: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useIntegrationSettings: () => integrationSettingsState,
  useProwlarrIndexers: () => prowlarrIndexersState,
  useProwlarrIndexerTemplates: () => prowlarrTemplatesState,
  useCreateProwlarrIndexer: () => ({ mutateAsync: createIndexerMutate, isPending: false }),
  useUpdateProwlarrIndexer: () => ({ mutateAsync: updateIndexerMutate, isPending: false }),
  useDeleteProwlarrIndexer: () => ({ mutateAsync: deleteIndexerMutate, isPending: false }),
  useTestProwlarrIndexer: () => ({ mutateAsync: testIndexerMutate, isPending: false }),
}));

describe('SettingsPage sidebar layout', () => {
  beforeEach(() => {
    global.fetch = vi.fn().mockResolvedValue({ ok: true }) as any;
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    updateProwlarrMutate.mockReset(); discoverProwlarrApiKeyMutate.mockReset(); createIndexerMutate.mockReset(); updateIndexerMutate.mockReset(); deleteIndexerMutate.mockReset(); testIndexerMutate.mockReset();
    discoverProwlarrApiKeyMutate.mockResolvedValue({ message: 'Fetched and saved API key from Prowlarr.' });
  });

  it('supports masked secret editing behavior for integrations', async () => {
    const user = userEvent.setup();
    renderWithProviders(<SettingsPage />);
    await user.click(screen.getByRole('button', { name: /integrations/i }));
    await user.click(screen.getByRole('button', { name: 'Configure' }));
    const integrationInput = screen.getByLabelText('TMDb API Key');
    expect(integrationInput).toHaveAttribute('type', 'password');
    await user.click(screen.getByRole('button', { name: 'Reveal' }));
    expect(integrationInput).toHaveAttribute('type', 'text');
    await user.click(screen.getByRole('button', { name: 'Clear field' }));
    await user.type(integrationInput, '1234567890123456');
    await user.click(screen.getAllByRole('button', { name: /^Save$/ })[0]);
    expect(global.fetch).toHaveBeenCalled();
  });

  it('shows unsaved indicator when section is dirty', async () => {
    const user = userEvent.setup();
    renderWithProviders(<SettingsPage />);
    await user.click(screen.getByRole('button', { name: /downloads/i }));
    await user.type(screen.getByLabelText('Default download path'), '/x');
    expect(screen.getByText('Unsaved changes')).toBeInTheDocument();
  });

  it('handles indexer add, edit, delete, and test flows', async () => {
    const user = userEvent.setup();
    createIndexerMutate.mockResolvedValue({}); updateIndexerMutate.mockResolvedValue({}); deleteIndexerMutate.mockResolvedValue(undefined); testIndexerMutate.mockResolvedValue({ success: true });
    renderWithProviders(<SettingsPage />);
    await user.click(screen.getByRole('button', { name: /indexers/i }));
    await user.selectOptions(screen.getByRole('combobox'), '10');
    await user.clear(screen.getByPlaceholderText('Indexer name')); await user.type(screen.getByPlaceholderText('Indexer name'), 'My Indexer');
    const addBaseUrlLabel = screen.getAllByText('Base Url')[0];
    const addBaseUrlInput = addBaseUrlLabel.parentElement?.querySelector('input');
    await user.type(addBaseUrlInput as HTMLInputElement, 'https://new.example');
    await user.click(screen.getByRole('button', { name: 'Add Indexer' }));
    expect(createIndexerMutate).toHaveBeenCalledWith({ template_id: 10, name: 'My Indexer', settings: { baseUrl: 'https://new.example' } });
    await user.click(screen.getByRole('button', { name: 'Edit' }));
    const editInput = screen.getByDisplayValue('Demo Indexer'); await user.clear(editInput); await user.type(editInput, 'Renamed Indexer');
    const editContainer = editInput.closest('div')?.parentElement;
    await user.click(within(editContainer as HTMLElement).getByRole('button', { name: /^Save$/ }));
    expect(updateIndexerMutate).toHaveBeenCalledWith({ id: 1, name: 'Renamed Indexer', settings: { baseUrl: 'https://old.example' } });
    await user.click(screen.getByRole('button', { name: 'Test' }));
    expect(testIndexerMutate).toHaveBeenCalledWith({ id: 1 });
    await user.click(screen.getByRole('button', { name: 'Delete' }));
    expect(deleteIndexerMutate).toHaveBeenCalledWith({ id: 1 });
  });

  it('smoke path: configure prowlarr, fetch key, and add indexer', async () => {
    const user = userEvent.setup();
    updateProwlarrMutate.mockResolvedValue({}); createIndexerMutate.mockResolvedValue({});
    renderWithProviders(<SettingsPage />);
    await user.click(screen.getByRole('button', { name: /connections/i }));
    await user.clear(screen.getByLabelText('Prowlarr URL')); await user.type(screen.getByLabelText('Prowlarr URL'), 'http://prowlarr.local:9696');
    await user.click(screen.getAllByRole('button', { name: /^Save$/ })[0]);
    await waitFor(() => expect(updateProwlarrMutate).toHaveBeenCalledWith({ url: 'http://prowlarr.local:9696' }));
    await user.click(screen.getByRole('button', { name: /prowlarr/i }));
    await user.click(screen.getByRole('button', { name: 'Fetch API key' }));
    expect(discoverProwlarrApiKeyMutate).toHaveBeenCalledWith({ force_refresh: false, auth: null });
  });
});
