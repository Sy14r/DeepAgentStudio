import { Outlet } from 'react-router-dom';
import { Header } from './Header';
import { Sidebar } from './Sidebar';
import { useUIStore } from '@/stores/uiStore';
import { cn } from '@/lib/utils';

export function AppLayout() {
  const { sidebarOpen } = useUIStore();

  return (
    <div className="min-h-screen bg-background">
      <Sidebar />
      <div
        className={cn(
          'flex min-h-screen flex-col transition-all duration-300',
          sidebarOpen ? 'pl-64' : 'pl-16'
        )}
      >
        <Header />
        <main className="flex-1 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
