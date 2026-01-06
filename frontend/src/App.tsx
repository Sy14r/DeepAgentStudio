import { Routes, Route, Navigate } from 'react-router-dom';
import { ProtectedRoute, PublicRoute } from '@/components/auth';
import { AppLayout } from '@/components/layout';
import {
  LoginPage,
  RegisterPage,
  DashboardPage,
  AgentsPage,
  AgentEditorPage,
  ToolsPage,
  ToolEditorPage,
  MCPServerEditorPage,
  PromptsPage,
  PlaygroundPage,
  SessionsPage,
  SettingsPage,
} from '@/pages';

function App() {
  return (
    <Routes>
      {/* Public routes */}
      <Route
        path="/login"
        element={
          <PublicRoute>
            <LoginPage />
          </PublicRoute>
        }
      />
      <Route
        path="/register"
        element={
          <PublicRoute>
            <RegisterPage />
          </PublicRoute>
        }
      />

      {/* Protected routes */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<DashboardPage />} />

        {/* Agents */}
        <Route path="agents" element={<AgentsPage />} />
        <Route path="agents/new" element={<AgentEditorPage />} />
        <Route path="agents/:id" element={<AgentEditorPage />} />
        <Route path="agents/:id/edit" element={<AgentEditorPage />} />

        {/* Tools */}
        <Route path="tools" element={<ToolsPage />} />
        <Route path="tools/new" element={<ToolEditorPage />} />
        <Route path="tools/:id" element={<ToolEditorPage />} />
        <Route path="tools/:id/edit" element={<ToolEditorPage />} />
        {/* MCP Servers (under tools) */}
        <Route path="tools/mcp/new" element={<MCPServerEditorPage />} />
        <Route path="tools/mcp/:id/edit" element={<MCPServerEditorPage />} />

        {/* Prompts */}
        <Route path="prompts" element={<PromptsPage />} />
        <Route path="prompts/new" element={<PromptsPage />} />
        <Route path="prompts/:id" element={<PromptsPage />} />

        {/* Playground */}
        <Route path="playground" element={<PlaygroundPage />} />
        <Route path="playground/:agentId" element={<PlaygroundPage />} />

        {/* Sessions */}
        <Route path="sessions" element={<SessionsPage />} />
        <Route path="sessions/:id" element={<SessionsPage />} />

        {/* Settings */}
        <Route path="settings" element={<SettingsPage />} />
        <Route path="settings/providers" element={<SettingsPage />} />
      </Route>

      {/* Catch-all redirect */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
