import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AgentsPage } from '../AgentsPage';
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

const mockAgents = [
  {
    id: 1,
    name: 'Test Agent',
    description: 'A test agent',
    agent_type: 'ReAct',
    tags: ['test'],
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: null,
  },
  {
    id: 2,
    name: 'Another Agent',
    description: 'Another test agent',
    agent_type: 'Conversational',
    tags: ['demo'],
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

describe('AgentsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (apiClient.get as Mock).mockResolvedValue({
      data: {
        agents: mockAgents,
        total: 2,
        page: 1,
        page_size: 12,
      },
    });
  });

  it('renders page title', async () => {
    renderWithProviders(<AgentsPage />);
    expect(screen.getByRole('heading', { name: /agents/i })).toBeInTheDocument();
  });

  it('renders agents list when data loads', async () => {
    renderWithProviders(<AgentsPage />);

    await waitFor(() => {
      expect(screen.getByText('Test Agent')).toBeInTheDocument();
    });

    expect(screen.getByText('Another Agent')).toBeInTheDocument();
  });

  it('shows empty state when no agents exist', async () => {
    (apiClient.get as Mock).mockResolvedValue({
      data: {
        agents: [],
        total: 0,
        page: 1,
        page_size: 12,
      },
    });

    renderWithProviders(<AgentsPage />);

    await waitFor(() => {
      expect(screen.getByText(/no agents yet/i)).toBeInTheDocument();
    });
  });

  it('filters agents by search', async () => {
    const user = userEvent.setup();
    renderWithProviders(<AgentsPage />);

    await waitFor(() => {
      expect(screen.getByText('Test Agent')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/search agents/i);
    await user.type(searchInput, 'Test');

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith(
        expect.stringContaining('search=Test')
      );
    });
  });

  it('shows agent type badges', async () => {
    renderWithProviders(<AgentsPage />);

    await waitFor(() => {
      expect(screen.getByText('ReAct')).toBeInTheDocument();
      expect(screen.getByText('Conversational')).toBeInTheDocument();
    });
  });

  it('has a button to create new agent', async () => {
    renderWithProviders(<AgentsPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /new agent/i })).toBeInTheDocument();
    });
  });
});
