import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient, getErrorMessage } from '@/api/client';
import { useAuthStore } from '@/stores/authStore';
import { LoginRequest, LoginResponse, RegisterRequest, User } from '@/api/types';

export function useLogin() {
  const { login } = useAuthStore();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: LoginRequest): Promise<LoginResponse> => {
      // OAuth2PasswordRequestForm expects form data, not JSON
      const formData = new URLSearchParams();
      formData.append('username', data.username);
      formData.append('password', data.password);
      const response = await apiClient.post<LoginResponse>('/auth/login', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });
      return response.data;
    },
    onSuccess: async (data) => {
      // Fetch user profile after login
      const userResponse = await apiClient.get<User>('/auth/me', {
        headers: { Authorization: `Bearer ${data.access_token}` },
      });
      login(data.access_token, userResponse.data);
      queryClient.invalidateQueries();
    },
  });
}

export function useRegister() {
  return useMutation({
    mutationFn: async (data: RegisterRequest): Promise<User> => {
      const response = await apiClient.post<User>('/auth/register', data);
      return response.data;
    },
  });
}

export function useCurrentUser() {
  const { isAuthenticated } = useAuthStore();

  return useQuery({
    queryKey: ['currentUser'],
    queryFn: async (): Promise<User> => {
      const response = await apiClient.get<User>('/auth/me');
      return response.data;
    },
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useLogout() {
  const { logout } = useAuthStore();
  const queryClient = useQueryClient();

  return () => {
    logout();
    queryClient.clear();
  };
}

export { getErrorMessage };
