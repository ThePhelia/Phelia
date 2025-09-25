import clsx from 'clsx';
import { Loader2, Pause as PauseIcon, Play, Trash2 } from 'lucide-react';
import { useCallback } from 'react';

import { Button } from '@/app/components/ui/button';
import {
  useDeleteDownload,
  usePauseDownload,
  useResumeDownload,
} from '@/app/lib/api';
import type { DownloadItem } from '@/app/lib/types';
import { isDownloadPaused } from '@/app/lib/downloads';

interface DownloadActionsProps {
  item: DownloadItem;
  size?: 'icon' | 'sm';
  className?: string;
}

function DownloadActions({ item, size = 'icon', className }: DownloadActionsProps) {
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

    void deleteMutation
      .mutateAsync({ id: item.id })
      .catch((error) => {
        console.error('Failed to delete download', error);
      });
  }, [deleteMutation, item?.id]);

  return (
    <div className={clsx('flex items-center gap-2', className)}>
      <Button
        type="button"
        size={size}
        variant="ghost"
        disabled={isBusy}
        onClick={handlePauseResume}
        aria-label={isPaused ? 'Resume download' : 'Pause download'}
      >
        {pauseMutation.isPending || resumeMutation.isPending ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : isPaused ? (
          <Play className="h-4 w-4" />
        ) : (
          <PauseIcon className="h-4 w-4" />
        )}
      </Button>
      <Button
        type="button"
        size={size}
        variant="ghost"
        disabled={isBusy}
        onClick={handleDelete}
        aria-label="Delete download"
      >
        {deleteMutation.isPending ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <Trash2 className="h-4 w-4" />
        )}
      </Button>
    </div>
  );
}

export default DownloadActions;
