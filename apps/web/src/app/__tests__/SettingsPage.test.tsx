import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SettingsPage from '@/app/routes/settings';
import { renderWithProviders } from '@/app/test-utils';
import type {
  ProviderSettingMutationVariables,
  ProviderSettingStatus,
} from '@/app/lib/types';

const { providerQueryState, capabilitiesState, mutationState, mutateAsync, toastMock, toastSuccess, toastError } =
  vi.hoisted(() => {
    const providerQueryState = {
      data: [] as ProviderSettingStatus[] | undefined,
      isLoading: false,
      isError: false,
      error: null as Error | null,
      isFetching: false,
    };

    const capabilitiesState = {
      data: { version: '1.2.3', jackettUrl: 'http://jackett.local' },
      isLoading: false,
    };

    const mutationState = {
      isPending: false,
      variables: undefined as ProviderSettingMutationVariables | undefined,
    };

    const mutateAsync = vi.fn(async (variables: ProviderSettingMutationVariables) => {
      mutationState.isPending = true;
      mutationState.variables = variables;
      await Promise.resolve();
      mutationState.isPending = false;
      return { provider: variables.provider, configured: Boolean(variables.api_key) } as ProviderSettingStatus;
    });

    const toastSuccess = vi.fn();
    const toastError = vi.fn();
    const toastMock = Object.assign(vi.fn(), {
      success: toastSuccess,
      error: toastError,
    });

    return { providerQueryState, capabilitiesState, mutationState, mutateAsync, toastMock, toastSuccess, toastError };
  });

vi.mock('sonner', () => ({
  toast: toastMock,
}));

vi.mock('@/app/lib/api', () => ({
  useCapabilities: () => capabilitiesState,
  useProviderSettings: () => providerQueryState,
  useUpdateProviderSetting: () => ({
    mutateAsync,
    isPending: mutationState.isPending,
    variables: mutationState.variables,
  }),
}));

describe('SettingsPage services tab', () => {
  beforeEach(() => {
    mutateAsync.mockClear();
    toastMock.mockClear();
    toastSuccess.mockClear();
    toastError.mockClear();
    mutationState.isPending = false;
    mutationState.variables = undefined;
    providerQueryState.isLoading = false;
    providerQueryState.isError = false;
    providerQueryState.error = null;
    providerQueryState.data = [];
  });

  it('renders provider guidance links', async () => {
    providerQueryState.data = [
      { provider: 'tmdb', configured: true, preview: '****abcd' },
      { provider: 'discogs', configured: false, preview: null },
      { provider: 'listenbrainz', configured: false, preview: null },
      { provider: 'spotify_client_id', configured: false, preview: null },
      { provider: 'spotify_client_secret', configured: true, preview: '••••' },
    ];

    const user = userEvent.setup();
    renderWithProviders(<SettingsPage />);

    await user.click(screen.getByRole('button', { name: /services/i }));

    expect(screen.getByText('TMDb API key:', { exact: false })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'https://www.themoviedb.org/settings/api' })).toHaveAttribute(
      'href',
      'https://www.themoviedb.org/settings/api',
    );
    expect(screen.getByText('Discogs personal token:', { exact: false })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'https://www.discogs.com/settings/developers' })).toHaveAttribute(
      'href',
      'https://www.discogs.com/settings/developers',
    );
    expect(screen.getByText('ListenBrainz token:', { exact: false })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'https://listenbrainz.org/settings/' })).toHaveAttribute(
      'href',
      'https://listenbrainz.org/settings/',
    );
    expect(screen.getAllByText('Spotify Developer Dashboard:', { exact: false })).toHaveLength(2);
  });

  it('submits a provider key via the mutation hook', async () => {
    providerQueryState.data = [{ provider: 'tmdb', configured: false }];

    const user = userEvent.setup();
    renderWithProviders(<SettingsPage />);

    await user.click(screen.getByRole('button', { name: /services/i }));

    const input = screen.getByRole('textbox', { name: /tmdb api key/i });
    await user.clear(input);
    await user.type(input, 'abcd1234');

    await user.click(screen.getByRole('button', { name: /save tmdb api key/i }));

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith({ provider: 'tmdb', api_key: 'abcd1234' });
    });

    const result = await mutateAsync.mock.results.at(-1)?.value;
    expect(result).toEqual({ provider: 'tmdb', configured: true });
    expect(toastSuccess).toHaveBeenCalledWith('TMDb API key saved.');
    expect(toastError).not.toHaveBeenCalled();
  });

  it('handles Spotify client credentials independently', async () => {
    providerQueryState.data = [
      { provider: 'spotify_client_id', configured: false, preview: null },
      { provider: 'spotify_client_secret', configured: true, preview: '••••••' },
    ];

    const user = userEvent.setup();
    renderWithProviders(<SettingsPage />);

    await user.click(screen.getByRole('button', { name: /services/i }));

    const clientIdInput = screen.getByRole('textbox', { name: /spotify client id/i });
    await user.clear(clientIdInput);
    await user.type(clientIdInput, 'spotify-client-id');

    await user.click(screen.getByRole('button', { name: /save spotify client id/i }));

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith({ provider: 'spotify_client_id', api_key: 'spotify-client-id' });
    });
    expect(toastSuccess).toHaveBeenCalledWith('Spotify Client ID saved.');

    const clientSecretInput = screen.getByRole('textbox', { name: /spotify client secret/i });
    await user.clear(clientSecretInput);

    await user.click(screen.getByRole('button', { name: /save spotify client secret/i }));

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith({ provider: 'spotify_client_secret', api_key: null });
    });
    expect(toastSuccess).toHaveBeenCalledWith('Spotify Client Secret cleared.');
    expect(toastError).not.toHaveBeenCalled();
  });
});
