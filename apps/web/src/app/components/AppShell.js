import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { Outlet } from 'react-router-dom';
import { cn } from '@/app/utils/cn';
import Header from '@/app/components/Header';
import Sidebar from '@/app/components/Sidebar';
import CommandPalette from '@/app/components/CommandPalette';
import DownloadsDrawer from '@/app/components/DownloadsDrawer';
import TorrentSearchDialog from '@/app/components/TorrentSearchDialog';
import { useUiState } from '@/app/stores/ui';
function AppShell() {
    const sidebarCollapsed = useUiState((state) => state.sidebarCollapsed);
    return (_jsxs("div", { className: "flex min-h-screen bg-background", children: [_jsx(Sidebar, {}), _jsxs("div", { className: "relative flex min-h-screen flex-1 flex-col", children: [_jsx(Header, {}), _jsx("main", { className: cn('flex-1 overflow-y-auto px-4 pb-16 pt-6 transition-[padding-left] duration-300 sm:px-8', sidebarCollapsed ? 'sm:pl-24' : 'sm:pl-8'), children: _jsx("div", { className: "mx-auto w-full max-w-[1600px] space-y-10", children: _jsx(Outlet, {}) }) })] }), _jsx(CommandPalette, {}), _jsx(DownloadsDrawer, {}), _jsx(TorrentSearchDialog, {})] }));
}
export default AppShell;
