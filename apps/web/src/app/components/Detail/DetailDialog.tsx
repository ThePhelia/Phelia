import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

type MediaItem = {
  id: string | number;
  title: string;
  subtitle?: string;
  year?: string | number;
  coverUrl?: string;
  description?: string;
};

type DetailDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  item: MediaItem | null;
  onPrimary?: (item: MediaItem) => void;
  primaryLabel?: string;
};

export function DetailDialog({
  open,
  onOpenChange,
  item,
  onPrimary,
  primaryLabel = "Add",
}: DetailDialogProps) {
  if (!item) {
    return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Nothing selected</DialogTitle>
            <DialogDescription>Select an item to see details.</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="secondary" onClick={() => onOpenChange(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="line-clamp-2">{item.title}</DialogTitle>
          {item.subtitle ? (
            <DialogDescription className="line-clamp-2">
              {item.subtitle}
              {item.year ? ` • ${item.year}` : ""}
            </DialogDescription>
          ) : item.year ? (
            <DialogDescription>{item.year}</DialogDescription>
          ) : null}
        </DialogHeader>

        <div className="mt-3 grid grid-cols-3 gap-4">
          <div className="col-span-1">
            {item.coverUrl ? (
              <img
                src={item.coverUrl}
                alt={item.title}
                className="w-full rounded-xl object-cover"
              />
            ) : (
              <div className="aspect-square w-full rounded-xl border" />
            )}
          </div>
          <div className="col-span-2">
            <p className="text-sm leading-relaxed whitespace-pre-line">
              {item.description ?? "No description available."}
            </p>
          </div>
        </div>

        <DialogFooter className="mt-4">
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Close
          </Button>
          {onPrimary ? (
            <Button onClick={() => onPrimary(item)}>{primaryLabel}</Button>
          ) : null}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default DetailDialog;

