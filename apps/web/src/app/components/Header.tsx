import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Download, Menu, Settings, SunMoon, User } from 'lucide-react';
import GlobalSearch from '@/app/components/GlobalSearch';
import { Button } from '@/app/components/ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/app/components/ui/tooltip';
import { Avatar, AvatarFallback } from '@/app/components/ui/avatar';
import { useUiState } from '@/app/stores/ui';
import { useTheme } from '@/app/components/ThemeProvider';
import { cn } from '@/app/utils/cn';

function Header() {
  const { t } = useTranslation();
  const { toggle, resolved } = useTheme();
  const setDownloadsOpen = useUiState((state) => state.setDownloadsOpen);
  const sidebarCollapsed = useUiState((state) => state.sidebarCollapsed);
  const setSidebarCollapsed = useUiState((state) => state.setSidebarCollapsed);
  const setCommandOpen = useUiState((state) => state.setCommandOpen);

  return (
    <header className="sticky top-0 z-30 flex items-center justify-between gap-4 border-b border-border/60 bg-background/80 px-4 py-4 backdrop-blur-xl sm:px-8">
      <div className="flex flex-1 items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          className="hidden rounded-full border border-border/60 bg-background/50 shadow-sm transition hover:border-border/80 hover:bg-background/80 lg:inline-flex"
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
        >
          <Menu className="h-5 w-5" />
          <span className="sr-only">Toggle navigation</span>
        </Button>
        <Link to="/" className={cn('flex items-center gap-2 text-lg font-semibold tracking-tight')}>
          <div className="flex h-9 w-9 items-center justify-center rounded-2xl bg-gradient-to-br from-[color:var(--accent)] to-orange-200 text-black shadow-glow">
            P
          </div>
          <span className="hidden sm:inline">Phelia</span>
        </Link>
        <div className="flex-1">
          <GlobalSearch />
        </div>
      </div>
      <TooltipProvider>
        <div className="flex items-center gap-2">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="rounded-full border border-border/60 bg-background/50 shadow-sm transition hover:bg-background/80"
                onClick={() => setCommandOpen(true)}
              >
                <span className="text-sm font-semibold">⌘K</span>
              </Button>
            </TooltipTrigger>
            <TooltipContent>Command palette</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="rounded-full border border-border/60 bg-background/50 shadow-sm transition hover:bg-background/80"
                onClick={() => setDownloadsOpen(true)}
              >
                <Download className="h-5 w-5" />
                <span className="sr-only">{t('sections.downloads')}</span>
              </Button>
            </TooltipTrigger>
            <TooltipContent>{t('sections.downloads')}</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="rounded-full border border-border/60 bg-background/50 shadow-sm transition hover:bg-background/80"
                onClick={toggle}
              >
                <SunMoon className="h-5 w-5" />
                <span className="sr-only">Toggle theme</span>
              </Button>
            </TooltipTrigger>
            <TooltipContent>Theme: {resolved}</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                asChild
                variant="ghost"
                size="icon"
                className="rounded-full border border-border/60 bg-background/50 shadow-sm transition hover:bg-background/80"
              >
                <Link to="/settings">
                  <Settings className="h-5 w-5" />
                  <span className="sr-only">{t('sections.settings')}</span>
                </Link>
              </Button>
            </TooltipTrigger>
            <TooltipContent>{t('sections.settings')}</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="rounded-full border border-border/60 bg-background/50 shadow-sm transition hover:bg-background/80"
              >
                <Avatar className="h-9 w-9">
                  <AvatarFallback>
                    <User className="h-5 w-5" />
                  </AvatarFallback>
                </Avatar>
              </Button>
            </TooltipTrigger>
            <TooltipContent>Profile</TooltipContent>
          </Tooltip>
        </div>
      </TooltipProvider>
    </header>
  );
}

export default Header;
