import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { Sidebar } from '../Sidebar';
import { useUIStore } from '@/stores/uiStore';

function renderSidebar(sidebarOpen = true) {
  useUIStore.setState({ sidebarOpen });

  return render(
    <MemoryRouter>
      <Sidebar />
    </MemoryRouter>
  );
}

describe('Sidebar', () => {
  beforeEach(() => {
    useUIStore.setState({ sidebarOpen: true, theme: 'system' });
  });

  it('should render when sidebar is open', () => {
    renderSidebar(true);
    expect(screen.getByText('DeepAgent Studio')).toBeInTheDocument();
  });

  it('should not render when sidebar is closed', () => {
    renderSidebar(false);
    expect(screen.queryByText('DeepAgent Studio')).not.toBeInTheDocument();
  });

  it('should render main navigation items', () => {
    renderSidebar();
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Playground')).toBeInTheDocument();
  });

  it('should render management navigation items', () => {
    renderSidebar();
    expect(screen.getByText('Agents')).toBeInTheDocument();
    expect(screen.getByText('Tools')).toBeInTheDocument();
    expect(screen.getByText('Prompts')).toBeInTheDocument();
  });

  it('should render activity navigation items', () => {
    renderSidebar();
    expect(screen.getByText('Sessions')).toBeInTheDocument();
  });

  it('should render settings navigation item', () => {
    renderSidebar();
    expect(screen.getByText('Settings')).toBeInTheDocument();
  });

  it('should have navigation links with correct hrefs', () => {
    renderSidebar();

    const dashboardLink = screen.getByRole('link', { name: /dashboard/i });
    expect(dashboardLink).toHaveAttribute('href', '/');

    const playgroundLink = screen.getByRole('link', { name: /playground/i });
    expect(playgroundLink).toHaveAttribute('href', '/playground');

    const agentsLink = screen.getByRole('link', { name: /agents/i });
    expect(agentsLink).toHaveAttribute('href', '/agents');

    const settingsLink = screen.getByRole('link', { name: /settings/i });
    expect(settingsLink).toHaveAttribute('href', '/settings');
  });

  it('should collapse sidebar when collapse button is clicked', async () => {
    const user = userEvent.setup();
    renderSidebar(true);

    // There are multiple collapse buttons (header and footer), use the first one
    const collapseButtons = screen.getAllByRole('button', { name: /collapse sidebar/i });
    await user.click(collapseButtons[0]);

    expect(useUIStore.getState().sidebarOpen).toBe(false);
  });

  it('should render section headers', () => {
    renderSidebar();
    expect(screen.getByText('Manage')).toBeInTheDocument();
    expect(screen.getByText('Activity')).toBeInTheDocument();
  });
});
