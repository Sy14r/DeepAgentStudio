import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { DashboardPage } from '../DashboardPage';

function renderDashboardPage() {
  return render(
    <MemoryRouter>
      <DashboardPage />
    </MemoryRouter>
  );
}

describe('DashboardPage', () => {
  it('should render dashboard title', () => {
    renderDashboardPage();
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
  });

  it('should render welcome message', () => {
    renderDashboardPage();
    expect(
      screen.getByText(/Welcome to DeepAgent Studio/i)
    ).toBeInTheDocument();
  });

  it('should render stat cards', () => {
    renderDashboardPage();
    expect(screen.getByText('Agents')).toBeInTheDocument();
    expect(screen.getByText('Tools')).toBeInTheDocument();
    expect(screen.getByText('Prompts')).toBeInTheDocument();
    expect(screen.getByText('Sessions')).toBeInTheDocument();
  });

  it('should render quick start section', () => {
    renderDashboardPage();
    expect(screen.getByText('Quick Start')).toBeInTheDocument();
    expect(screen.getByText(/Open Playground/i)).toBeInTheDocument();
  });

  it('should render recent activity section', () => {
    renderDashboardPage();
    expect(screen.getByText('Recent Activity')).toBeInTheDocument();
  });

  it('should have navigation links to other pages', () => {
    renderDashboardPage();

    // Check that stat cards link to their respective pages
    const links = screen.getAllByRole('link');
    const hrefs = links.map((link) => link.getAttribute('href'));

    expect(hrefs).toContain('/agents');
    expect(hrefs).toContain('/tools');
    expect(hrefs).toContain('/prompts');
    expect(hrefs).toContain('/sessions');
    expect(hrefs).toContain('/playground');
  });
});
