import { useEffect, useRef, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';

import { Badge } from '@/app/components/ui/badge';
import { Button } from '@/app/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/app/components/ui/dialog';
import { Skeleton } from '@/app/components/ui/skeleton';
import { API_BASE } from '@/app/lib/api';

interface MarketPlugin {
  id: string;
  title: string;
  version: string;
  description: string;
  permissions: string[];
  installed: boolean;
  enabled: boolean;
}

interface MarketRegistryEnvelope {
  plugins: MarketPlugin[];
}

interface MarketRequestOptions extends Omit<RequestInit, 'body'> {
  json?: unknown;
}

const API_BASE_WITH_SLASH = API_BASE.endsWith('/') ? API_BASE : `${API_BASE}/`;

async function marketRequest<T>(path: string, options: MarketRequestOptions = {}): Promise<T> {
  const { json, headers, method, ...rest } = options;
  const normalizedPath = path.replace(/^\//, '');
  const url = new URL(normalizedPath, API_BASE_WITH_SLASH);
  const finalHeaders = new Headers(headers);

  let body: BodyInit | undefined;
  const finalMethod = method ?? (json !== undefined ? 'POST' : 'GET');

  if (json !== undefined) {
    if (!finalHeaders.has('Content-Type')) {
      finalHeaders.set('Content-Type', 'application/json');
    }
    body = JSON.stringify(json);
  }

  if (!finalHeaders.has('Accept')) {
    finalHeaders.set('Accept', 'application/json, text/plain;q=0.9, */*;q=0.8');
  }

  const response = await fetch(url.toString(), {
    ...rest,
    method: finalMethod,
    headers: finalHeaders,
    body,
  });

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    try {
      const errorData = await response.clone().json();
      if (errorData && typeof (errorData as { message?: unknown }).message === 'string') {
        message = (errorData as { message: string }).message;
      } else {
        const fallbackText = await response.text();
        if (fallbackText) {
          message = fallbackText;
        }
      }
    } catch {
      try {
        const fallbackText = await response.text();
        if (fallbackText) {
          message = fallbackText;
        }
      } catch {
        // ignore secondary parse failures
      }
    }
    throw new Error(message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const contentType = response.headers.get('content-type') ?? '';
  if (contentType.includes('application/json')) {
    return (await response.json()) as T;
  }

  return (await response.text()) as unknown as T;
}

async function fetchRegistry(): Promise<MarketPlugin[]> {
  const data = await marketRequest<MarketPlugin[] | MarketRegistryEnvelope>('market/registry');

  if (Array.isArray(data)) {
    return data;
  }

  if (data && Array.isArray((data as MarketRegistryEnvelope).plugins)) {
    return (data as MarketRegistryEnvelope).plugins;
  }

  return [];
}

async function fetchPreinstallWarning(): Promise<string> {
  return await marketRequest<string>('market/preinstall_warning');
}

async function installPluginRequest(pluginId: string, acceptedPermissions: string[]): Promise<void> {
  await marketRequest<void>(`market/install/${pluginId}`, {
    method: 'POST',
    json: { accepted_permissions: acceptedPermissions },
  });
}

async function enablePluginRequest(pluginId: string): Promise<void> {
  await marketRequest<void>(`market/enable/${pluginId}`, { method: 'POST' });
}

async function disablePluginRequest(pluginId: string): Promise<void> {
  await marketRequest<void>(`market/disable/${pluginId}`, { method: 'POST' });
}

async function uninstallPluginRequest(pluginId: string): Promise<void> {
  await marketRequest<void>(`market/uninstall/${pluginId}`, { method: 'POST' });
}

function MarketPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['market', 'registry'],
    queryFn: fetchRegistry,
    staleTime: 60_000,
  });
  const [plugins, setPlugins] = useState<MarketPlugin[]>([]);
  const [selectedPlugin, setSelectedPlugin] = useState<MarketPlugin | null>(null);
  const [preinstallWarning, setPreinstallWarning] = useState('');
  const [warningOpen, setWarningOpen] = useState(false);
  const [permissionsOpen, setPermissionsOpen] = useState(false);
  const [permissionSelections, setPermissionSelections] = useState<Record<string, boolean>>({});
  const [finalAcceptance, setFinalAcceptance] = useState(false);
  const [loadingWarningId, setLoadingWarningId] = useState<string | null>(null);
  const [installingPluginId, setInstallingPluginId] = useState<string | null>(null);
  const [actionState, setActionState] = useState<{ id: string; type: 'enable' | 'disable' | 'uninstall' } | null>(null);

  const proceedToPermissionsRef = useRef(false);

  useEffect(() => {
    if (data) {
      setPlugins(data.map((plugin) => ({
        ...plugin,
        permissions: Array.isArray(plugin.permissions) ? plugin.permissions : [],
      })));
    }
  }, [data]);

  const installMutation = useMutation({
    mutationFn: async ({
      pluginId,
      acceptedPermissions,
    }: {
      pluginId: string;
      acceptedPermissions: string[];
    }) => {
      await installPluginRequest(pluginId, acceptedPermissions);
      await enablePluginRequest(pluginId);
    },
    onMutate: ({ pluginId }) => {
      setInstallingPluginId(pluginId);
    },
    onSuccess: (_, { pluginId }) => {
      setPlugins((prev) =>
        prev.map((plugin) =>
          plugin.id === pluginId ? { ...plugin, installed: true, enabled: true } : plugin,
        ),
      );
      toast.success('Plugin installed and enabled');
      setPermissionsOpen(false);
      setSelectedPlugin(null);
      setPermissionSelections({});
      setFinalAcceptance(false);
    },
    onError: (error: unknown) => {
      const message = error instanceof Error ? error.message : 'Failed to install plugin';
      toast.error(message);
    },
    onSettled: () => {
      setInstallingPluginId(null);
    },
  });

  const enableMutation = useMutation({
    mutationFn: (pluginId: string) => enablePluginRequest(pluginId),
    onMutate: (pluginId: string) => {
      setActionState({ id: pluginId, type: 'enable' });
    },
    onSuccess: (_, pluginId) => {
      setPlugins((prev) =>
        prev.map((plugin) =>
          plugin.id === pluginId ? { ...plugin, enabled: true, installed: true } : plugin,
        ),
      );
      toast.success('Plugin enabled');
    },
    onError: (error: unknown) => {
      const message = error instanceof Error ? error.message : 'Failed to enable plugin';
      toast.error(message);
    },
    onSettled: () => {
      setActionState(null);
    },
  });

  const disableMutation = useMutation({
    mutationFn: (pluginId: string) => disablePluginRequest(pluginId),
    onMutate: (pluginId: string) => {
      setActionState({ id: pluginId, type: 'disable' });
    },
    onSuccess: (_, pluginId) => {
      setPlugins((prev) =>
        prev.map((plugin) =>
          plugin.id === pluginId ? { ...plugin, enabled: false } : plugin,
        ),
      );
      toast.success('Plugin disabled');
    },
    onError: (error: unknown) => {
      const message = error instanceof Error ? error.message : 'Failed to disable plugin';
      toast.error(message);
    },
    onSettled: () => {
      setActionState(null);
    },
  });

  const uninstallMutation = useMutation({
    mutationFn: (pluginId: string) => uninstallPluginRequest(pluginId),
    onMutate: (pluginId: string) => {
      setActionState({ id: pluginId, type: 'uninstall' });
    },
    onSuccess: (_, pluginId) => {
      setPlugins((prev) => prev.filter((plugin) => plugin.id !== pluginId));
      toast.success('Plugin uninstalled');
    },
    onError: (error: unknown) => {
      const message = error instanceof Error ? error.message : 'Failed to uninstall plugin';
      toast.error(message);
    },
    onSettled: () => {
      setActionState(null);
    },
  });

  const isActionPending = (pluginId: string, type: 'enable' | 'disable' | 'uninstall') => {
    return actionState?.id === pluginId && actionState?.type === type;
  };

  const handleInstallClick = async (plugin: MarketPlugin) => {
    try {
      setSelectedPlugin(plugin);
      setLoadingWarningId(plugin.id);
      const warning = await fetchPreinstallWarning();
      setPreinstallWarning(warning);
      setWarningOpen(true);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unable to load installation warning.';
      toast.error(message);
      setSelectedPlugin(null);
    } finally {
      setLoadingWarningId(null);
    }
  };

  const handleWarningClose = (open: boolean) => {
    if (open) {
      setWarningOpen(true);
      return;
    }

    setWarningOpen(false);
    if (proceedToPermissionsRef.current) {
      proceedToPermissionsRef.current = false;
      return;
    }

    setSelectedPlugin(null);
    setPreinstallWarning('');
  };

  const handlePermissionsClose = (open: boolean) => {
    if (open) {
      setPermissionsOpen(true);
      return;
    }

    if (installMutation.isPending) {
      return;
    }

    setPermissionsOpen(false);
    setPermissionSelections({});
    setFinalAcceptance(false);
    setSelectedPlugin(null);
  };

  const handleProceedToPermissions = () => {
    if (!selectedPlugin) return;

    const selections: Record<string, boolean> = {};
    selectedPlugin.permissions.forEach((permission) => {
      selections[permission] = true;
    });

    setPermissionSelections(selections);
    setFinalAcceptance(false);
    proceedToPermissionsRef.current = true;
    setWarningOpen(false);
    setPermissionsOpen(true);
  };

  const handleConfirmInstallation = () => {
    if (!selectedPlugin) {
      return;
    }

    const acceptedPermissions = selectedPlugin.permissions.filter(
      (permission) => permissionSelections[permission],
    );

    installMutation.mutate({
      pluginId: selectedPlugin.id,
      acceptedPermissions,
    });
  };

  return (
    <div className="space-y-10">
      <div>
        <h1 className="text-3xl font-semibold text-foreground">Marketplace</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Browse, install, and manage plugins to extend your experience.
        </p>
      </div>
      {isLoading ? (
        <div className="space-y-6">
          <Skeleton className="h-10 w-1/3 rounded-full" />
          <div className="grid gap-6 md:grid-cols-2">
            {Array.from({ length: 4 }).map((_, index) => (
              <Skeleton key={index} className="h-48 w-full rounded-3xl" />
            ))}
          </div>
        </div>
      ) : isError ? (
        <p className="text-sm text-muted-foreground">Unable to load marketplace.</p>
      ) : !plugins.length ? (
        <p className="text-sm text-muted-foreground">No plugins available right now.</p>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
          {plugins.map((plugin) => {
            const installing = installingPluginId === plugin.id;
            const loadingWarning = loadingWarningId === plugin.id;
            const disablePending = isActionPending(plugin.id, 'disable');
            const enablePending = isActionPending(plugin.id, 'enable');
            const uninstallPending = isActionPending(plugin.id, 'uninstall');
            const actionInProgress =
              installing || loadingWarning || disablePending || enablePending || uninstallPending;

            return (
              <div
                key={plugin.id}
                className="flex h-full flex-col justify-between rounded-3xl border border-border/60 bg-background/60 p-6 shadow-sm"
              >
                <div className="space-y-4">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <h2 className="text-xl font-semibold text-foreground">{plugin.title}</h2>
                      <p className="text-xs uppercase tracking-wider text-muted-foreground">Version {plugin.version}</p>
                    </div>
                    <Badge variant="accent">
                      {plugin.permissions.length}{' '}
                      {plugin.permissions.length === 1 ? 'permission' : 'permissions'}
                    </Badge>
                  </div>
                  <p className="text-sm leading-relaxed text-muted-foreground">{plugin.description}</p>
                </div>
                <div className="mt-6 flex flex-wrap gap-2">
                  {!plugin.installed ? (
                    <Button
                      type="button"
                      onClick={() => void handleInstallClick(plugin)}
                      disabled={loadingWarning || installing}
                    >
                      {(loadingWarning || installing) ? (
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      ) : null}
                      Install
                    </Button>
                  ) : (
                    <>
                      <Button type="button" variant="secondary" disabled>
                        Installed
                      </Button>
                      {plugin.enabled ? (
                        <Button
                          type="button"
                          variant="outline"
                          onClick={() => disableMutation.mutate(plugin.id)}
                          disabled={disablePending || actionInProgress}
                        >
                          {disablePending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                          Disable
                        </Button>
                      ) : (
                        <Button
                          type="button"
                          variant="outline"
                          onClick={() => enableMutation.mutate(plugin.id)}
                          disabled={enablePending || actionInProgress}
                        >
                          {enablePending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                          Enable
                        </Button>
                      )}
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() => uninstallMutation.mutate(plugin.id)}
                        disabled={uninstallPending || installing}
                      >
                        {uninstallPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                        Uninstall
                      </Button>
                    </>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <Dialog open={warningOpen} onOpenChange={handleWarningClose}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle>Install {selectedPlugin?.title}</DialogTitle>
            <DialogDescription className="whitespace-pre-line text-left text-sm leading-relaxed text-muted-foreground">
              {preinstallWarning}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => handleWarningClose(false)}
            >
              Cancel
            </Button>
            <Button type="button" onClick={handleProceedToPermissions}>
              Install plugin
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={permissionsOpen} onOpenChange={handlePermissionsClose}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle>Permissions</DialogTitle>
            <DialogDescription className="text-left text-sm leading-relaxed text-muted-foreground">
              Review and accept the requested permissions before completing the installation.
            </DialogDescription>
          </DialogHeader>
          <div className="px-8 pb-6">
            {selectedPlugin?.permissions.length ? (
              <ul className="space-y-3">
                {selectedPlugin.permissions.map((permission) => (
                  <li key={permission} className="flex items-start gap-3">
                    <input
                      type="checkbox"
                      id={`permission-${permission}`}
                      className="mt-1 h-4 w-4 rounded border-border text-foreground focus:ring-2 focus:ring-[color:var(--accent)]"
                      checked={Boolean(permissionSelections[permission])}
                      onChange={() =>
                        setPermissionSelections((current) => ({
                          ...current,
                          [permission]: !current[permission],
                        }))
                      }
                    />
                    <label htmlFor={`permission-${permission}`} className="text-sm leading-relaxed text-foreground">
                      {permission}
                    </label>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground">This plugin does not request any permissions.</p>
            )}
            <label className="mt-6 flex items-start gap-3">
              <input
                type="checkbox"
                className="mt-1 h-4 w-4 rounded border-border text-foreground focus:ring-2 focus:ring-[color:var(--accent)]"
                checked={finalAcceptance}
                onChange={(event) => setFinalAcceptance(event.target.checked)}
              />
              <span className="text-sm leading-relaxed text-foreground">I accept the requested permissions</span>
            </label>
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => handlePermissionsClose(false)}
              disabled={installMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              type="button"
              onClick={handleConfirmInstallation}
              disabled={!finalAcceptance || installMutation.isPending}
            >
              {installMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : null}
              Confirm installation
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default MarketPage;
