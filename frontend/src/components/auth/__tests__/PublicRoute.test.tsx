import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { PublicRoute } from '../PublicRoute';
import { useAuthStore } from '@/stores/authStore';

function LoginPage() {
  return <div>Login Page</div>;
}

function DashboardPage() {
  return <div>Dashboard Page</div>;
}

function renderWithRouter(isAuthenticated: boolean) {
  // Set auth state
  useAuthStore.setState({ isAuthenticated });

  return render(
    <MemoryRouter initialEntries={['/login']}>
      <Routes>
        <Route
          path="/login"
          element={
            <PublicRoute>
              <LoginPage />
            </PublicRoute>
          }
        />
        <Route path="/" element={<DashboardPage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe('PublicRoute', () => {
  beforeEach(() => {
    useAuthStore.setState({
      user: null,
      token: null,
      isAuthenticated: false,
    });
  });

  it('should render children when not authenticated', () => {
    renderWithRouter(false);
    expect(screen.getByText('Login Page')).toBeInTheDocument();
  });

  it('should redirect to dashboard when authenticated', () => {
    renderWithRouter(true);
    expect(screen.getByText('Dashboard Page')).toBeInTheDocument();
    expect(screen.queryByText('Login Page')).not.toBeInTheDocument();
  });
});
