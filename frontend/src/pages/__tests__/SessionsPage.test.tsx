import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SessionsPage } from '../SessionsPage';
import { vi, describe, it, expect, beforeEach, Mock } from 'vitest';
import { apiClient } from '@/api/client';

vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
  },
}));

const mockSessions = [
  {
    id: 1,
    title: 'Test Session',
    status: 'completed',
    agent_id: 1,
    started_at: '2024-01-01T00:00:00Z',
    completed_at: '2024-01-01T00:05:00Z',
    total_latency_ms: 5000,
    token_usage_input: 100,
    token_usage_output: 200,
    total_cost: 0.001,
    error_message: null,
    error_type: null,
  },
  {
    id: 2,
    title: 'Failed Session',
    status: 'failed',
    agent_id: 1,
    started_at: '2024-01-02T00:00:00Z',
    completed_at: '2024-01-02T00:01:00Z',
    total_latency_ms: 1000,
    token_usage_input: 50,
    token_usage_output: 0,
    total_cost: 0.0005,
    error_message: 'Something went wrong',
    error_type: 'RuntimeError',
  },
];

const mockAgents = [
  {
    id: 1,
    name: 'Test Agent',
    agent_type: 'ReAct',
    is_active: true,
  },
];

const mockStatistics = {
  total_sessions: 2,
  completed_sessions: 1,
  failed_sessions: 1,
  average_latency_ms: 3000,
  total_tokens_used: 350,
  total_cost: 0.0015,
  success_rate: 50, // API returns percentage (0-100), not decimal
};

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

describe('SessionsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (apiClient.get as Mock).mockImplementation((url: string) => {
      if (url.includes('/sessions/statistics')) {
        return Promise.resolve({ data: mockStatistics });
      }
      if (url.includes('/agents')) {
        return Promise.resolve({
          data: { agents: mockAgents, total: 1, page: 1, page_size: 100 },
        });
      }
      if (url.includes('/sessions')) {
        return Promise.resolve({
          data: { sessions: mockSessions, total: 2, page: 1, page_size: 12 },
        });
      }
      return Promise.resolve({ data: {} });
    });
  });

  it('renders page title', async () => {
    renderWithProviders(<SessionsPage />);
    expect(screen.getByRole('heading', { name: /sessions/i })).toBeInTheDocument();
  });

  it('renders sessions list when data loads', async () => {
    renderWithProviders(<SessionsPage />);

    await waitFor(() => {
      expect(screen.getByText('Test Session')).toBeInTheDocument();
    });

    expect(screen.getByText('Failed Session')).toBeInTheDocument();
  });

  it('shows statistics cards', async () => {
    renderWithProviders(<SessionsPage />);

    await waitFor(() => {
      expect(screen.getByText('Total Sessions')).toBeInTheDocument();
      expect(screen.getByText('Success Rate')).toBeInTheDocument();
    });
  });

  it('shows success rate statistic', async () => {
    renderWithProviders(<SessionsPage />);

    await waitFor(() => {
      expect(screen.getByText('50.0%')).toBeInTheDocument();
    });
  });

  it('shows empty state when no sessions exist', async () => {
    (apiClient.get as Mock).mockImplementation((url: string) => {
      if (url.includes('/sessions/statistics')) {
        return Promise.resolve({
          data: { ...mockStatistics, total_sessions: 0 },
        });
      }
      if (url.includes('/agents')) {
        return Promise.resolve({
          data: { agents: mockAgents, total: 1, page: 1, page_size: 100 },
        });
      }
      if (url.includes('/sessions')) {
        return Promise.resolve({
          data: { sessions: [], total: 0, page: 1, page_size: 12 },
        });
      }
      return Promise.resolve({ data: {} });
    });

    renderWithProviders(<SessionsPage />);

    await waitFor(() => {
      expect(screen.getByText(/no sessions yet/i)).toBeInTheDocument();
    });
  });

  it('shows status badges', async () => {
    renderWithProviders(<SessionsPage />);

    await waitFor(() => {
      expect(screen.getByText('completed')).toBeInTheDocument();
      expect(screen.getByText('failed')).toBeInTheDocument();
    });
  });

  it('has view details button for each session', async () => {
    renderWithProviders(<SessionsPage />);

    await waitFor(() => {
      const viewButtons = screen.getAllByRole('button', { name: /view details/i });
      expect(viewButtons).toHaveLength(2);
    });
  });
});
