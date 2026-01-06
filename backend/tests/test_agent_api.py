"""
Tests for Agent API endpoints
"""
import pytest
from fastapi import status


class TestCreateAgent:
    """Test cases for POST /api/v1/agents"""

    def test_create_agent_success(self, client, auth_headers, test_llm_provider):
        """Test successful agent creation"""
        agent_data = {
            "name": "Test Agent",
            "description": "A test agent",
            "agent_type": "ReAct",
            "tags": ["test", "automation"],
            "config": {
                "llm_config": {
                    "provider": "openai",
                    "provider_id": test_llm_provider.id,
                    "model": "gpt-4",
                    "temperature": 0.7,
                    "max_tokens": 2000,
                    "stop_sequences": []
                },
                "reflection_config": {
                    "enabled": False,
                    "depth": 2,
                    "iteration_limit": 5
                },
                "memory_config": {
                    "type": "buffer",
                    "context_window": 10,
                    "retrieval_strategy": "similarity"
                },
                "tool_ids": [],
                "prompt_id": None,
                "system_prompt": "You are a helpful assistant."
            }
        }

        response = client.post("/api/v1/agents", json=agent_data, headers=auth_headers)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Test Agent"
        assert data["description"] == "A test agent"
        assert data["agent_type"] == "ReAct"
        assert data["tags"] == ["test", "automation"]
        assert data["is_active"] is True
        assert data["current_version_id"] is not None
        assert "current_version" in data
        assert data["current_version"]["version_number"] == 1

    def test_create_agent_minimal(self, client, auth_headers, test_llm_provider):
        """Test creating agent with minimal required fields"""
        agent_data = {
            "name": "Minimal Agent",
            "config": {
                "llm_config": {
                    "provider": "openai",
                    "provider_id": test_llm_provider.id,
                    "model": "gpt-4",
                    "temperature": 0.5,
                    "max_tokens": 1000,
                    "stop_sequences": []
                }
            }
        }

        response = client.post("/api/v1/agents", json=agent_data, headers=auth_headers)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Minimal Agent"
        assert data["agent_type"] == "ReAct"  # Default
        assert data["tags"] == []
        assert data["description"] is None

    def test_create_agent_unauthorized(self, client):
        """Test creating agent without authentication"""
        agent_data = {
            "name": "Test Agent",
            "config": {
                "llm_config": {
                    "provider": "openai",
                    "provider_id": 1,
                    "model": "gpt-4",
                    "temperature": 0.7,
                    "max_tokens": 2000,
                    "stop_sequences": []
                }
            }
        }

        response = client.post("/api/v1/agents", json=agent_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_agent_invalid_data(self, client, auth_headers):
        """Test creating agent with invalid data"""
        # Missing required config
        agent_data = {
            "name": "Invalid Agent"
        }

        response = client.post("/api/v1/agents", json=agent_data, headers=auth_headers)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestListAgents:
    """Test cases for GET /api/v1/agents"""

    def test_list_agents_empty(self, client, auth_headers):
        """Test listing agents when none exist"""
        response = client.get("/api/v1/agents", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["agents"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["page_size"] == 50

    def test_list_agents_with_data(self, client, auth_headers, test_llm_provider):
        """Test listing agents with multiple agents"""
        # Create 3 agents
        for i in range(3):
            agent_data = {
                "name": f"Agent {i+1}",
                "config": {
                    "llm_config": {
                        "provider": "openai",
                        "provider_id": test_llm_provider.id,
                        "model": "gpt-4",
                        "temperature": 0.7,
                        "max_tokens": 2000,
                        "stop_sequences": []
                    }
                }
            }
            client.post("/api/v1/agents", json=agent_data, headers=auth_headers)

        response = client.get("/api/v1/agents", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["agents"]) == 3
        assert data["total"] == 3

    def test_list_agents_pagination(self, client, auth_headers, test_llm_provider):
        """Test agent list pagination"""
        # Create 5 agents
        for i in range(5):
            agent_data = {
                "name": f"Agent {i+1}",
                "config": {
                    "llm_config": {
                        "provider": "openai",
                        "provider_id": test_llm_provider.id,
                        "model": "gpt-4",
                        "temperature": 0.7,
                        "max_tokens": 2000,
                        "stop_sequences": []
                    }
                }
            }
            client.post("/api/v1/agents", json=agent_data, headers=auth_headers)

        # Get first page
        response = client.get("/api/v1/agents?skip=0&limit=2", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["agents"]) == 2
        assert data["total"] == 5
        assert data["page"] == 1

        # Get second page
        response = client.get("/api/v1/agents?skip=2&limit=2", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["agents"]) == 2
        assert data["page"] == 2

    def test_list_agents_active_only(self, client, auth_headers, test_llm_provider):
        """Test listing only active agents"""
        # Create 2 active agents
        for i in range(2):
            agent_data = {
                "name": f"Active Agent {i+1}",
                "config": {
                    "llm_config": {
                        "provider": "openai",
                        "provider_id": test_llm_provider.id,
                        "model": "gpt-4",
                        "temperature": 0.7,
                        "max_tokens": 2000,
                        "stop_sequences": []
                    }
                }
            }
            client.post("/api/v1/agents", json=agent_data, headers=auth_headers)

        # Create and soft delete 1 agent
        agent_data = {
            "name": "Inactive Agent",
            "config": {
                "llm_config": {
                    "provider": "openai",
                    "provider_id": test_llm_provider.id,
                    "model": "gpt-4",
                    "temperature": 0.7,
                    "max_tokens": 2000,
                    "stop_sequences": []
                }
            }
        }
        create_response = client.post("/api/v1/agents", json=agent_data, headers=auth_headers)
        agent_id = create_response.json()["id"]
        client.delete(f"/api/v1/agents/{agent_id}", headers=auth_headers)

        # List active only (default)
        response = client.get("/api/v1/agents?active_only=true", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["agents"]) == 2
        assert data["total"] == 2

        # List all (including inactive)
        response = client.get("/api/v1/agents?active_only=false", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["agents"]) == 3
        assert data["total"] == 3

    def test_list_agents_unauthorized(self, client):
        """Test listing agents without authentication"""
        response = client.get("/api/v1/agents")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestGetAgent:
    """Test cases for GET /api/v1/agents/{agent_id}"""

    def test_get_agent_success(self, client, auth_headers, test_llm_provider):
        """Test getting agent details"""
        # Create agent
        agent_data = {
            "name": "Detailed Agent",
            "description": "Agent for detail testing",
            "tags": ["detail", "test"],
            "config": {
                "llm_config": {
                    "provider": "openai",
                    "provider_id": test_llm_provider.id,
                    "model": "gpt-4",
                    "temperature": 0.7,
                    "max_tokens": 2000,
                    "stop_sequences": []
                }
            }
        }
        create_response = client.post("/api/v1/agents", json=agent_data, headers=auth_headers)
        agent_id = create_response.json()["id"]

        # Get agent
        response = client.get(f"/api/v1/agents/{agent_id}", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == agent_id
        assert data["name"] == "Detailed Agent"
        assert data["description"] == "Agent for detail testing"
        assert data["tags"] == ["detail", "test"]
        assert data["current_version"] is not None
        assert data["current_version"]["version_number"] == 1

    def test_get_agent_not_found(self, client, auth_headers):
        """Test getting non-existent agent"""
        response = client.get("/api/v1/agents/99999", headers=auth_headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_agent_unauthorized(self, client):
        """Test getting agent without authentication"""
        response = client.get("/api/v1/agents/1")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestUpdateAgent:
    """Test cases for PUT /api/v1/agents/{agent_id}"""

    def test_update_agent_basic_fields(self, client, auth_headers, test_llm_provider):
        """Test updating agent basic fields without config change"""
        # Create agent
        agent_data = {
            "name": "Original Name",
            "description": "Original description",
            "tags": ["original"],
            "config": {
                "llm_config": {
                    "provider": "openai",
                    "provider_id": test_llm_provider.id,
                    "model": "gpt-4",
                    "temperature": 0.7,
                    "max_tokens": 2000,
                    "stop_sequences": []
                }
            }
        }
        create_response = client.post("/api/v1/agents", json=agent_data, headers=auth_headers)
        agent_id = create_response.json()["id"]
        original_version_id = create_response.json()["current_version_id"]

        # Update basic fields only
        update_data = {
            "name": "Updated Name",
            "description": "Updated description",
            "tags": ["updated", "modified"]
        }
        response = client.put(f"/api/v1/agents/{agent_id}", json=update_data, headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated description"
        assert data["tags"] == ["updated", "modified"]
        # Version should not change
        assert data["current_version_id"] == original_version_id
        assert data["current_version"]["version_number"] == 1

    def test_update_agent_with_config(self, client, auth_headers, test_llm_provider):
        """Test updating agent config creates new version"""
        # Create agent
        agent_data = {
            "name": "Versioned Agent",
            "config": {
                "llm_config": {
                    "provider": "openai",
                    "provider_id": test_llm_provider.id,
                    "model": "gpt-4",
                    "temperature": 0.7,
                    "max_tokens": 2000,
                    "stop_sequences": []
                }
            }
        }
        create_response = client.post("/api/v1/agents", json=agent_data, headers=auth_headers)
        agent_id = create_response.json()["id"]

        # Update with new config
        update_data = {
            "name": "Versioned Agent V2",
            "config": {
                "llm_config": {
                    "provider": "openai",
                    "provider_id": test_llm_provider.id,
                    "model": "gpt-4-turbo",
                    "temperature": 0.8,
                    "max_tokens": 4000,
                    "stop_sequences": []
                }
            }
        }
        response = client.put(f"/api/v1/agents/{agent_id}", json=update_data, headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Versioned Agent V2"
        assert data["current_version"]["version_number"] == 2
        assert data["current_version"]["config"]["llm_config"]["model"] == "gpt-4-turbo"

    def test_update_agent_not_found(self, client, auth_headers):
        """Test updating non-existent agent"""
        update_data = {
            "name": "Updated"
        }
        response = client.put("/api/v1/agents/99999", json=update_data, headers=auth_headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_agent_unauthorized(self, client):
        """Test updating agent without authentication"""
        update_data = {
            "name": "Updated"
        }
        response = client.put("/api/v1/agents/1", json=update_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestDeleteAgent:
    """Test cases for DELETE /api/v1/agents/{agent_id}"""

    def test_delete_agent_soft(self, client, auth_headers, test_llm_provider):
        """Test soft deleting an agent"""
        # Create agent
        agent_data = {
            "name": "Delete Me",
            "config": {
                "llm_config": {
                    "provider": "openai",
                    "provider_id": test_llm_provider.id,
                    "model": "gpt-4",
                    "temperature": 0.7,
                    "max_tokens": 2000,
                    "stop_sequences": []
                }
            }
        }
        create_response = client.post("/api/v1/agents", json=agent_data, headers=auth_headers)
        agent_id = create_response.json()["id"]

        # Soft delete
        response = client.delete(f"/api/v1/agents/{agent_id}", headers=auth_headers)

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify agent still exists but is inactive
        get_response = client.get(f"/api/v1/agents/{agent_id}", headers=auth_headers)
        assert get_response.status_code == status.HTTP_200_OK
        assert get_response.json()["is_active"] is False

    def test_delete_agent_hard(self, client, auth_headers, test_llm_provider):
        """Test hard deleting an agent"""
        # Create agent
        agent_data = {
            "name": "Delete Me Hard",
            "config": {
                "llm_config": {
                    "provider": "openai",
                    "provider_id": test_llm_provider.id,
                    "model": "gpt-4",
                    "temperature": 0.7,
                    "max_tokens": 2000,
                    "stop_sequences": []
                }
            }
        }
        create_response = client.post("/api/v1/agents", json=agent_data, headers=auth_headers)
        agent_id = create_response.json()["id"]

        # Hard delete
        response = client.delete(f"/api/v1/agents/{agent_id}?hard_delete=true", headers=auth_headers)

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify agent no longer exists
        get_response = client.get(f"/api/v1/agents/{agent_id}", headers=auth_headers)
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_agent_not_found(self, client, auth_headers):
        """Test deleting non-existent agent"""
        response = client.delete("/api/v1/agents/99999", headers=auth_headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_agent_unauthorized(self, client):
        """Test deleting agent without authentication"""
        response = client.delete("/api/v1/agents/1")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestAgentVersions:
    """Test cases for GET /api/v1/agents/{agent_id}/versions"""

    def test_list_versions(self, client, auth_headers, test_llm_provider):
        """Test listing agent version history"""
        # Create agent
        agent_data = {
            "name": "Multi-Version Agent",
            "config": {
                "llm_config": {
                    "provider": "openai",
                    "provider_id": test_llm_provider.id,
                    "model": "gpt-3.5-turbo",
                    "temperature": 0.5,
                    "max_tokens": 1000,
                    "stop_sequences": []
                }
            }
        }
        create_response = client.post("/api/v1/agents", json=agent_data, headers=auth_headers)
        agent_id = create_response.json()["id"]

        # Update with new config twice
        for i in range(2):
            update_data = {
                "config": {
                    "llm_config": {
                        "provider": "openai",
                        "provider_id": test_llm_provider.id,
                        "model": f"gpt-4-{i}",
                        "temperature": 0.7 + (i * 0.1),
                        "max_tokens": 2000 + (i * 1000),
                        "stop_sequences": []
                    }
                }
            }
            client.put(f"/api/v1/agents/{agent_id}", json=update_data, headers=auth_headers)

        # List versions
        response = client.get(f"/api/v1/agents/{agent_id}/versions", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        versions = response.json()
        assert len(versions) == 3
        # Versions should be in descending order
        assert versions[0]["version_number"] == 3
        assert versions[1]["version_number"] == 2
        assert versions[2]["version_number"] == 1

    def test_list_versions_not_found(self, client, auth_headers):
        """Test listing versions for non-existent agent"""
        response = client.get("/api/v1/agents/99999/versions", headers=auth_headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_list_versions_unauthorized(self, client):
        """Test listing versions without authentication"""
        response = client.get("/api/v1/agents/1/versions")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestAgentRollback:
    """Test cases for POST /api/v1/agents/{agent_id}/rollback"""

    def test_rollback_agent_success(self, client, auth_headers, test_llm_provider):
        """Test rolling back agent to previous version"""
        # Create agent
        agent_data = {
            "name": "Rollback Agent",
            "config": {
                "llm_config": {
                    "provider": "openai",
                    "provider_id": test_llm_provider.id,
                    "model": "gpt-3.5-turbo",
                    "temperature": 0.5,
                    "max_tokens": 1000,
                    "stop_sequences": []
                }
            }
        }
        create_response = client.post("/api/v1/agents", json=agent_data, headers=auth_headers)
        agent_id = create_response.json()["id"]
        version_1_id = create_response.json()["current_version_id"]

        # Update to create version 2
        update_data = {
            "config": {
                "llm_config": {
                    "provider": "openai",
                    "provider_id": test_llm_provider.id,
                    "model": "gpt-4",
                    "temperature": 0.8,
                    "max_tokens": 4000,
                    "stop_sequences": []
                }
            }
        }
        client.put(f"/api/v1/agents/{agent_id}", json=update_data, headers=auth_headers)

        # Rollback to version 1
        rollback_data = {
            "version_id": version_1_id
        }
        response = client.post(f"/api/v1/agents/{agent_id}/rollback", json=rollback_data, headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["current_version_id"] == version_1_id
        assert data["current_version"]["version_number"] == 1
        assert data["current_version"]["config"]["llm_config"]["model"] == "gpt-3.5-turbo"

    def test_rollback_agent_invalid_version(self, client, auth_headers, test_llm_provider):
        """Test rolling back to non-existent version"""
        # Create agent
        agent_data = {
            "name": "Rollback Agent",
            "config": {
                "llm_config": {
                    "provider": "openai",
                    "provider_id": test_llm_provider.id,
                    "model": "gpt-4",
                    "temperature": 0.7,
                    "max_tokens": 2000,
                    "stop_sequences": []
                }
            }
        }
        create_response = client.post("/api/v1/agents", json=agent_data, headers=auth_headers)
        agent_id = create_response.json()["id"]

        # Rollback to non-existent version
        rollback_data = {
            "version_id": 99999
        }
        response = client.post(f"/api/v1/agents/{agent_id}/rollback", json=rollback_data, headers=auth_headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_rollback_agent_not_found(self, client, auth_headers):
        """Test rolling back non-existent agent"""
        rollback_data = {
            "version_id": 1
        }
        response = client.post("/api/v1/agents/99999/rollback", json=rollback_data, headers=auth_headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_rollback_agent_unauthorized(self, client):
        """Test rolling back agent without authentication"""
        rollback_data = {
            "version_id": 1
        }
        response = client.post("/api/v1/agents/1/rollback", json=rollback_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
