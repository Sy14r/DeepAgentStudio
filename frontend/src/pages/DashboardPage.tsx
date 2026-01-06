import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui';
import { Bot, Wrench, FileText, Play, History, TrendingUp } from 'lucide-react';
import { Link } from 'react-router-dom';

interface StatCardProps {
  title: string;
  value: string | number;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  href: string;
}

function StatCard({ title, value, description, icon: Icon, href }: StatCardProps) {
  return (
    <Link to={href}>
      <Card className="hover:bg-accent/50 transition-colors cursor-pointer">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">{title}</CardTitle>
          <Icon className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{value}</div>
          <p className="text-xs text-muted-foreground">{description}</p>
        </CardContent>
      </Card>
    </Link>
  );
}

export function DashboardPage() {
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
          value="-"
          description="Active agents"
          icon={Bot}
          href="/agents"
        />
        <StatCard
          title="Tools"
          value="-"
          description="Available tools"
          icon={Wrench}
          href="/tools"
        />
        <StatCard
          title="Prompts"
          value="-"
          description="Saved prompts"
          icon={FileText}
          href="/prompts"
        />
        <StatCard
          title="Sessions"
          value="-"
          description="Total sessions"
          icon={History}
          href="/sessions"
        />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
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
              className="text-sm text-primary hover:underline"
            >
              Open Playground →
            </Link>
          </CardContent>
        </Card>

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
            <p className="text-sm text-muted-foreground">
              No recent activity. Start a session in the playground to see activity here.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
