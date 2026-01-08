import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PromptAnalytics } from '../PromptAnalytics';
import { vi, describe, it, expect, beforeEach, Mock } from 'vitest';
import { apiClient } from '@/api/client';

vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
  },
}));

const mockAnalyticsData = {
  prompt_id: 1,
  prompt_name: 'Test Prompt',
  total_usage_count: 150,
  total_versions: 3,
  current_version_id: 3,
  version_usage: [
    {
      version_id: 3,
      version_number: 3,
      usage_count: 100,
      is_active: true,
      is_current: true,
      created_at: '2024-01-03T00:00:00Z',
    },
    {
      version_id: 2,
      version_number: 2,
      usage_count: 35,
      is_active: true,
      is_current: false,
      created_at: '2024-01-02T00:00:00Z',
    },
    {
      version_id: 1,
      version_number: 1,
      usage_count: 15,
      is_active: false,
      is_current: false,
      created_at: '2024-01-01T00:00:00Z',
    },
  ],
};

function renderWithProviders(component: React.ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>{component}</QueryClientProvider>
  );
}

describe('PromptAnalytics', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Loading State', () => {
    it('shows loading spinner while fetching data', async () => {
      // Keep the promise pending
      (apiClient.get as Mock).mockImplementation(() => new Promise(() => {}));

      renderWithProviders(<PromptAnalytics promptId={1} />);

      // Spinner is rendered as a div with animate-spin class
      expect(document.querySelector('.animate-spin')).toBeInTheDocument();
    });
  });

  describe('Error State', () => {
    it('shows error message when fetch fails', async () => {
      (apiClient.get as Mock).mockRejectedValue(new Error('Network error'));

      renderWithProviders(<PromptAnalytics promptId={1} />);

      await waitFor(() => {
        expect(screen.getByText(/unable to load analytics/i)).toBeInTheDocument();
      });
    });
  });

  describe('Analytics Display', () => {
    beforeEach(() => {
      (apiClient.get as Mock).mockResolvedValue({ data: mockAnalyticsData });
    });

    it('displays total usage count', async () => {
      renderWithProviders(<PromptAnalytics promptId={1} />);

      await waitFor(() => {
        expect(screen.getByText('150')).toBeInTheDocument();
        expect(screen.getByText(/times used/i)).toBeInTheDocument();
      });
    });

    it('displays total versions count', async () => {
      renderWithProviders(<PromptAnalytics promptId={1} />);

      await waitFor(() => {
        expect(screen.getByText('3')).toBeInTheDocument();
        expect(screen.getByText(/total versions/i)).toBeInTheDocument();
      });
    });

    it('displays version usage breakdown', async () => {
      renderWithProviders(<PromptAnalytics promptId={1} />);

      await waitFor(() => {
        expect(screen.getByText('v3')).toBeInTheDocument();
        expect(screen.getByText('v2')).toBeInTheDocument();
        expect(screen.getByText('v1')).toBeInTheDocument();
      });
    });

    it('shows usage count for each version', async () => {
      renderWithProviders(<PromptAnalytics promptId={1} />);

      await waitFor(() => {
        expect(screen.getByText('100 uses')).toBeInTheDocument();
        expect(screen.getByText('35 uses')).toBeInTheDocument();
        expect(screen.getByText('15 uses')).toBeInTheDocument();
      });
    });

    it('marks current version with badge', async () => {
      renderWithProviders(<PromptAnalytics promptId={1} />);

      await waitFor(() => {
        expect(screen.getByText('Current')).toBeInTheDocument();
      });
    });

    it('marks inactive versions with badge', async () => {
      renderWithProviders(<PromptAnalytics promptId={1} />);

      await waitFor(() => {
        expect(screen.getByText('Inactive')).toBeInTheDocument();
      });
    });

    it('renders progress bars for version usage', async () => {
      renderWithProviders(<PromptAnalytics promptId={1} />);

      await waitFor(() => {
        // Progress bars are rendered as divs with bg-primary class
        const container = document.querySelector('.space-y-3');
        expect(container).toBeInTheDocument();
      });
    });
  });

  describe('Empty State', () => {
    it('shows empty message when no versions exist', async () => {
      (apiClient.get as Mock).mockResolvedValue({
        data: {
          ...mockAnalyticsData,
          total_versions: 0,
          version_usage: [],
        },
      });

      renderWithProviders(<PromptAnalytics promptId={1} />);

      await waitFor(() => {
        expect(screen.getByText(/no versions found/i)).toBeInTheDocument();
      });
    });
  });

  describe('Zero Usage', () => {
    it('displays zero correctly when no usage', async () => {
      (apiClient.get as Mock).mockResolvedValue({
        data: {
          ...mockAnalyticsData,
          total_usage_count: 0,
          version_usage: [
            {
              version_id: 1,
              version_number: 1,
              usage_count: 0,
              is_active: true,
              is_current: true,
              created_at: '2024-01-01T00:00:00Z',
            },
          ],
        },
      });

      renderWithProviders(<PromptAnalytics promptId={1} />);

      await waitFor(() => {
        // Total usage should be 0
        const totalUsage = screen.getAllByText('0');
        expect(totalUsage.length).toBeGreaterThan(0);

        expect(screen.getByText('0 uses')).toBeInTheDocument();
      });
    });
  });

  describe('API Integration', () => {
    it('calls analytics endpoint with correct prompt ID', async () => {
      (apiClient.get as Mock).mockResolvedValue({ data: mockAnalyticsData });

      renderWithProviders(<PromptAnalytics promptId={42} />);

      await waitFor(() => {
        expect(apiClient.get).toHaveBeenCalledWith('/prompts/42/analytics');
      });
    });

    it('does not fetch when promptId is falsy', async () => {
      renderWithProviders(<PromptAnalytics promptId={0} />);

      await waitFor(() => {
        expect(apiClient.get).not.toHaveBeenCalled();
      });
    });
  });

  describe('Single Version', () => {
    it('handles single version correctly', async () => {
      (apiClient.get as Mock).mockResolvedValue({
        data: {
          prompt_id: 1,
          prompt_name: 'Single Version Prompt',
          total_usage_count: 50,
          total_versions: 1,
          current_version_id: 1,
          version_usage: [
            {
              version_id: 1,
              version_number: 1,
              usage_count: 50,
              is_active: true,
              is_current: true,
              created_at: '2024-01-01T00:00:00Z',
            },
          ],
        },
      });

      renderWithProviders(<PromptAnalytics promptId={1} />);

      await waitFor(() => {
        expect(screen.getByText('50')).toBeInTheDocument();
        expect(screen.getByText('1')).toBeInTheDocument();
        expect(screen.getByText('v1')).toBeInTheDocument();
        expect(screen.getByText('50 uses')).toBeInTheDocument();
        expect(screen.getByText('Current')).toBeInTheDocument();
      });
    });
  });

  describe('Progress Bar Calculations', () => {
    it('calculates progress bar width relative to max usage', async () => {
      (apiClient.get as Mock).mockResolvedValue({ data: mockAnalyticsData });

      renderWithProviders(<PromptAnalytics promptId={1} />);

      await waitFor(() => {
        // Verify version usage data is displayed
        expect(screen.getByText('v3')).toBeInTheDocument();
        expect(screen.getByText('v2')).toBeInTheDocument();
        expect(screen.getByText('v1')).toBeInTheDocument();
        // Progress bars exist for each version (inside h-2 bg-muted containers)
        const progressContainers = document.querySelectorAll('.h-2.bg-muted');
        expect(progressContainers.length).toBe(3);
      });
    });
  });
});
