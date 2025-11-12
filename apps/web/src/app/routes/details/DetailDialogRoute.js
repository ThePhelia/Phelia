import { jsx as _jsx } from "react/jsx-runtime";
import { useEffect } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import DetailDialog from "@/app/components/Detail/DetailDialog";
function DetailDialogRoute() {
    const { kind = "movie", id } = useParams();
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    useEffect(() => {
        if (!id)
            navigate(-1);
    }, [id, navigate]);
    if (!id)
        return null;
    const mappedKind = kind === "music" ? "album" : kind;
    return (_jsx(DetailDialog, { kind: mappedKind, id: id, provider: searchParams.get("provider") ?? undefined, open: true, onOpenChange: (open) => {
            if (!open)
                navigate(-1);
        } }));
}
export default DetailDialogRoute;
