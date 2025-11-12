import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import clsx from 'clsx';
import { Loader2, Pause as PauseIcon, Play, Trash2 } from 'lucide-react';
import { useCallback } from 'react';
import { Button } from '@/app/components/ui/button';
import { useDeleteDownload, usePauseDownload, useResumeDownload, } from '@/app/lib/api';
import { isDownloadPaused } from '@/app/lib/downloads';
function DownloadActions({ item, size = 'icon', className }) {
    const pauseMutation = usePauseDownload();
    const resumeMutation = useResumeDownload();
    const deleteMutation = useDeleteDownload();
    const isPaused = isDownloadPaused(item.status);
    const isBusy = pauseMutation.isPending || resumeMutation.isPending || deleteMutation.isPending;
    const handlePauseResume = useCallback(() => {
        if (!item?.id) {
            return;
        }
        const action = isPaused ? resumeMutation.mutateAsync : pauseMutation.mutateAsync;
        void action(item.id).catch((error) => {
            console.error('Failed to toggle download state', error);
        });
    }, [isPaused, item?.id, pauseMutation.mutateAsync, resumeMutation.mutateAsync]);
    const handleDelete = useCallback(() => {
        if (!item?.id) {
            return;
        }
        const confirmed = window.confirm('Remove this download from the client?');
        if (!confirmed) {
            return;
        }
        void deleteMutation
            .mutateAsync({ id: item.id })
            .catch((error) => {
            console.error('Failed to delete download', error);
        });
    }, [deleteMutation, item?.id]);
    return (_jsxs("div", { className: clsx('flex items-center gap-2', className), children: [_jsx(Button, { type: "button", size: size, variant: "ghost", disabled: isBusy, onClick: handlePauseResume, "aria-label": isPaused ? 'Resume download' : 'Pause download', children: pauseMutation.isPending || resumeMutation.isPending ? (_jsx(Loader2, { className: "h-4 w-4 animate-spin" })) : isPaused ? (_jsx(Play, { className: "h-4 w-4" })) : (_jsx(PauseIcon, { className: "h-4 w-4" })) }), _jsx(Button, { type: "button", size: size, variant: "ghost", disabled: isBusy, onClick: handleDelete, "aria-label": "Delete download", children: deleteMutation.isPending ? (_jsx(Loader2, { className: "h-4 w-4 animate-spin" })) : (_jsx(Trash2, { className: "h-4 w-4" })) })] }));
}
export default DownloadActions;
