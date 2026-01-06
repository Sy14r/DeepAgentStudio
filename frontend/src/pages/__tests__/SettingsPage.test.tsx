import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SettingsPage } from '../SettingsPage';
import { vi, describe, it, expect, beforeEach, Mock } from 'vitest';
import { apiClient } from '@/api/client';

vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock('@/stores/authStore', () => ({
  useAuthStore: () => ({
    user: {
      id: 1,
      username: 'testuser',
      email: 'test@example.com',
    },
  }),
}));

vi.mock('@/stores/uiStore', () => ({
  useUIStore: () => ({
    theme: 'light',
    setTheme: vi.fn(),
  }),
}));

const mockProviders = [
  {
    id: 1,
    name: 'OpenAI Provider',
    provider_type: 'openai',
    is_active: true,
    config: {},
    last_used_at: '2024-01-01T00:00:00Z',
    created_at: '2024-01-01T00:00:00Z',
  },
  {
    id: 2,
    name: 'Anthropic Provider',
    provider_type: 'anthropic',
    is_active: true,
    config: {},
    last_used_at: null,
    created_at: '2024-01-02T00:00:00Z',
  },
];

function renderWithProviders(component: React.ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{component}</BrowserRouter>
    </QueryClientProvider>
  );
}

describe('SettingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (apiClient.get as Mock).mockResolvedValue({
      data: {
        providers: mockProviders,
        total: 2,
        page: 1,
        page_size: 50,
      },
    });
  });

  it('renders page title', async () => {
    renderWithProviders(<SettingsPage />);
    expect(screen.getByRole('heading', { name: /settings/i })).toBeInTheDocument();
  });

  it('shows profile section with user info', async () => {
    renderWithProviders(<SettingsPage />);

    await waitFor(() => {
      expect(screen.getByText('Profile')).toBeInTheDocument();
      expect(screen.getByText('testuser')).toBeInTheDocument();
      expect(screen.getByText('test@example.com')).toBeInTheDocument();
    });
  });

  it('shows appearance section with theme options', async () => {
    renderWithProviders(<SettingsPage />);

    await waitFor(() => {
      expect(screen.getByText('Appearance')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /light/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /dark/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /system/i })).toBeInTheDocument();
    });
  });

  it('shows LLM Providers section', async () => {
    renderWithProviders(<SettingsPage />);

    await waitFor(() => {
      expect(screen.getByText('LLM Providers')).toBeInTheDocument();
    });
  });

  it('renders LLM providers list when data loads', async () => {
    renderWithProviders(<SettingsPage />);

    await waitFor(() => {
      expect(screen.getByText('OpenAI Provider')).toBeInTheDocument();
      expect(screen.getByText('Anthropic Provider')).toBeInTheDocument();
    });
  });

  it('shows provider type badges', async () => {
    renderWithProviders(<SettingsPage />);

    await waitFor(() => {
      expect(screen.getByText('OpenAI')).toBeInTheDocument();
      expect(screen.getByText('Anthropic')).toBeInTheDocument();
    });
  });

  it('has add provider button', async () => {
    renderWithProviders(<SettingsPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /add provider/i })).toBeInTheDocument();
    });
  });

  it('shows empty state when no providers exist', async () => {
    (apiClient.get as Mock).mockResolvedValue({
      data: {
        providers: [],
        total: 0,
        page: 1,
        page_size: 50,
      },
    });

    renderWithProviders(<SettingsPage />);

    await waitFor(() => {
      expect(screen.getByText(/no llm providers configured/i)).toBeInTheDocument();
    });
  });

  it('opens form dialog when add provider is clicked', async () => {
    const user = userEvent.setup();
    renderWithProviders(<SettingsPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /add provider/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /add provider/i }));

    await waitFor(() => {
      expect(screen.getByText('Add LLM Provider')).toBeInTheDocument();
    });
  });
});
