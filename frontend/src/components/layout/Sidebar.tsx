import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  Bot,
  Sparkles,
  Wrench,
  FileText,
  Play,
  History,
  Settings,
  ChevronLeft,
  Eye,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useUIStore } from '@/stores/uiStore';
import { Button, ScrollArea, Separator, Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui';
import { useSessions } from '@/api/hooks';

interface NavItem {
  title: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
}

const mainNavItems: NavItem[] = [
  { title: 'Dashboard', href: '/', icon: LayoutDashboard },
  { title: 'Playground', href: '/playground', icon: Play },
];

const managementNavItems: NavItem[] = [
  { title: 'Agents', href: '/agents', icon: Bot },
  { title: 'Agent Types', href: '/agent-types', icon: Sparkles },
  { title: 'Tools', href: '/tools', icon: Wrench },
  { title: 'Prompts', href: '/prompts', icon: FileText },
];

const activityNavItems: NavItem[] = [
  { title: 'Sessions', href: '/sessions', icon: History },
];

// Settings is now handled directly in the footer section

function NavSection({ title, items, collapsed }: { title?: string; items: NavItem[]; collapsed?: boolean }) {
  return (
    <div className={cn("py-2", collapsed ? "px-2" : "px-3")}>
      {title && !collapsed && (
        <h2 className="mb-2 px-4 text-xs font-semibold tracking-tight text-muted-foreground uppercase">
          {title}
        </h2>
      )}
      <div className={cn("space-y-1", collapsed && "flex flex-col items-center")}>
        {items.map((item) => {
          const navLink = (
            <NavLink
              to={item.href}
              className={({ isActive }) =>
                cn(
                  'flex items-center rounded-lg font-medium transition-all duration-150',
                  collapsed
                    ? 'justify-center w-10 h-10'
                    : 'gap-3 px-3 py-2 text-sm',
                  isActive
                    ? 'bg-primary text-primary-foreground shadow-sm'
                    : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                )
              }
            >
              <item.icon className={cn("shrink-0", collapsed ? "h-5 w-5" : "h-4 w-4")} />
              {!collapsed && <span>{item.title}</span>}
            </NavLink>
          );

          if (collapsed) {
            return (
              <Tooltip key={item.href} delayDuration={0}>
                <TooltipTrigger asChild>
                  <span className="inline-block">
                    {navLink}
                  </span>
                </TooltipTrigger>
                <TooltipContent side="right" className="font-medium">
                  {item.title}
                </TooltipContent>
              </Tooltip>
            );
          }

          return <span key={item.href}>{navLink}</span>;
        })}
      </div>
    </div>
  );
}

function RecentSessions() {
  const { data } = useSessions({ pageSize: 5 });
  const sessions = data?.sessions || [];

  if (sessions.length === 0) {
    return (
      <div className="px-3 py-2">
        <h2 className="mb-2 px-4 text-xs font-semibold tracking-tight text-muted-foreground uppercase">
          Recent Sessions
        </h2>
        <p className="px-4 text-xs text-muted-foreground">No sessions yet</p>
      </div>
    );
  }

  return (
    <div className="px-3 py-2">
      <h2 className="mb-2 px-4 text-xs font-semibold tracking-tight text-muted-foreground uppercase">
        Recent Sessions
      </h2>
      <div className="space-y-1">
        {sessions.map((session) => (
          <SessionNavItem key={session.id} session={session} />
        ))}
      </div>
    </div>
  );
}

interface SessionNavItemProps {
  session: {
    id: number;
    title: string | null;
    agent_id: number | null;
  };
}

function SessionNavItem({ session }: SessionNavItemProps) {
  const navigate = useNavigate();
  const fullTitle = session.title || `Session #${session.id}`;
  const displayTitle = fullTitle.length > 20 ? `${fullTitle.slice(0, 20)}...` : fullTitle;

  const handleView = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    navigate(`/sessions/${session.id}`);
  };

  const handleResume = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (session.agent_id) {
      navigate(`/playground/${session.agent_id}/session/${session.id}`);
    }
  };

  return (
    <Tooltip delayDuration={300}>
      <TooltipTrigger asChild>
        <div className="group relative">
          <NavLink
            to={`/sessions/${session.id}`}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150',
                isActive
                  ? 'bg-primary text-primary-foreground shadow-sm'
                  : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
              )
            }
          >
            <span className="truncate flex-1 pr-12">{displayTitle}</span>
          </NavLink>

          {/* Hover action buttons */}
          <div className="absolute right-2 top-1/2 -translate-y-1/2 hidden group-hover:flex items-center gap-1">
            <Tooltip delayDuration={0}>
              <TooltipTrigger asChild>
                <button
                  onClick={handleView}
                  className="p-1 rounded hover:bg-background/80 text-muted-foreground hover:text-foreground transition-colors"
                >
                  <Eye className="h-3.5 w-3.5" />
                </button>
              </TooltipTrigger>
              <TooltipContent side="top" className="text-xs">
                View Details
              </TooltipContent>
            </Tooltip>

            {session.agent_id && (
              <Tooltip delayDuration={0}>
                <TooltipTrigger asChild>
                  <button
                    onClick={handleResume}
                    className="p-1 rounded hover:bg-background/80 text-muted-foreground hover:text-foreground transition-colors"
                  >
                    <Play className="h-3.5 w-3.5" />
                  </button>
                </TooltipTrigger>
                <TooltipContent side="top" className="text-xs">
                  Resume in Playground
                </TooltipContent>
              </Tooltip>
            )}
          </div>
        </div>
      </TooltipTrigger>
      <TooltipContent side="right" className="max-w-xs">
        {fullTitle}
      </TooltipContent>
    </Tooltip>
  );
}

export function Sidebar() {
  const { sidebarOpen, setSidebarOpen } = useUIStore();
  const collapsed = !sidebarOpen;

  return (
    <TooltipProvider delayDuration={0}>
      <aside className={cn(
        "fixed left-0 top-0 z-30 h-screen border-r bg-background transition-all duration-200 ease-in-out",
        collapsed ? "w-16" : "w-64"
      )}>
        {/* Header */}
        <div className={cn(
          "flex h-14 items-center border-b",
          collapsed ? "justify-center px-2" : "px-4"
        )}>
          {collapsed ? (
            <Tooltip delayDuration={0}>
              <TooltipTrigger asChild>
                <NavLink
                  to="/"
                  className="flex items-center justify-center w-10 h-10 rounded-lg hover:bg-accent transition-colors"
                >
                  <Bot className="h-6 w-6 text-primary" />
                </NavLink>
              </TooltipTrigger>
              <TooltipContent side="right">DeepAgent Studio</TooltipContent>
            </Tooltip>
          ) : (
            <>
              <NavLink to="/" className="flex items-center gap-2 font-semibold">
                <Bot className="h-6 w-6 text-primary" />
                <span>DeepAgent Studio</span>
              </NavLink>
              <Button
                variant="ghost"
                size="icon"
                className="ml-auto h-8 w-8"
                onClick={() => setSidebarOpen(false)}
                aria-label="Collapse sidebar"
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
            </>
          )}
        </div>

        {/* Navigation */}
        <ScrollArea className="h-[calc(100vh-3.5rem-3rem)]">
          <div className="flex flex-col">
            <div className="py-2">
              <NavSection items={mainNavItems} collapsed={collapsed} />
              <Separator className={cn("my-2", collapsed && "mx-3")} />
              <NavSection title="Manage" items={managementNavItems} collapsed={collapsed} />
              <Separator className={cn("my-2", collapsed && "mx-3")} />
              <NavSection title="Activity" items={activityNavItems} collapsed={collapsed} />
              {!collapsed && (
                <>
                  <Separator className="my-2" />
                  <RecentSessions />
                </>
              )}
            </div>
          </div>
        </ScrollArea>

        {/* Footer with Settings */}
        <div className={cn(
          "absolute bottom-0 left-0 right-0 border-t bg-background",
          collapsed ? "px-2 py-2" : "px-3 py-2"
        )}>
          {/* Settings */}
          {collapsed ? (
            <Tooltip delayDuration={0}>
              <TooltipTrigger asChild>
                <span className="inline-block">
                  <NavLink
                    to="/settings"
                    className={({ isActive }) =>
                      cn(
                        'flex items-center justify-center w-10 h-10 rounded-lg font-medium transition-all duration-150',
                        isActive
                          ? 'bg-primary text-primary-foreground shadow-sm'
                          : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                      )
                    }
                  >
                    <Settings className="h-5 w-5" />
                  </NavLink>
                </span>
              </TooltipTrigger>
              <TooltipContent side="right">Settings</TooltipContent>
            </Tooltip>
          ) : (
            <NavLink
              to="/settings"
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150',
                  isActive
                    ? 'bg-primary text-primary-foreground shadow-sm'
                    : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                )
              }
            >
              <Settings className="h-4 w-4" />
              <span>Settings</span>
            </NavLink>
          )}
        </div>
      </aside>
    </TooltipProvider>
  );
}
