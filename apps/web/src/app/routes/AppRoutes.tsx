import { Suspense, lazy, useEffect } from 'react';
import { Route, Routes, useLocation } from 'react-router-dom';

import AppShell from '@/app/components/AppShell';
import { reportFrontendRuntimeError } from '@/app/lib/telemetry';
import DetailDialogRoute from '@/app/routes/details/DetailDialogRoute';
import LoadingView from '@/app/routes/LoadingView';

const HomePage = lazy(() => import('@/app/routes/index'));
const MoviesPage = lazy(() => import('@/app/routes/movies'));
const TvPage = lazy(() => import('@/app/routes/tv'));
const MusicPage = lazy(() => import('@/app/routes/music'));
const LibraryPage = lazy(() => import('@/app/routes/library'));
const DownloadsPage = lazy(() => import('@/app/routes/downloads'));
const SettingsPage = lazy(() => import('@/app/routes/settings'));
const DetailPage = lazy(() => import('@/app/routes/details/$kind.$id'));

function AppRoutes() {
  const location = useLocation();
  const state = location.state as { backgroundLocation?: Location } | undefined;

  useEffect(() => {
    const onError = (event: ErrorEvent) => {
      reportFrontendRuntimeError({
        routeName: location.pathname,
        selectorKey: event.filename || 'window.error',
        message: event.message || 'Unhandled runtime error',
        stack: event.error?.stack,
      });
    };

    const onUnhandledRejection = (event: PromiseRejectionEvent) => {
      const reason = event.reason instanceof Error ? event.reason : new Error(String(event.reason));
      reportFrontendRuntimeError({
        routeName: location.pathname,
        selectorKey: 'window.unhandledrejection',
        message: reason.message,
        stack: reason.stack,
      });
    };

    window.addEventListener('error', onError);
    window.addEventListener('unhandledrejection', onUnhandledRejection);

    return () => {
      window.removeEventListener('error', onError);
      window.removeEventListener('unhandledrejection', onUnhandledRejection);
    };
  }, [location.pathname]);

  return (
    <>
      <Suspense fallback={<LoadingView />}>
        <Routes location={state?.backgroundLocation ?? location}>
          <Route element={<AppShell />}>
            <Route index element={<PageErrorBoundary pageName="home"><HomePage /></PageErrorBoundary>} />
            <Route path="movies" element={<PageErrorBoundary pageName="movies"><MoviesPage /></PageErrorBoundary>} />
            <Route path="tv" element={<PageErrorBoundary pageName="tv"><TvPage /></PageErrorBoundary>} />
            <Route path="music" element={<PageErrorBoundary pageName="music"><MusicPage /></PageErrorBoundary>} />
            <Route path="library" element={<PageErrorBoundary pageName="library"><LibraryPage /></PageErrorBoundary>} />
            <Route path="downloads" element={<PageErrorBoundary pageName="downloads"><DownloadsPage /></PageErrorBoundary>} />
            <Route path="settings" element={<PageErrorBoundary pageName="settings"><SettingsPage /></PageErrorBoundary>} />
            <Route path="details/:kind/:id" element={<PageErrorBoundary pageName="details"><DetailPage /></PageErrorBoundary>} />
          </Route>
        </Routes>
      </Suspense>
      {state?.backgroundLocation ? (
        <Suspense fallback={null}>
          <Routes>
            <Route path="details/:kind/:id" element={<PageErrorBoundary pageName="detail-dialog"><DetailDialogRoute /></PageErrorBoundary>} />
          </Routes>
        </Suspense>
      ) : null}
    </>
  );
}

export default AppRoutes;
