import { describe, it, expect, beforeEach } from 'vitest';
import { useAuthStore } from '../authStore';

describe('authStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    useAuthStore.setState({
      user: null,
      token: null,
      isAuthenticated: false,
    });
  });

  describe('initial state', () => {
    it('should have null user and token initially', () => {
      const state = useAuthStore.getState();
      expect(state.user).toBeNull();
      expect(state.token).toBeNull();
      expect(state.isAuthenticated).toBe(false);
    });
  });

  describe('login', () => {
    it('should set user, token and isAuthenticated on login', () => {
      const mockUser = {
        id: 1,
        username: 'testuser',
        email: 'test@example.com',
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
      };
      const mockToken = 'test-token-123';

      useAuthStore.getState().login(mockToken, mockUser);

      const state = useAuthStore.getState();
      expect(state.user).toEqual(mockUser);
      expect(state.token).toBe(mockToken);
      expect(state.isAuthenticated).toBe(true);
    });
  });

  describe('logout', () => {
    it('should clear user, token and isAuthenticated on logout', () => {
      // First login
      const mockUser = {
        id: 1,
        username: 'testuser',
        email: 'test@example.com',
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
      };
      useAuthStore.getState().login('test-token', mockUser);

      // Then logout
      useAuthStore.getState().logout();

      const state = useAuthStore.getState();
      expect(state.user).toBeNull();
      expect(state.token).toBeNull();
      expect(state.isAuthenticated).toBe(false);
    });
  });

  describe('updateUser', () => {
    it('should update user data', () => {
      const mockUser = {
        id: 1,
        username: 'testuser',
        email: 'test@example.com',
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
      };
      useAuthStore.getState().login('test-token', mockUser);

      const updatedUser = {
        ...mockUser,
        username: 'updateduser',
        email: 'updated@example.com',
      };
      useAuthStore.getState().updateUser(updatedUser);

      const state = useAuthStore.getState();
      expect(state.user?.username).toBe('updateduser');
      expect(state.user?.email).toBe('updated@example.com');
    });
  });
});
