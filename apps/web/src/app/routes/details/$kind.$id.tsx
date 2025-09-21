import { useMemo } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Button } from '@/app/components/ui/button';
import DetailContent from '@/app/components/Detail/DetailContent';
import { useDetails } from '@/app/lib/api';
import type { MediaKind } from '@/app/lib/types';
import { Skeleton } from '@/app/components/ui/skeleton';

function DetailPage() {
  const params = useParams();
  const navigate = useNavigate();
  const detailId = params.id;

  if (!detailId) {
    return (
      <div className="space-y-4">
        <p className="text-sm text-muted-foreground">Unable to load details.</p>
        <Button variant="ghost" onClick={() => navigate(-1)}>
          Go back
        </Button>
      </div>
    );
  }

  const mappedKind = useMemo<MediaKind>(() => (params.kind === 'music' ? 'album' : (params.kind as MediaKind)), [params.kind]);
  const { data, isLoading, isError } = useDetails(mappedKind, detailId);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-64 w-full rounded-3xl" />
        <Skeleton className="h-6 w-1/3" />
        <Skeleton className="h-4 w-2/3" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="space-y-4">
        <p className="text-sm text-muted-foreground">Unable to load details.</p>
        <Button variant="ghost" onClick={() => navigate(-1)}>
          Go back
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <Button variant="ghost" onClick={() => navigate(-1)} className="rounded-full border border-border/60 px-4">
        ← Back
      </Button>
      <DetailContent detail={data} />
    </div>
  );
}

export default DetailPage;
