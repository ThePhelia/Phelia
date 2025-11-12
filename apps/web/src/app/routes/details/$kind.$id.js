import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useMemo } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Button } from '@/app/components/ui/button';
import DetailContent from '@/app/components/Detail/DetailContent';
import { useDetails } from '@/app/lib/api';
import { Skeleton } from '@/app/components/ui/skeleton';
function DetailPage() {
    const { kind = 'movie', id } = useParams();
    const navigate = useNavigate();
    const mappedKind = useMemo(() => (kind === 'music' ? 'album' : kind), [kind]);
    useEffect(() => {
        if (!id)
            navigate(-1);
    }, [id, navigate]);
    if (!id)
        return null;
    const { data, isLoading, isError } = useDetails(mappedKind, id);
    if (isLoading) {
        return (_jsxs("div", { className: "space-y-6", children: [_jsx(Skeleton, { className: "h-64 w-full rounded-3xl" }), _jsx(Skeleton, { className: "h-6 w-1/3" }), _jsx(Skeleton, { className: "h-4 w-2/3" })] }));
    }
    if (isError || !data) {
        return (_jsxs("div", { className: "space-y-4", children: [_jsx("p", { className: "text-sm text-muted-foreground", children: "Unable to load details." }), _jsx(Button, { variant: "ghost", onClick: () => navigate(-1), children: "Go back" })] }));
    }
    return (_jsxs("div", { className: "space-y-8", children: [_jsx(Button, { variant: "ghost", onClick: () => navigate(-1), className: "rounded-full border border-border/60 px-4", children: "\u2190 Back" }), _jsx(DetailContent, { detail: data })] }));
}
export default DetailPage;
