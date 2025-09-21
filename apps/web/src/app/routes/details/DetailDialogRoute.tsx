import { useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import DetailDialog from "@/app/components/Detail/DetailDialog";
import type { MediaKind } from "@/app/lib/types";

function DetailDialogRoute() {
  const { kind = "movie", id } = useParams();
  const navigate = useNavigate();

  useEffect(() => {
    if (!id) navigate(-1);
  }, [id, navigate]);

  if (!id) return null;

  const mappedKind: MediaKind = kind === "music" ? "album" : (kind as MediaKind);

  return (
    <DetailDialog
      kind={mappedKind}
      id={id}
      open
      onOpenChange={(open) => {
        if (!open) navigate(-1);
      }}
    />
  );
}

export default DetailDialogRoute;
