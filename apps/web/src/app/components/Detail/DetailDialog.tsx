import type { ReactNode } from "react";
import { Dialog, DialogContent, DialogFooter } from "@/app/components/ui/dialog";
import { Button } from "@/app/components/ui/button";
import { Skeleton } from "@/app/components/ui/skeleton";
import DetailContent from "@/app/components/Detail/DetailContent";
import { useDetails } from "@/app/lib/api";
import type { MediaKind } from "@/app/lib/types";

interface DetailDialogProps {
  kind: MediaKind;
  id: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function LoadingState() {
  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <Skeleton className="h-7 w-3/4" />
        <Skeleton className="h-4 w-1/2" />
      </div>
      <div className="grid gap-4 md:grid-cols-[2fr_3fr]">
        <Skeleton className="aspect-[2/3] w-full rounded-3xl" />
        <div className="space-y-3">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-5/6" />
          <Skeleton className="h-4 w-2/3" />
        </div>
      </div>
    </div>
  );
}

function ErrorState() {
  return (
    <div className="space-y-2 text-center">
      <p className="text-lg font-semibold text-foreground">Failed to load details.</p>
      <p className="text-sm text-muted-foreground">Please try again later.</p>
    </div>
  );
}

function DetailDialog({ kind, id, open, onOpenChange }: DetailDialogProps) {
  const { data, isLoading, isError } = useDetails(kind, id);

  let content: ReactNode = null;

  if (isLoading) {
    content = <LoadingState />;
  } else if (isError) {
    content = <ErrorState />;
  } else if (data) {
    content = <DetailContent detail={data} />;
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-3xl">
        {content}
        <DialogFooter className="mt-6">
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default DetailDialog;
