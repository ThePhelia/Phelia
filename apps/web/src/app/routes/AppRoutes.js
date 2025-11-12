import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { Suspense, lazy } from 'react';
import { Route, Routes, useLocation } from 'react-router-dom';
import AppShell from '@/app/components/AppShell';
import DetailDialogRoute from '@/app/routes/details/DetailDialogRoute';
import LoadingView from '@/app/routes/LoadingView';
const HomePage = lazy(() => import('@/app/routes/index'));
const MoviesPage = lazy(() => import('@/app/routes/movies'));
const TvPage = lazy(() => import('@/app/routes/tv'));
const MusicPage = lazy(() => import('@/app/routes/music'));
const LibraryPage = lazy(() => import('@/app/routes/library'));
const DownloadsPage = lazy(() => import('@/app/routes/downloads'));
const SettingsPage = lazy(() => import('@/app/routes/settings'));
const MarketPage = lazy(() => import('@/pages/Market'));
const DetailPage = lazy(() => import('@/app/routes/details/$kind.$id'));
function AppRoutes() {
    const location = useLocation();
    const state = location.state;
    return (_jsxs(_Fragment, { children: [_jsx(Suspense, { fallback: _jsx(LoadingView, {}), children: _jsx(Routes, { location: state?.backgroundLocation ?? location, children: _jsxs(Route, { element: _jsx(AppShell, {}), children: [_jsx(Route, { index: true, element: _jsx(HomePage, {}) }), _jsx(Route, { path: "movies", element: _jsx(MoviesPage, {}) }), _jsx(Route, { path: "tv", element: _jsx(TvPage, {}) }), _jsx(Route, { path: "music", element: _jsx(MusicPage, {}) }), _jsx(Route, { path: "market", element: _jsx(MarketPage, {}) }), _jsx(Route, { path: "library", element: _jsx(LibraryPage, {}) }), _jsx(Route, { path: "downloads", element: _jsx(DownloadsPage, {}) }), _jsx(Route, { path: "settings", element: _jsx(SettingsPage, {}) }), _jsx(Route, { path: "details/:kind/:id", element: _jsx(DetailPage, {}) })] }) }) }), state?.backgroundLocation ? (_jsx(Suspense, { fallback: null, children: _jsx(Routes, { children: _jsx(Route, { path: "details/:kind/:id", element: _jsx(DetailDialogRoute, {}) }) }) })) : null] }));
}
export default AppRoutes;
