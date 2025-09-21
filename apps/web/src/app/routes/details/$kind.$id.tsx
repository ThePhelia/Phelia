import { useEffect, useMemo } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Button } from '@/app/components/ui/button';
import DetailContent from '@/app/components/Detail/DetailContent';
import { useDetails } from '@/app/lib/api';
import type { MediaKind } from '@/app/lib/types';
import { Skeleton } from '@/app/components/ui/skeleton';

function DetailPage() {
  const { kind = 'movie', id } = useParams();
  const navigate = useNavigate();
  const mappedKind = useMemo<MediaKind>(() => (kind === 'music' ? 'album' : (kind as MediaKind)), [kind]);

  useEffect(() => {
    if (!id) navigate(-1);
  }, [id, navigate]);

  if (!id) return null;

  const { data, isLoading, isError } = useDetails(mappedKind, id);

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
