import { Suspense, lazy } from 'react';
import { Route, Routes, useLocation } from 'react-router-dom';

import AppShell from '@/app/components/AppShell';
import DetailDialogRoute from '@/app/routes/details/DetailDialogRoute';
import LoadingView from '@/app/routes/LoadingView';

const HomePage = lazy(() => import('@/app/routes/index'));
const MoviesPage = lazy(() => import('@/app/routes/movies'));
const TvPage = lazy(() => import('@/app/routes/tv'));
const MusicPage = lazy(() => import('@/app/routes/music'));
const BrowsePage = lazy(() => import('@/app/routes/browse'));
const LibraryPage = lazy(() => import('@/app/routes/library'));
const DownloadsPage = lazy(() => import('@/app/routes/downloads'));
const SettingsPage = lazy(() => import('@/app/routes/settings'));
const DetailPage = lazy(() => import('@/app/routes/details/$kind.$id'));

function AppRoutes() {
  const location = useLocation();
  const state = location.state as { backgroundLocation?: Location } | undefined;

  return (
    <>
      <Suspense fallback={<LoadingView />}>
        <Routes location={state?.backgroundLocation ?? location}>
          <Route element={<AppShell />}>
            <Route index element={<HomePage />} />
            <Route path="browse" element={<BrowsePage />} />
            <Route path="movies" element={<MoviesPage />} />
            <Route path="tv" element={<TvPage />} />
            <Route path="music" element={<MusicPage />} />
            <Route path="library" element={<LibraryPage />} />
            <Route path="downloads" element={<DownloadsPage />} />
            <Route path="settings" element={<SettingsPage />} />
            <Route path="details/:kind/:id" element={<DetailPage />} />
          </Route>
        </Routes>
      </Suspense>
      {state?.backgroundLocation ? (
        <Suspense fallback={null}>
          <Routes>
            <Route path="details/:kind/:id" element={<DetailDialogRoute />} />
          </Routes>
        </Suspense>
      ) : null}
    </>
  );
}

export default AppRoutes;
