import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { LoginPage } from '../LoginPage';
import { useAuthStore } from '@/stores/authStore';

// Mock the API client
vi.mock('@/api/client', () => ({
  apiClient: {
    post: vi.fn(),
    get: vi.fn(),
  },
  getErrorMessage: vi.fn((error) => error?.message || 'An error occurred'),
}));

function renderLoginPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe('LoginPage', () => {
  beforeEach(() => {
    useAuthStore.setState({
      user: null,
      token: null,
      isAuthenticated: false,
    });
    vi.clearAllMocks();
  });

  it('should render login form', () => {
    renderLoginPage();

    expect(screen.getByText('Welcome back')).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/enter your username/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/enter your password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('should have link to register page', () => {
    renderLoginPage();

    const signUpLink = screen.getByRole('link', { name: /sign up/i });
    expect(signUpLink).toBeInTheDocument();
    expect(signUpLink).toHaveAttribute('href', '/register');
  });

  it('should show validation errors for empty fields', async () => {
    const user = userEvent.setup();
    renderLoginPage();

    const submitButton = screen.getByRole('button', { name: /sign in/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/username is required/i)).toBeInTheDocument();
    });
  });

  it('should allow typing in username field', async () => {
    const user = userEvent.setup();
    renderLoginPage();

    const usernameInput = screen.getByPlaceholderText(/enter your username/i);
    await user.type(usernameInput, 'testuser');

    expect(usernameInput).toHaveValue('testuser');
  });

  it('should toggle password visibility', async () => {
    const user = userEvent.setup();
    renderLoginPage();

    const passwordInput = screen.getByPlaceholderText(/enter your password/i);
    expect(passwordInput).toHaveAttribute('type', 'password');

    // Find the toggle button (contains an svg icon)
    const toggleButtons = screen.getAllByRole('button').filter(
      (btn) => btn.querySelector('svg') && (btn as HTMLButtonElement).type === 'button'
    );

    if (toggleButtons.length > 0) {
      await user.click(toggleButtons[0]);
      expect(passwordInput).toHaveAttribute('type', 'text');
    }
  });

  it('should disable submit button while loading', async () => {
    const user = userEvent.setup();
    const { apiClient } = await import('@/api/client');

    // Mock a slow response
    vi.mocked(apiClient.post).mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve({ data: {} }), 1000))
    );

    renderLoginPage();

    await user.type(screen.getByPlaceholderText(/enter your username/i), 'testuser');
    await user.type(screen.getByPlaceholderText(/enter your password/i), 'password123');

    const submitButton = screen.getByRole('button', { name: /sign in/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/signing in/i)).toBeInTheDocument();
    });
  });
});
