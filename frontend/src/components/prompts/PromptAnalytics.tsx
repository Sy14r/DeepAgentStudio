import { useQuery } from '@tanstack/react-query';
import {
  Badge,
  Spinner,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui';
import { apiClient } from '@/api/client';
import { BarChart3, TrendingUp, History, CheckCircle2 } from 'lucide-react';

interface VersionUsage {
  version_id: number;
  version_number: number;
  usage_count: number;
  is_active: boolean;
  is_current: boolean;
  created_at: string | null;
}

interface PromptAnalyticsData {
  prompt_id: number;
  prompt_name: string;
  total_usage_count: number;
  total_versions: number;
  current_version_id: number | null;
  version_usage: VersionUsage[];
}

interface PromptAnalyticsProps {
  promptId: number;
}

function usePromptAnalytics(promptId: number) {
  return useQuery({
    queryKey: ['prompt-analytics', promptId],
    queryFn: async (): Promise<PromptAnalyticsData> => {
      const response = await apiClient.get<PromptAnalyticsData>(`/prompts/${promptId}/analytics`);
      return response.data;
    },
    enabled: !!promptId,
  });
}

export function PromptAnalytics({ promptId }: PromptAnalyticsProps) {
  const { data: analytics, isLoading, error } = usePromptAnalytics(promptId);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Spinner className="h-6 w-6" />
      </div>
    );
  }

  if (error || !analytics) {
    return (
      <div className="text-sm text-muted-foreground py-4">
        Unable to load analytics
      </div>
    );
  }

  // Calculate max usage for progress bars
  const maxUsage = Math.max(...analytics.version_usage.map((v) => v.usage_count), 1);

  return (
    <div className="space-y-4">
      {/* Summary Stats */}
      <div className="grid grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <TrendingUp className="h-4 w-4" />
              Total Usage
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{analytics.total_usage_count}</div>
            <p className="text-xs text-muted-foreground">times used</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <History className="h-4 w-4" />
              Versions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{analytics.total_versions}</div>
            <p className="text-xs text-muted-foreground">total versions</p>
          </CardContent>
        </Card>
      </div>

      {/* Version Usage Breakdown */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <BarChart3 className="h-4 w-4" />
            Usage by Version
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {analytics.version_usage.map((version) => (
              <div key={version.version_id} className="space-y-1">
                <div className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">v{version.version_number}</span>
                    {version.is_current && (
                      <Badge variant="default" className="text-xs">
                        <CheckCircle2 className="h-3 w-3 mr-1" />
                        Current
                      </Badge>
                    )}
                    {!version.is_active && (
                      <Badge variant="secondary" className="text-xs">
                        Inactive
                      </Badge>
                    )}
                  </div>
                  <span className="text-muted-foreground">{version.usage_count} uses</span>
                </div>
                {/* Progress bar */}
                <div className="h-2 bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary transition-all duration-300"
                    style={{ width: `${(version.usage_count / maxUsage) * 100}%` }}
                  />
                </div>
              </div>
            ))}

            {analytics.version_usage.length === 0 && (
              <p className="text-sm text-muted-foreground text-center py-4">
                No versions found
              </p>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
