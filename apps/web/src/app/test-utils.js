import { jsx as _jsx } from "react/jsx-runtime";
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { ThemeProvider } from '@/app/components/ThemeProvider';
function createQueryClient() {
    return new QueryClient({
        defaultOptions: {
            queries: { retry: false },
            mutations: { retry: false },
        },
    });
}
export function renderWithProviders(ui, { route = '/' } = {}) {
    window.history.pushState({}, 'Test Page', route);
    const queryClient = createQueryClient();
    const Wrapper = ({ children }) => (_jsx(ThemeProvider, { children: _jsx(QueryClientProvider, { client: queryClient, children: _jsx(BrowserRouter, { children: children }) }) }));
    return {
        queryClient,
        ...render(ui, { wrapper: Wrapper }),
    };
}
