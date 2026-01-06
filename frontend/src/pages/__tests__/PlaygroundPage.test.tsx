import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PlaygroundPage } from '../PlaygroundPage';
import { vi, describe, it, expect, beforeEach, Mock } from 'vitest';
import { apiClient } from '@/api/client';

vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

const mockAgents = [
  {
    id: 1,
    name: 'Test Agent',
    description: 'A test agent for playground',
    agent_type: 'ReAct',
    tags: ['test'],
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
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

describe('PlaygroundPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (apiClient.get as Mock).mockResolvedValue({
      data: {
        agents: mockAgents,
        total: 1,
        page: 1,
        page_size: 100,
      },
    });
  });

  it('renders page title', async () => {
    renderWithProviders(<PlaygroundPage />);
    expect(screen.getByRole('heading', { name: /playground/i })).toBeInTheDocument();
  });

  it('shows agent selector', async () => {
    renderWithProviders(<PlaygroundPage />);

    await waitFor(() => {
      expect(screen.getByText('Agent')).toBeInTheDocument();
    });
  });

  it('shows chat panel', async () => {
    renderWithProviders(<PlaygroundPage />);

    await waitFor(() => {
      expect(screen.getByText('Chat')).toBeInTheDocument();
    });
  });

  it('shows execution trace panel', async () => {
    renderWithProviders(<PlaygroundPage />);

    await waitFor(() => {
      expect(screen.getByText('Execution Trace')).toBeInTheDocument();
    });
  });

  it('shows prompt to select agent when none selected', async () => {
    renderWithProviders(<PlaygroundPage />);

    await waitFor(() => {
      expect(screen.getByText(/select an agent to start chatting/i)).toBeInTheDocument();
    });
  });

  it('has new session button', async () => {
    renderWithProviders(<PlaygroundPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /new session/i })).toBeInTheDocument();
    });
  });

  it('has message input field', async () => {
    renderWithProviders(<PlaygroundPage />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/select an agent first/i)).toBeInTheDocument();
    });
  });
});
