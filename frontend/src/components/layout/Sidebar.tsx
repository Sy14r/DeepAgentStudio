import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Bot,
  Wrench,
  FileText,
  Play,
  History,
  Settings,
  ChevronLeft,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useUIStore } from '@/stores/uiStore';
import { Button, ScrollArea, Separator, Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui';

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
