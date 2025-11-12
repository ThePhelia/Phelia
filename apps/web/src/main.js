import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { BrowserRouter } from 'react-router-dom';
import { Toaster } from 'sonner';
import AppRoutes from '@/app/routes/AppRoutes';
import { ThemeProvider } from '@/app/components/ThemeProvider';
import '@/app/lib/i18n';
import '@/styles/tokens.css';
import '@/styles/globals.css';
const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            refetchOnWindowFocus: false,
            retry: 2,
            staleTime: 1000 * 60,
        },
        mutations: {
            retry: 1,
        },
    },
});
const rootElement = document.getElementById('root');
if (!rootElement) {
    throw new Error('Root element not found');
}
ReactDOM.createRoot(rootElement).render(_jsx(React.StrictMode, { children: _jsxs(QueryClientProvider, { client: queryClient, children: [_jsx(ThemeProvider, { children: _jsx(BrowserRouter, { children: _jsx(AppRoutes, {}) }) }), _jsx(Toaster, { position: "bottom-right", richColors: true, closeButton: true }), import.meta.env.DEV ? _jsx(ReactQueryDevtools, { initialIsOpen: false }) : null] }) }));
