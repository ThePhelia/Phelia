import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useEffect, useRef, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Badge } from '@/app/components/ui/badge';
import { Button } from '@/app/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, } from '@/app/components/ui/dialog';
import { Skeleton } from '@/app/components/ui/skeleton';
import { API_BASE } from '@/app/lib/api';
const API_BASE_WITH_SLASH = API_BASE.endsWith('/') ? API_BASE : `${API_BASE}/`;
async function marketRequest(path, options = {}) {
    const { json, headers, method, ...rest } = options;
    const normalizedPath = path.replace(/^\//, '');
    const url = new URL(normalizedPath, API_BASE_WITH_SLASH);
    const finalHeaders = new Headers(headers);
    let body;
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
            if (errorData && typeof errorData.message === 'string') {
                message = errorData.message;
            }
            else {
                const fallbackText = await response.text();
                if (fallbackText) {
                    message = fallbackText;
                }
            }
        }
        catch {
            try {
                const fallbackText = await response.text();
                if (fallbackText) {
                    message = fallbackText;
                }
            }
            catch {
                // ignore secondary parse failures
            }
        }
        throw new Error(message);
    }
    if (response.status === 204) {
        return undefined;
    }
    const contentType = response.headers.get('content-type') ?? '';
    if (contentType.includes('application/json')) {
        return (await response.json());
    }
    return (await response.text());
}
async function fetchRegistry() {
    const data = await marketRequest('market/registry');
    if (Array.isArray(data)) {
        return data;
    }
    if (data && Array.isArray(data.plugins)) {
        return data.plugins;
    }
    return [];
}
async function fetchPreinstallWarning() {
    return await marketRequest('market/preinstall_warning');
}
async function installPluginRequest(pluginId, acceptedPermissions) {
    await marketRequest(`market/install/${pluginId}`, {
        method: 'POST',
        json: { accepted_permissions: acceptedPermissions },
    });
}
async function enablePluginRequest(pluginId) {
    await marketRequest(`market/enable/${pluginId}`, { method: 'POST' });
}
async function disablePluginRequest(pluginId) {
    await marketRequest(`market/disable/${pluginId}`, { method: 'POST' });
}
async function uninstallPluginRequest(pluginId) {
    await marketRequest(`market/uninstall/${pluginId}`, { method: 'POST' });
}
function MarketPage() {
    const { data, isLoading, isError } = useQuery({
        queryKey: ['market', 'registry'],
        queryFn: fetchRegistry,
        staleTime: 60000,
    });
    const [plugins, setPlugins] = useState([]);
    const [selectedPlugin, setSelectedPlugin] = useState(null);
    const [preinstallWarning, setPreinstallWarning] = useState('');
    const [warningOpen, setWarningOpen] = useState(false);
    const [permissionsOpen, setPermissionsOpen] = useState(false);
    const [permissionSelections, setPermissionSelections] = useState({});
    const [finalAcceptance, setFinalAcceptance] = useState(false);
    const [loadingWarningId, setLoadingWarningId] = useState(null);
    const [installingPluginId, setInstallingPluginId] = useState(null);
    const [actionState, setActionState] = useState(null);
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
        mutationFn: async ({ pluginId, acceptedPermissions, }) => {
            await installPluginRequest(pluginId, acceptedPermissions);
            await enablePluginRequest(pluginId);
        },
        onMutate: ({ pluginId }) => {
            setInstallingPluginId(pluginId);
        },
        onSuccess: (_, { pluginId }) => {
            setPlugins((prev) => prev.map((plugin) => plugin.id === pluginId ? { ...plugin, installed: true, enabled: true } : plugin));
            toast.success('Plugin installed and enabled');
            setPermissionsOpen(false);
            setSelectedPlugin(null);
            setPermissionSelections({});
            setFinalAcceptance(false);
        },
        onError: (error) => {
            const message = error instanceof Error ? error.message : 'Failed to install plugin';
            toast.error(message);
        },
        onSettled: () => {
            setInstallingPluginId(null);
        },
    });
    const enableMutation = useMutation({
        mutationFn: (pluginId) => enablePluginRequest(pluginId),
        onMutate: (pluginId) => {
            setActionState({ id: pluginId, type: 'enable' });
        },
        onSuccess: (_, pluginId) => {
            setPlugins((prev) => prev.map((plugin) => plugin.id === pluginId ? { ...plugin, enabled: true, installed: true } : plugin));
            toast.success('Plugin enabled');
        },
        onError: (error) => {
            const message = error instanceof Error ? error.message : 'Failed to enable plugin';
            toast.error(message);
        },
        onSettled: () => {
            setActionState(null);
        },
    });
    const disableMutation = useMutation({
        mutationFn: (pluginId) => disablePluginRequest(pluginId),
        onMutate: (pluginId) => {
            setActionState({ id: pluginId, type: 'disable' });
        },
        onSuccess: (_, pluginId) => {
            setPlugins((prev) => prev.map((plugin) => plugin.id === pluginId ? { ...plugin, enabled: false } : plugin));
            toast.success('Plugin disabled');
        },
        onError: (error) => {
            const message = error instanceof Error ? error.message : 'Failed to disable plugin';
            toast.error(message);
        },
        onSettled: () => {
            setActionState(null);
        },
    });
    const uninstallMutation = useMutation({
        mutationFn: (pluginId) => uninstallPluginRequest(pluginId),
        onMutate: (pluginId) => {
            setActionState({ id: pluginId, type: 'uninstall' });
        },
        onSuccess: (_, pluginId) => {
            setPlugins((prev) => prev.filter((plugin) => plugin.id !== pluginId));
            toast.success('Plugin uninstalled');
        },
        onError: (error) => {
            const message = error instanceof Error ? error.message : 'Failed to uninstall plugin';
            toast.error(message);
        },
        onSettled: () => {
            setActionState(null);
        },
    });
    const isActionPending = (pluginId, type) => {
        return actionState?.id === pluginId && actionState?.type === type;
    };
    const handleInstallClick = async (plugin) => {
        try {
            setSelectedPlugin(plugin);
            setLoadingWarningId(plugin.id);
            const warning = await fetchPreinstallWarning();
            setPreinstallWarning(warning);
            setWarningOpen(true);
        }
        catch (error) {
            const message = error instanceof Error ? error.message : 'Unable to load installation warning.';
            toast.error(message);
            setSelectedPlugin(null);
        }
        finally {
            setLoadingWarningId(null);
        }
    };
    const handleWarningClose = (open) => {
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
    const handlePermissionsClose = (open) => {
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
        if (!selectedPlugin)
            return;
        const selections = {};
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
        const acceptedPermissions = selectedPlugin.permissions.filter((permission) => permissionSelections[permission]);
        installMutation.mutate({
            pluginId: selectedPlugin.id,
            acceptedPermissions,
        });
    };
    return (_jsxs("div", { className: "space-y-10", children: [_jsxs("div", { children: [_jsx("h1", { className: "text-3xl font-semibold text-foreground", children: "Marketplace" }), _jsx("p", { className: "mt-2 text-sm text-muted-foreground", children: "Browse, install, and manage plugins to extend your experience." })] }), isLoading ? (_jsxs("div", { className: "space-y-6", children: [_jsx(Skeleton, { className: "h-10 w-1/3 rounded-full" }), _jsx("div", { className: "grid gap-6 md:grid-cols-2", children: Array.from({ length: 4 }).map((_, index) => (_jsx(Skeleton, { className: "h-48 w-full rounded-3xl" }, index))) })] })) : isError ? (_jsx("p", { className: "text-sm text-muted-foreground", children: "Unable to load marketplace." })) : !plugins.length ? (_jsx("p", { className: "text-sm text-muted-foreground", children: "No plugins available right now." })) : (_jsx("div", { className: "grid gap-6 md:grid-cols-2 xl:grid-cols-3", children: plugins.map((plugin) => {
                    const installing = installingPluginId === plugin.id;
                    const loadingWarning = loadingWarningId === plugin.id;
                    const disablePending = isActionPending(plugin.id, 'disable');
                    const enablePending = isActionPending(plugin.id, 'enable');
                    const uninstallPending = isActionPending(plugin.id, 'uninstall');
                    const actionInProgress = installing || loadingWarning || disablePending || enablePending || uninstallPending;
                    return (_jsxs("div", { className: "flex h-full flex-col justify-between rounded-3xl border border-border/60 bg-background/60 p-6 shadow-sm", children: [_jsxs("div", { className: "space-y-4", children: [_jsxs("div", { className: "flex items-start justify-between gap-4", children: [_jsxs("div", { children: [_jsx("h2", { className: "text-xl font-semibold text-foreground", children: plugin.title }), _jsxs("p", { className: "text-xs uppercase tracking-wider text-muted-foreground", children: ["Version ", plugin.version] })] }), _jsxs(Badge, { variant: "accent", children: [plugin.permissions.length, ' ', plugin.permissions.length === 1 ? 'permission' : 'permissions'] })] }), _jsx("p", { className: "text-sm leading-relaxed text-muted-foreground", children: plugin.description })] }), _jsx("div", { className: "mt-6 flex flex-wrap gap-2", children: !plugin.installed ? (_jsxs(Button, { type: "button", onClick: () => void handleInstallClick(plugin), disabled: loadingWarning || installing, children: [(loadingWarning || installing) ? (_jsx(Loader2, { className: "mr-2 h-4 w-4 animate-spin" })) : null, "Install"] })) : (_jsxs(_Fragment, { children: [_jsx(Button, { type: "button", variant: "secondary", disabled: true, children: "Installed" }), plugin.enabled ? (_jsxs(Button, { type: "button", variant: "outline", onClick: () => disableMutation.mutate(plugin.id), disabled: disablePending || actionInProgress, children: [disablePending ? _jsx(Loader2, { className: "mr-2 h-4 w-4 animate-spin" }) : null, "Disable"] })) : (_jsxs(Button, { type: "button", variant: "outline", onClick: () => enableMutation.mutate(plugin.id), disabled: enablePending || actionInProgress, children: [enablePending ? _jsx(Loader2, { className: "mr-2 h-4 w-4 animate-spin" }) : null, "Enable"] })), _jsxs(Button, { type: "button", variant: "outline", onClick: () => uninstallMutation.mutate(plugin.id), disabled: uninstallPending || installing, children: [uninstallPending ? _jsx(Loader2, { className: "mr-2 h-4 w-4 animate-spin" }) : null, "Uninstall"] })] })) })] }, plugin.id));
                }) })), _jsx(Dialog, { open: warningOpen, onOpenChange: handleWarningClose, children: _jsxs(DialogContent, { className: "max-w-xl", children: [_jsxs(DialogHeader, { children: [_jsxs(DialogTitle, { children: ["Install ", selectedPlugin?.title] }), _jsx(DialogDescription, { className: "whitespace-pre-line text-left text-sm leading-relaxed text-muted-foreground", children: preinstallWarning })] }), _jsxs(DialogFooter, { children: [_jsx(Button, { type: "button", variant: "outline", onClick: () => handleWarningClose(false), children: "Cancel" }), _jsx(Button, { type: "button", onClick: handleProceedToPermissions, children: "Install plugin" })] })] }) }), _jsx(Dialog, { open: permissionsOpen, onOpenChange: handlePermissionsClose, children: _jsxs(DialogContent, { className: "max-w-xl", children: [_jsxs(DialogHeader, { children: [_jsx(DialogTitle, { children: "Permissions" }), _jsx(DialogDescription, { className: "text-left text-sm leading-relaxed text-muted-foreground", children: "Review and accept the requested permissions before completing the installation." })] }), _jsxs("div", { className: "px-8 pb-6", children: [selectedPlugin?.permissions.length ? (_jsx("ul", { className: "space-y-3", children: selectedPlugin.permissions.map((permission) => (_jsxs("li", { className: "flex items-start gap-3", children: [_jsx("input", { type: "checkbox", id: `permission-${permission}`, className: "mt-1 h-4 w-4 rounded border-border text-foreground focus:ring-2 focus:ring-[color:var(--accent)]", checked: Boolean(permissionSelections[permission]), onChange: () => setPermissionSelections((current) => ({
                                                    ...current,
                                                    [permission]: !current[permission],
                                                })) }), _jsx("label", { htmlFor: `permission-${permission}`, className: "text-sm leading-relaxed text-foreground", children: permission })] }, permission))) })) : (_jsx("p", { className: "text-sm text-muted-foreground", children: "This plugin does not request any permissions." })), _jsxs("label", { className: "mt-6 flex items-start gap-3", children: [_jsx("input", { type: "checkbox", className: "mt-1 h-4 w-4 rounded border-border text-foreground focus:ring-2 focus:ring-[color:var(--accent)]", checked: finalAcceptance, onChange: (event) => setFinalAcceptance(event.target.checked) }), _jsx("span", { className: "text-sm leading-relaxed text-foreground", children: "I accept the requested permissions" })] })] }), _jsxs(DialogFooter, { children: [_jsx(Button, { type: "button", variant: "outline", onClick: () => handlePermissionsClose(false), disabled: installMutation.isPending, children: "Cancel" }), _jsxs(Button, { type: "button", onClick: handleConfirmInstallation, disabled: !finalAcceptance || installMutation.isPending, children: [installMutation.isPending ? (_jsx(Loader2, { className: "mr-2 h-4 w-4 animate-spin" })) : null, "Confirm installation"] })] })] }) })] }));
}
export default MarketPage;
