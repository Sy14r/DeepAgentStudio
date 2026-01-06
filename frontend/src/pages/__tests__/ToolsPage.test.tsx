import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ToolsPage } from '../ToolsPage';
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

const mockTools = [
  {
    id: 1,
    name: 'Web Search',
    description: 'Search the web for information',
    tool_type: 'builtin',
    category: 'web',
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
  },
  {
    id: 2,
    name: 'Custom Tool',
    description: 'A custom tool',
    tool_type: 'custom',
    category: 'utility',
    function_code: 'def run(query): return query',
    is_active: true,
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

describe('ToolsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (apiClient.get as Mock).mockResolvedValue({
      data: {
        tools: mockTools,
        total: 2,
        page: 1,
        page_size: 12,
      },
    });
  });

  it('renders page title', async () => {
    renderWithProviders(<ToolsPage />);
    expect(screen.getByRole('heading', { name: /tools/i })).toBeInTheDocument();
  });

  it('renders tools list when data loads', async () => {
    renderWithProviders(<ToolsPage />);

    await waitFor(() => {
      expect(screen.getByText('Web Search')).toBeInTheDocument();
    });

    expect(screen.getByText('Custom Tool')).toBeInTheDocument();
  });

  it('shows empty state when no tools exist', async () => {
    (apiClient.get as Mock).mockResolvedValue({
      data: {
        tools: [],
        total: 0,
        page: 1,
        page_size: 12,
      },
    });

    renderWithProviders(<ToolsPage />);

    await waitFor(() => {
      expect(screen.getByText(/no tools yet/i)).toBeInTheDocument();
    });
  });

  it('shows category badges', async () => {
    renderWithProviders(<ToolsPage />);

    await waitFor(() => {
      expect(screen.getByText('web')).toBeInTheDocument();
      expect(screen.getByText('utility')).toBeInTheDocument();
    });
  });

  it('filters tools by search', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ToolsPage />);

    await waitFor(() => {
      expect(screen.getByText('Web Search')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/search tools/i);
    await user.type(searchInput, 'Web');

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith(
        expect.stringContaining('search=Web')
      );
    });
  });

  it('has a button to create new tool', async () => {
    renderWithProviders(<ToolsPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /new tool/i })).toBeInTheDocument();
    });
  });
});
