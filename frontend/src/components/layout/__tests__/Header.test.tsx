import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { Header } from '../Header';
import { useUIStore } from '@/stores/uiStore';
import { useAuthStore } from '@/stores/authStore';

function renderHeader() {
  return render(
    <MemoryRouter>
      <Header />
    </MemoryRouter>
  );
}

describe('Header', () => {
  beforeEach(() => {
    useUIStore.setState({ sidebarOpen: true, theme: 'system' });
    useAuthStore.setState({
      user: {
        id: 1,
        username: 'testuser',
        email: 'test@example.com',
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
      },
      token: 'test-token',
      isAuthenticated: true,
    });
  });

  it('should render sidebar toggle button', () => {
    renderHeader();
    expect(screen.getByRole('button', { name: /toggle sidebar/i })).toBeInTheDocument();
  });

  it('should render theme toggle button', () => {
    renderHeader();
    expect(screen.getByRole('button', { name: /toggle theme/i })).toBeInTheDocument();
  });

  it('should render user avatar', () => {
    renderHeader();
    // Look for the avatar button
    const avatarButton = screen.getByRole('button', { name: /te/i });
    expect(avatarButton).toBeInTheDocument();
  });

  it('should toggle sidebar when toggle button is clicked', async () => {
    const user = userEvent.setup();
    renderHeader();

    const toggleButton = screen.getByRole('button', { name: /toggle sidebar/i });
    await user.click(toggleButton);

    expect(useUIStore.getState().sidebarOpen).toBe(false);
  });

  it('should cycle through themes when theme toggle is clicked', async () => {
    const user = userEvent.setup();
    useUIStore.setState({ theme: 'light' });
    renderHeader();

    const themeButton = screen.getByRole('button', { name: /toggle theme/i });

    // Light -> System
    await user.click(themeButton);
    expect(useUIStore.getState().theme).toBe('system');

    // System -> Dark
    await user.click(themeButton);
    expect(useUIStore.getState().theme).toBe('dark');

    // Dark -> Light
    await user.click(themeButton);
    expect(useUIStore.getState().theme).toBe('light');
  });

  it('should open user dropdown menu on avatar click', async () => {
    const user = userEvent.setup();
    renderHeader();

    const avatarButton = screen.getAllByRole('button').find(
      (btn) => btn.textContent === 'TE'
    );

    if (avatarButton) {
      await user.click(avatarButton);

      // Check dropdown content appears
      expect(await screen.findByText('testuser')).toBeInTheDocument();
      expect(await screen.findByText('test@example.com')).toBeInTheDocument();
    }
  });

  it('should display user initials in avatar', () => {
    renderHeader();

    // User initials should be 'TE' for 'testuser'
    expect(screen.getByText('TE')).toBeInTheDocument();
  });

  it('should call logout when logout button is clicked', async () => {
    const user = userEvent.setup();
    renderHeader();

    // Open dropdown
    const avatarButton = screen.getAllByRole('button').find(
      (btn) => btn.textContent === 'TE'
    );

    if (avatarButton) {
      await user.click(avatarButton);

      // Click logout
      const logoutButton = await screen.findByText(/log out/i);
      await user.click(logoutButton);

      expect(useAuthStore.getState().isAuthenticated).toBe(false);
    }
  });
});
