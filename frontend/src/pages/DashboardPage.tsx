import { Card, CardContent, CardDescription, CardHeader, CardTitle, Spinner } from '@/components/ui';
import { Bot, Wrench, FileText, Play, History, TrendingUp } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useAgents, useTools, usePrompts, useSessions } from '@/api/hooks';
import { formatDistanceToNow } from 'date-fns';

interface StatCardProps {
  title: string;
  value: string | number;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  href: string;
  isLoading?: boolean;
}

function StatCard({ title, value, description, icon: Icon, href, isLoading }: StatCardProps) {
  return (
    <Link to={href}>
      <Card className="hover:bg-accent/50 transition-colors cursor-pointer">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">{title}</CardTitle>
          <Icon className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {isLoading ? <Spinner className="h-6 w-6" /> : value}
          </div>
          <p className="text-xs text-muted-foreground">{description}</p>
        </CardContent>
      </Card>
    </Link>
  );
}

export function DashboardPage() {
  // Fetch counts with minimal page size since we only need totals
  const { data: agentsData, isLoading: agentsLoading } = useAgents({ pageSize: 1 });
  const { data: toolsData, isLoading: toolsLoading } = useTools({ pageSize: 1 });
  const { data: promptsData, isLoading: promptsLoading } = usePrompts({ pageSize: 1 });
  const { data: sessionsData, isLoading: sessionsLoading } = useSessions({ pageSize: 5 });

  const recentSessions = sessionsData?.sessions || [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Welcome to DeepAgent Studio. Manage your AI agents and tools.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Agents"
          value={agentsData?.total ?? 0}
          description="Active agents"
          icon={Bot}
          href="/agents"
          isLoading={agentsLoading}
        />
        <StatCard
          title="Tools"
          value={toolsData?.total ?? 0}
          description="Available tools"
          icon={Wrench}
          href="/tools"
          isLoading={toolsLoading}
        />
        <StatCard
          title="Prompts"
          value={promptsData?.total ?? 0}
          description="Saved prompts"
          icon={FileText}
          href="/prompts"
          isLoading={promptsLoading}
        />
        <StatCard
          title="Sessions"
          value={sessionsData?.total ?? 0}
          description="Total sessions"
          icon={History}
          href="/sessions"
          isLoading={sessionsLoading}
        />
      </div>

      {/* Quick Start - Full Width */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Play className="h-5 w-5" />
            Quick Start
          </CardTitle>
          <CardDescription>
            Get started with the playground
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground mb-4">
            Test your agents in the interactive playground. Select an agent, send messages, and view execution traces.
          </p>
          <Link
            to="/playground"
            className="inline-flex items-center gap-2 text-sm font-medium text-primary hover:underline"
          >
            Open Playground →
          </Link>
        </CardContent>
      </Card>

      {/* Recent Activity - Full Width */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            Recent Activity
          </CardTitle>
          <CardDescription>
            Your latest sessions
          </CardDescription>
        </CardHeader>
        <CardContent>
          {sessionsLoading ? (
            <div className="flex justify-center py-4">
              <Spinner className="h-6 w-6" />
            </div>
          ) : recentSessions.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No recent activity. Start a session in the playground to see activity here.
            </p>
          ) : (
            <div className="space-y-3">
              {recentSessions.map((session) => (
                <Link
                  key={session.id}
                  to={`/sessions/${session.id}`}
                  className="block p-2 -mx-2 rounded-md hover:bg-accent/50 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">
                        {session.title || `Session #${session.id}`}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {formatDistanceToNow(new Date(session.started_at), { addSuffix: true })}
                      </p>
                    </div>
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full ${
                        session.status === 'completed'
                          ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                          : session.status === 'failed'
                          ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                          : session.status === 'running'
                          ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                          : 'bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400'
                      }`}
                    >
                      {session.status}
                    </span>
                  </div>
                </Link>
              ))}
              {(sessionsData?.total ?? 0) > 5 && (
                <Link
                  to="/sessions"
                  className="block text-sm text-primary hover:underline pt-2"
                >
                  View all sessions →
                </Link>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
