import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RegisterPage } from '../RegisterPage';
import { useAuthStore } from '@/stores/authStore';

// Mock the API client
vi.mock('@/api/client', () => ({
  apiClient: {
    post: vi.fn(),
    get: vi.fn(),
  },
  getErrorMessage: vi.fn((error) => error?.message || 'An error occurred'),
}));

function renderRegisterPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <RegisterPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe('RegisterPage', () => {
  beforeEach(() => {
    useAuthStore.setState({
      user: null,
      token: null,
      isAuthenticated: false,
    });
    vi.clearAllMocks();
  });

  it('should render register form', () => {
    renderRegisterPage();

    expect(screen.getByText('Create an account')).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/choose a username/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/enter your email/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/create a password/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/confirm your password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /create account/i })).toBeInTheDocument();
  });

  it('should have link to login page', () => {
    renderRegisterPage();

    const signInLink = screen.getByRole('link', { name: /sign in/i });
    expect(signInLink).toBeInTheDocument();
    expect(signInLink).toHaveAttribute('href', '/login');
  });

  it('should validate username length', async () => {
    const user = userEvent.setup();
    renderRegisterPage();

    await user.type(screen.getByPlaceholderText(/choose a username/i), 'ab');
    await user.type(screen.getByPlaceholderText(/enter your email/i), 'test@example.com');
    await user.type(screen.getByPlaceholderText(/create a password/i), 'Password12345');
    await user.type(screen.getByPlaceholderText(/confirm your password/i), 'Password12345');

    const submitButton = screen.getByRole('button', { name: /create account/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/username must be at least 3 characters/i)).toBeInTheDocument();
    });
  });

  it('should accept valid email input', async () => {
    const user = userEvent.setup();
    renderRegisterPage();

    const emailInput = screen.getByPlaceholderText(/enter your email/i);
    await user.type(emailInput, 'test@example.com');

    expect(emailInput).toHaveValue('test@example.com');
  });

  it('should validate password length', async () => {
    const user = userEvent.setup();
    renderRegisterPage();

    await user.type(screen.getByPlaceholderText(/choose a username/i), 'testuser');
    await user.type(screen.getByPlaceholderText(/enter your email/i), 'test@example.com');
    await user.type(screen.getByPlaceholderText(/create a password/i), 'short');
    await user.type(screen.getByPlaceholderText(/confirm your password/i), 'short');

    const submitButton = screen.getByRole('button', { name: /create account/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/password must be at least 12 characters/i)).toBeInTheDocument();
    });
  });

  it('should validate password match', async () => {
    const user = userEvent.setup();
    renderRegisterPage();

    await user.type(screen.getByPlaceholderText(/choose a username/i), 'testuser');
    await user.type(screen.getByPlaceholderText(/enter your email/i), 'test@example.com');
    await user.type(screen.getByPlaceholderText(/create a password/i), 'Password12345');
    await user.type(screen.getByPlaceholderText(/confirm your password/i), 'Password45678');

    const submitButton = screen.getByRole('button', { name: /create account/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/passwords don't match/i)).toBeInTheDocument();
    });
  });

  it('should toggle password visibility', async () => {
    const user = userEvent.setup();
    renderRegisterPage();

    const passwordInput = screen.getByPlaceholderText(/create a password/i);
    expect(passwordInput).toHaveAttribute('type', 'password');

    // Find toggle buttons (there are multiple for password fields)
    const toggleButtons = screen.getAllByRole('button').filter(
      (btn) => btn.querySelector('svg') && (btn as HTMLButtonElement).type === 'button'
    );

    if (toggleButtons.length > 0) {
      await user.click(toggleButtons[0]);
      expect(passwordInput).toHaveAttribute('type', 'text');
    }
  });
});
