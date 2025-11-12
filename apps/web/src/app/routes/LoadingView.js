import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { Loader2 } from 'lucide-react';
function LoadingView() {
    return (_jsx("div", { className: "flex h-screen items-center justify-center bg-background/80", children: _jsxs("div", { className: "flex items-center gap-3 rounded-full bg-card/40 px-6 py-4 shadow-glow", children: [_jsx(Loader2, { className: "h-6 w-6 animate-spin text-accent" }), _jsx("span", { className: "text-lg font-medium text-foreground", children: "Loading Phelia\u2026" })] }) }));
}
export default LoadingView;
