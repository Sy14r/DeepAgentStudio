import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PromptsPage } from '../PromptsPage';
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

const mockPrompts = [
  {
    id: 1,
    name: 'System Prompt',
    description: 'A system prompt template',
    use_case: 'general',
    message_type: 'system',
    tags: ['default'],
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: null,
  },
  {
    id: 2,
    name: 'Coding Helper',
    description: 'For code assistance',
    use_case: 'coding',
    message_type: 'system',
    tags: ['code', 'developer'],
    is_active: true,
    created_at: '2024-01-02T00:00:00Z',
    updated_at: null,
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

describe('PromptsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (apiClient.get as Mock).mockResolvedValue({
      data: {
        prompts: mockPrompts,
        total: 2,
        page: 1,
        page_size: 12,
      },
    });
  });

  it('renders page title', async () => {
    renderWithProviders(<PromptsPage />);
    expect(screen.getByRole('heading', { name: /prompts/i })).toBeInTheDocument();
  });

  it('renders prompts list when data loads', async () => {
    renderWithProviders(<PromptsPage />);

    await waitFor(() => {
      expect(screen.getByText('System Prompt')).toBeInTheDocument();
    });

    expect(screen.getByText('Coding Helper')).toBeInTheDocument();
  });

  it('shows empty state when no prompts exist', async () => {
    (apiClient.get as Mock).mockResolvedValue({
      data: {
        prompts: [],
        total: 0,
        page: 1,
        page_size: 12,
      },
    });

    renderWithProviders(<PromptsPage />);

    await waitFor(() => {
      expect(screen.getByText(/no prompts yet/i)).toBeInTheDocument();
    });
  });

  it('shows use case badges', async () => {
    renderWithProviders(<PromptsPage />);

    await waitFor(() => {
      expect(screen.getByText('general')).toBeInTheDocument();
      expect(screen.getByText('coding')).toBeInTheDocument();
    });
  });

  it('filters prompts by search', async () => {
    const user = userEvent.setup();
    renderWithProviders(<PromptsPage />);

    await waitFor(() => {
      expect(screen.getByText('System Prompt')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/search prompts/i);
    await user.type(searchInput, 'System');

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith(
        expect.stringContaining('search=System')
      );
    });
  });

  it('has a button to create new prompt', async () => {
    renderWithProviders(<PromptsPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /new prompt/i })).toBeInTheDocument();
    });
  });
});
