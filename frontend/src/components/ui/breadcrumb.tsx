import * as React from 'react';
import { Link } from 'react-router-dom';
import { ChevronRight, Home } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface BreadcrumbItem {
  label: string;
  href?: string;
  icon?: React.ComponentType<{ className?: string }>;
}

export interface BreadcrumbProps extends React.HTMLAttributes<HTMLElement> {
  items: BreadcrumbItem[];
  homeHref?: string;
  showHome?: boolean;
}

const Breadcrumb = React.forwardRef<HTMLElement, BreadcrumbProps>(
  ({ className, items, homeHref = '/', showHome = false, ...props }, ref) => {
    return (
      <nav
        ref={ref}
        aria-label="Breadcrumb"
        className={cn('flex items-center text-sm', className)}
        {...props}
      >
        <ol className="flex items-center gap-1.5">
          {showHome && (
            <>
              <li>
                <Link
                  to={homeHref}
                  className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground transition-colors"
                >
                  <Home className="h-4 w-4" />
                </Link>
              </li>
              <li className="text-muted-foreground/60">
                <ChevronRight className="h-3.5 w-3.5" />
              </li>
            </>
          )}
          {items.map((item, index) => {
            const isLast = index === items.length - 1;
            const Icon = item.icon;

            return (
              <React.Fragment key={index}>
                <li>
                  {item.href && !isLast ? (
                    <Link
                      to={item.href}
                      className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground transition-colors"
                    >
                      {Icon && <Icon className="h-4 w-4" />}
                      <span>{item.label}</span>
                    </Link>
                  ) : (
                    <span
                      className={cn(
                        'flex items-center gap-1.5',
                        isLast ? 'font-medium text-foreground' : 'text-muted-foreground'
                      )}
                    >
                      {Icon && <Icon className="h-4 w-4" />}
                      <span className={isLast ? 'truncate max-w-[200px]' : undefined}>
                        {item.label}
                      </span>
                    </span>
                  )}
                </li>
                {!isLast && (
                  <li className="text-muted-foreground/60">
                    <ChevronRight className="h-3.5 w-3.5" />
                  </li>
                )}
              </React.Fragment>
            );
          })}
        </ol>
      </nav>
    );
  }
);
Breadcrumb.displayName = 'Breadcrumb';

export { Breadcrumb };
