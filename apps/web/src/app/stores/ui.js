import { create } from 'zustand';
export const useUiState = create((set) => ({
    sidebarCollapsed: false,
    setSidebarCollapsed: (value) => set({ sidebarCollapsed: value }),
    downloadsOpen: false,
    setDownloadsOpen: (downloadsOpen) => set({ downloadsOpen }),
    commandOpen: false,
    setCommandOpen: (commandOpen) => set({ commandOpen }),
}));
