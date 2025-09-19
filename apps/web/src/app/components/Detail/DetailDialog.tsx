import { Dialog, DialogContent } from '@/app/components/ui/dialog';
import { useDetails } from '@/app/lib/api';
import type { MediaKind } from '@/app/lib/types';
import { Skeleton } from '@/app/components/ui/skeleton';
import DetailContent from '@/app/components/Detail/DetailContent';

interface DetailDialogProps {
  kind: MediaKind;
  id?: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function DetailDialog({ kind, id, open, onOpenChange }: DetailDialogProps) {
  const { data, isLoading, isError } = useDetails(kind, id);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[95vh] overflow-y-auto bg-background/95">
        {isLoading ? (
          <div className="space-y-6 p-8">
            <Skeleton className="h-64 w-full rounded-3xl" />
            <Skeleton className="h-6 w-1/3" />
            <Skeleton className="h-4 w-2/3" />
          </div>
        ) : isError || !data ? (
          <div className="p-8 text-sm text-muted-foreground">Failed to load details.</div>
        ) : (
          <div className="space-y-8 p-8">
            <DetailContent detail={data} />
          </div>
        )
      </DialogContent>
    </Dialog>
  );
}

export default DetailDialog;
