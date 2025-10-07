import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SettingsPage from '@/app/routes/settings';
import { renderWithProviders } from '@/app/test-utils';
import type { PluginSettingsSummary } from '@/app/lib/types';

const {
  capabilitiesState,
  toastMock,
  toastSuccess,
  toastError,
  pluginListState,
  pluginValuesState,
  pluginMutationState,
  pluginMutateAsync,
  uploadMutationState,
  uploadMutateAsync,
  installUrlMutationState,
  installUrlMutateAsync,
} =
  vi.hoisted(() => {
    const capabilitiesState = {
      data: { version: '1.2.3', services: { torrent_search: false } },
      isLoading: false,
    };

    const pluginListState = {
      data: [] as PluginSettingsSummary[] | undefined,
      isLoading: false,
      isError: false,
      error: null as Error | null,
    };

    const pluginValuesState = {
      data: { values: {} },
      isLoading: false,
      isFetching: false,
      isError: false,
      error: null as Error | null,
    };

    const pluginMutationState = {
      isPending: false,
    };

    const pluginMutateAsync = vi.fn(async () => {
      pluginMutationState.isPending = true;
      await Promise.resolve();
      pluginMutationState.isPending = false;
      return { values: {} };
    });

    const uploadMutationState = {
      isPending: false,
    };

    const uploadMutateAsync = vi.fn(async () => {
      uploadMutationState.isPending = true;
      await Promise.resolve();
      uploadMutationState.isPending = false;
      return { id: 'plugin.uploaded', version: '1.0.0' };
    });

    const installUrlMutationState = {
      isPending: false,
    };

    const installUrlMutateAsync = vi.fn(async () => {
      installUrlMutationState.isPending = true;
      await Promise.resolve();
      installUrlMutationState.isPending = false;
      return { id: 'plugin.url', version: '1.0.0' };
    });

    const toastSuccess = vi.fn();
    const toastError = vi.fn();
    const toastMock = Object.assign(vi.fn(), {
      success: toastSuccess,
      error: toastError,
    });

    return {
      capabilitiesState,
      toastMock,
      toastSuccess,
      toastError,
      pluginListState,
      pluginValuesState,
      pluginMutationState,
      pluginMutateAsync,
      uploadMutationState,
      uploadMutateAsync,
      installUrlMutationState,
      installUrlMutateAsync,
    };
  });

vi.mock('sonner', () => ({
  toast: toastMock,
}));

vi.mock('@/app/lib/api', () => ({
  useCapabilities: () => capabilitiesState,
  usePluginSettingsList: () => pluginListState,
  usePluginSettings: () => pluginValuesState,
  useUpdatePluginSettings: () => ({
    mutateAsync: pluginMutateAsync,
    isPending: pluginMutationState.isPending,
  }),
  useUploadPlugin: () => ({
    mutateAsync: uploadMutateAsync,
    isPending: uploadMutationState.isPending,
  }),
  useInstallPluginFromUrl: () => ({
    mutateAsync: installUrlMutateAsync,
    isPending: installUrlMutationState.isPending,
  }),
}));

describe('SettingsPage services tab', () => {
  beforeEach(() => {
    toastMock.mockClear();
    toastSuccess.mockClear();
    toastError.mockClear();
    pluginListState.data = [];
    pluginListState.isLoading = false;
    pluginListState.isError = false;
    pluginListState.error = null;
    pluginValuesState.data = { values: {} };
    pluginValuesState.isLoading = false;
    pluginValuesState.isFetching = false;
    pluginValuesState.isError = false;
    pluginValuesState.error = null;
    pluginMutateAsync.mockClear();
    pluginMutationState.isPending = false;
    uploadMutateAsync.mockClear();
    uploadMutationState.isPending = false;
    installUrlMutateAsync.mockClear();
    installUrlMutationState.isPending = false;
    capabilitiesState.data = { version: '1.2.3', services: { torrent_search: false } };
  });

  it('shows metadata banner on the services tab', async () => {
    const user = userEvent.setup();
    renderWithProviders(<SettingsPage />);

    await user.click(screen.getByRole('button', { name: /services/i }));

    expect(
      screen.getByText('Metadata is provided by the built-in Phelia Metadata Service.'),
    ).toBeInTheDocument();
    expect(screen.getByText(/Phelia version 1\.2\.3/)).toBeInTheDocument();
  });

  it('shows plugin installation toolbar when capabilities allow', async () => {
    capabilitiesState.data = {
      version: '1.2.3',
      services: { torrent_search: false },
      plugins: { upload: true, urlInstall: true, phexOnly: true },
    };

    const user = userEvent.setup();
    renderWithProviders(<SettingsPage />);

    await user.click(screen.getByRole('button', { name: /plugins/i }));

    expect(screen.getByRole('button', { name: 'Upload .phex' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Install from URL' })).toBeInTheDocument();
  });
});
