import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useUIStore } from '../uiStore';

describe('uiStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    useUIStore.setState({
      sidebarOpen: true,
      theme: 'system',
    });
    // Clear any class modifications
    document.documentElement.classList.remove('light', 'dark');
  });

  describe('initial state', () => {
    it('should have sidebar open by default', () => {
      const state = useUIStore.getState();
      expect(state.sidebarOpen).toBe(true);
    });

    it('should have system theme by default', () => {
      const state = useUIStore.getState();
      expect(state.theme).toBe('system');
    });
  });

  describe('toggleSidebar', () => {
    it('should toggle sidebar from open to closed', () => {
      useUIStore.getState().toggleSidebar();
      expect(useUIStore.getState().sidebarOpen).toBe(false);
    });

    it('should toggle sidebar from closed to open', () => {
      useUIStore.setState({ sidebarOpen: false });
      useUIStore.getState().toggleSidebar();
      expect(useUIStore.getState().sidebarOpen).toBe(true);
    });
  });

  describe('setSidebarOpen', () => {
    it('should set sidebar to open', () => {
      useUIStore.setState({ sidebarOpen: false });
      useUIStore.getState().setSidebarOpen(true);
      expect(useUIStore.getState().sidebarOpen).toBe(true);
    });

    it('should set sidebar to closed', () => {
      useUIStore.getState().setSidebarOpen(false);
      expect(useUIStore.getState().sidebarOpen).toBe(false);
    });
  });

  describe('setTheme', () => {
    it('should set theme to light', () => {
      useUIStore.getState().setTheme('light');
      expect(useUIStore.getState().theme).toBe('light');
      expect(document.documentElement.classList.contains('light')).toBe(true);
    });

    it('should set theme to dark', () => {
      useUIStore.getState().setTheme('dark');
      expect(useUIStore.getState().theme).toBe('dark');
      expect(document.documentElement.classList.contains('dark')).toBe(true);
    });

    it('should set theme to system and apply based on preference', () => {
      // Mock matchMedia to return dark preference
      vi.spyOn(window, 'matchMedia').mockImplementation((query) => ({
        matches: query === '(prefers-color-scheme: dark)',
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      }));

      useUIStore.getState().setTheme('system');
      expect(useUIStore.getState().theme).toBe('system');
      expect(document.documentElement.classList.contains('dark')).toBe(true);
    });
  });
});
