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

  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar />
      <div className="relative flex min-h-screen flex-1 flex-col">
        <Header />
        <main
          className={cn(
            'flex-1 overflow-y-auto px-4 pb-16 pt-6 transition-[padding-left] duration-300 sm:px-8',
            sidebarCollapsed ? 'sm:pl-24' : 'sm:pl-8',
          )}
        >
          <div className="mx-auto w-full max-w-[1600px] space-y-10">
            <Outlet />
          </div>
        </main>
      </div>
      <CommandPalette />
      <DownloadsDrawer />
      <TorrentSearchDialog />
    </div>
  );
}

export default AppShell;
