"""
Tests for Prompt API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from app.models.prompt import Prompt, PromptVersion, MessageType, PromptUseCase


class TestPromptAPIEndpoints:
    """Test cases for Prompt CRUD API endpoints"""

    def test_create_prompt(self, client, auth_headers, db):
        """Test creating a prompt via API"""
        prompt_data = {
            "name": "API Test Prompt",
            "description": "A prompt created via API",
            "use_case": "coding",
            "tags": ["api", "test"],
            "version": {
                "template": "Write a {language} function to {task}",
                "message_type": "user",
                "is_active": True
            }
        }

        response = client.post(
            "/api/v1/prompts",
            json=prompt_data,
            headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "API Test Prompt"
        assert data["use_case"] == "coding"
        assert data["current_version"] is not None
        assert data["current_version"]["template"] == "Write a {language} function to {task}"
        assert data["current_version"]["variables"] == ["language", "task"]
        assert data["current_version"]["version_number"] == 1

    def test_create_prompt_minimal(self, client, auth_headers):
        """Test creating prompt with minimal data"""
        prompt_data = {
            "name": "Minimal Prompt",
            "version": {
                "template": "Simple template"
            }
        }

        response = client.post(
            "/api/v1/prompts",
            json=prompt_data,
            headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Minimal Prompt"
        assert data["use_case"] == "other"  # Default
        assert data["tags"] == []  # Default

    def test_list_prompts(self, client, auth_headers, test_user, db):
        """Test listing prompts"""
        # Create test prompts
        prompt1 = Prompt(
            user_id=test_user.id,
            name="Prompt 1",
            use_case=PromptUseCase.CODING
        )
        prompt2 = Prompt(
            user_id=test_user.id,
            name="Prompt 2",
            use_case=PromptUseCase.WRITING
        )
        db.add_all([prompt1, prompt2])
        db.commit()

        response = client.get("/api/v1/prompts", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "prompts" in data
        assert "total" in data
        assert data["total"] >= 2
        assert len(data["prompts"]) >= 2

    def test_list_prompts_filter_by_use_case(self, client, auth_headers, test_user, db):
        """Test filtering prompts by use case"""
        coding_prompt = Prompt(
            user_id=test_user.id,
            name="Coding Prompt",
            use_case=PromptUseCase.CODING
        )
        writing_prompt = Prompt(
            user_id=test_user.id,
            name="Writing Prompt",
            use_case=PromptUseCase.WRITING
        )
        db.add_all([coding_prompt, writing_prompt])
        db.commit()

        response = client.get(
            "/api/v1/prompts?use_case=coding",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        for prompt in data["prompts"]:
            assert prompt["use_case"] == "coding"

    def test_list_prompts_pagination(self, client, auth_headers, test_user, db):
        """Test prompt list pagination"""
        # Create multiple prompts
        for i in range(5):
            prompt = Prompt(
                user_id=test_user.id,
                name=f"Prompt {i}"
            )
            db.add(prompt)
        db.commit()

        response = client.get(
            "/api/v1/prompts?skip=0&limit=2",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["prompts"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2

    def test_get_prompt_by_id(self, client, auth_headers, test_user, db):
        """Test getting prompt by ID"""
        prompt = Prompt(
            user_id=test_user.id,
            name="Get Test Prompt",
            description="Test description"
        )
        db.add(prompt)
        db.commit()

        response = client.get(
            f"/api/v1/prompts/{prompt.id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == prompt.id
        assert data["name"] == "Get Test Prompt"
        assert data["description"] == "Test description"

    def test_get_prompt_not_found(self, client, auth_headers):
        """Test getting non-existent prompt returns 404"""
        response = client.get(
            "/api/v1/prompts/99999",
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_update_prompt_metadata(self, client, auth_headers, test_user, db):
        """Test updating prompt metadata"""
        prompt = Prompt(
            user_id=test_user.id,
            name="Original Name",
            description="Original description"
        )
        db.add(prompt)
        db.commit()

        update_data = {
            "name": "Updated Name",
            "description": "Updated description",
            "tags": ["updated"]
        }

        response = client.put(
            f"/api/v1/prompts/{prompt.id}",
            json=update_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated description"
        assert data["tags"] == ["updated"]

    def test_soft_delete_prompt(self, client, auth_headers, test_user, db):
        """Test soft deleting a prompt"""
        prompt = Prompt(
            user_id=test_user.id,
            name="Soft Delete Test"
        )
        db.add(prompt)
        db.commit()
        prompt_id = prompt.id

        response = client.delete(
            f"/api/v1/prompts/{prompt_id}",
            headers=auth_headers
        )

        assert response.status_code == 204

        # Verify soft delete
        deleted = db.query(Prompt).filter(Prompt.id == prompt_id).first()
        assert deleted is not None
        assert deleted.is_active is False

    def test_hard_delete_prompt(self, client, auth_headers, test_user, db):
        """Test hard deleting a prompt"""
        prompt = Prompt(
            user_id=test_user.id,
            name="Hard Delete Test"
        )
        db.add(prompt)
        db.commit()
        prompt_id = prompt.id

        response = client.delete(
            f"/api/v1/prompts/{prompt_id}?hard_delete=true",
            headers=auth_headers
        )

        assert response.status_code == 204

        # Verify hard delete
        deleted = db.query(Prompt).filter(Prompt.id == prompt_id).first()
        assert deleted is None

    def test_unauthorized_access(self, client):
        """Test that endpoints require authentication"""
        response = client.get("/api/v1/prompts")
        assert response.status_code == 401


class TestPromptVersionAPI:
    """Test cases for Prompt Version API endpoints"""

    def test_create_new_version(self, client, auth_headers, test_user, db):
        """Test creating a new version of a prompt"""
        # Create initial prompt
        response = client.post(
            "/api/v1/prompts",
            json={
                "name": "Version Test",
                "version": {"template": "Version 1"}
            },
            headers=auth_headers
        )
        prompt_id = response.json()["id"]

        # Create new version
        new_version = {
            "template": "Updated version with {variable}",
            "message_type": "system",
            "is_active": True
        }

        response = client.post(
            f"/api/v1/prompts/{prompt_id}/versions",
            json=new_version,
            headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["current_version"]["version_number"] == 2
        assert data["current_version"]["template"] == "Updated version with {variable}"
        assert data["current_version"]["variables"] == ["variable"]

    def test_list_prompt_versions(self, client, auth_headers, test_user, db):
        """Test listing all versions of a prompt"""
        prompt = Prompt(user_id=test_user.id, name="Multi-Version")
        db.add(prompt)
        db.flush()

        # Create multiple versions
        for i in range(1, 4):
            version = PromptVersion(
                prompt_id=prompt.id,
                version_number=i,
                template=f"Version {i}",
                variables=[],
                created_by=test_user.id
            )
            db.add(version)
        db.commit()

        response = client.get(
            f"/api/v1/prompts/{prompt.id}/versions",
            headers=auth_headers
        )

        assert response.status_code == 200
        versions = response.json()
        assert len(versions) == 3
        # Should be ordered by version_number desc
        assert versions[0]["version_number"] == 3
        assert versions[1]["version_number"] == 2
        assert versions[2]["version_number"] == 1

    def test_update_version_is_active(self, client, auth_headers, test_user, db):
        """Test updating version is_active flag for A/B testing"""
        prompt = Prompt(user_id=test_user.id, name="A/B Test")
        db.add(prompt)
        db.flush()

        version = PromptVersion(
            prompt_id=prompt.id,
            version_number=1,
            template="Test",
            variables=[],
            is_active=True,
            created_by=test_user.id
        )
        db.add(version)
        db.commit()

        # Deactivate version
        response = client.patch(
            f"/api/v1/prompts/{prompt.id}/versions/{version.id}",
            json={"is_active": False},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False

    def test_rollback_to_previous_version(self, client, auth_headers, test_user, db):
        """Test rolling back to a previous version"""
        # Create prompt with multiple versions
        response = client.post(
            "/api/v1/prompts",
            json={
                "name": "Rollback Test",
                "version": {"template": "Version 1"}
            },
            headers=auth_headers
        )
        prompt_id = response.json()["id"]
        version1_id = response.json()["current_version"]["id"]

        # Create version 2
        client.post(
            f"/api/v1/prompts/{prompt_id}/versions",
            json={"template": "Version 2"},
            headers=auth_headers
        )

        # Rollback to version 1
        response = client.post(
            f"/api/v1/prompts/{prompt_id}/rollback",
            json={"version_id": version1_id},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["current_version"]["id"] == version1_id
        assert data["current_version"]["template"] == "Version 1"

    def test_rollback_invalid_version(self, client, auth_headers, test_user, db):
        """Test rolling back to invalid version fails"""
        prompt = Prompt(user_id=test_user.id, name="Invalid Rollback")
        db.add(prompt)
        db.commit()

        response = client.post(
            f"/api/v1/prompts/{prompt.id}/rollback",
            json={"version_id": 99999},
            headers=auth_headers
        )

        assert response.status_code == 404


class TestPromptPreviewAPI:
    """Test cases for Prompt Preview API"""

    def test_preview_prompt_with_variables(self, client, auth_headers):
        """Test previewing a prompt template with variables"""
        preview_data = {
            "template": "Hello {name}, welcome to {platform}!",
            "variables": {
                "name": "John",
                "platform": "DeepAgentStudio"
            }
        }

        response = client.post(
            "/api/v1/prompts/preview",
            json=preview_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["rendered"] == "Hello John, welcome to DeepAgentStudio!"
        assert set(data["variables_found"]) == {"name", "platform"}
        assert data["variables_missing"] == []

    def test_preview_prompt_missing_variables(self, client, auth_headers):
        """Test preview with missing variables"""
        preview_data = {
            "template": "Hello {name}, you have {count} messages",
            "variables": {"name": "Alice"}
        }

        response = client.post(
            "/api/v1/prompts/preview",
            json=preview_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "count" in data["variables_missing"]
        assert "{count}" in data["rendered"]  # Unsubstituted

    def test_preview_prompt_no_variables(self, client, auth_headers):
        """Test preview with template without variables"""
        preview_data = {
            "template": "Static template with no variables",
            "variables": {}
        }

        response = client.post(
            "/api/v1/prompts/preview",
            json=preview_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["rendered"] == "Static template with no variables"
        assert data["variables_found"] == []
        assert data["variables_missing"] == []

    def test_preview_complex_variables(self, client, auth_headers):
        """Test preview with duplicate and complex variable names"""
        preview_data = {
            "template": "The {item} costs ${price}. Buy {item} now!",
            "variables": {"item": "book", "price": "19.99"}
        }

        response = client.post(
            "/api/v1/prompts/preview",
            json=preview_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["rendered"] == "The book costs $19.99. Buy book now!"
        # Should only list unique variables
        assert data["variables_found"] == ["item", "price"]


class TestPromptAccessControl:
    """Test cases for prompt access control"""

    def test_cannot_access_other_users_prompt(self, client, auth_headers, second_test_user, db):
        """Test that users cannot access other users' prompts"""
        # Create prompt for different user
        other_prompt = Prompt(
            user_id=second_test_user.id,
            name="Other User Prompt"
        )
        db.add(other_prompt)
        db.commit()

        response = client.get(
            f"/api/v1/prompts/{other_prompt.id}",
            headers=auth_headers
        )

        assert response.status_code == 404  # 404 for security

    def test_cannot_update_other_users_prompt(self, client, auth_headers, second_test_user, db):
        """Test that users cannot update other users' prompts"""
        other_prompt = Prompt(
            user_id=second_test_user.id,
            name="Other User Prompt"
        )
        db.add(other_prompt)
        db.commit()

        response = client.put(
            f"/api/v1/prompts/{other_prompt.id}",
            json={"name": "Hacked Name"},
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_cannot_delete_other_users_prompt(self, client, auth_headers, second_test_user, db):
        """Test that users cannot delete other users' prompts"""
        other_prompt = Prompt(
            user_id=second_test_user.id,
            name="Other User Prompt"
        )
        db.add(other_prompt)
        db.commit()

        response = client.delete(
            f"/api/v1/prompts/{other_prompt.id}",
            headers=auth_headers
        )

        assert response.status_code == 404


class TestPromptAnalyticsAPI:
    """Test cases for Prompt Analytics API endpoint"""

    def test_get_analytics_basic(self, client, auth_headers, test_user, db):
        """Test getting basic analytics for a prompt"""
        # Create prompt with version
        prompt = Prompt(
            user_id=test_user.id,
            name="Analytics Test Prompt"
        )
        db.add(prompt)
        db.flush()

        version = PromptVersion(
            prompt_id=prompt.id,
            version_number=1,
            template="Test template",
            variables=[],
            is_active=True,
            usage_count=10,
            created_by=test_user.id
        )
        db.add(version)
        db.flush()

        prompt.current_version_id = version.id
        db.commit()

        response = client.get(
            f"/api/v1/prompts/{prompt.id}/analytics",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["prompt_id"] == prompt.id
        assert data["prompt_name"] == "Analytics Test Prompt"
        assert data["total_usage_count"] == 10
        assert data["total_versions"] == 1
        assert len(data["version_usage"]) == 1
        assert data["version_usage"][0]["usage_count"] == 10
        assert data["version_usage"][0]["is_current"] is True

    def test_get_analytics_multiple_versions(self, client, auth_headers, test_user, db):
        """Test analytics with multiple versions"""
        prompt = Prompt(
            user_id=test_user.id,
            name="Multi-Version Analytics"
        )
        db.add(prompt)
        db.flush()

        # Create multiple versions with different usage counts
        version1 = PromptVersion(
            prompt_id=prompt.id,
            version_number=1,
            template="Version 1",
            variables=[],
            is_active=True,
            usage_count=5,
            created_by=test_user.id
        )
        version2 = PromptVersion(
            prompt_id=prompt.id,
            version_number=2,
            template="Version 2",
            variables=[],
            is_active=True,
            usage_count=15,
            created_by=test_user.id
        )
        version3 = PromptVersion(
            prompt_id=prompt.id,
            version_number=3,
            template="Version 3",
            variables=[],
            is_active=False,  # Inactive
            usage_count=3,
            created_by=test_user.id
        )
        db.add_all([version1, version2, version3])
        db.flush()

        prompt.current_version_id = version2.id
        db.commit()

        response = client.get(
            f"/api/v1/prompts/{prompt.id}/analytics",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_usage_count"] == 23  # 5 + 15 + 3
        assert data["total_versions"] == 3
        assert data["current_version_id"] == version2.id

        # Check version ordering (should be by version_number desc)
        version_usage = data["version_usage"]
        assert len(version_usage) == 3
        assert version_usage[0]["version_number"] == 3
        assert version_usage[1]["version_number"] == 2
        assert version_usage[2]["version_number"] == 1

        # Check is_current flag
        current_versions = [v for v in version_usage if v["is_current"]]
        assert len(current_versions) == 1
        assert current_versions[0]["version_id"] == version2.id

        # Check is_active flag
        inactive = [v for v in version_usage if not v["is_active"]]
        assert len(inactive) == 1
        assert inactive[0]["version_number"] == 3

    def test_get_analytics_no_versions(self, client, auth_headers, test_user, db):
        """Test analytics for prompt with no versions"""
        prompt = Prompt(
            user_id=test_user.id,
            name="No Versions Prompt"
        )
        db.add(prompt)
        db.commit()

        response = client.get(
            f"/api/v1/prompts/{prompt.id}/analytics",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_usage_count"] == 0
        assert data["total_versions"] == 0
        assert data["version_usage"] == []

    def test_get_analytics_not_found(self, client, auth_headers):
        """Test analytics for non-existent prompt returns 404"""
        response = client.get(
            "/api/v1/prompts/99999/analytics",
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_get_analytics_other_user_prompt(self, client, auth_headers, second_test_user, db):
        """Test that users cannot get analytics for other users' prompts"""
        other_prompt = Prompt(
            user_id=second_test_user.id,
            name="Other User Analytics Prompt"
        )
        db.add(other_prompt)
        db.commit()

        response = client.get(
            f"/api/v1/prompts/{other_prompt.id}/analytics",
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_get_analytics_zero_usage(self, client, auth_headers, test_user, db):
        """Test analytics with zero usage shows correct data"""
        prompt = Prompt(
            user_id=test_user.id,
            name="Zero Usage Prompt"
        )
        db.add(prompt)
        db.flush()

        version = PromptVersion(
            prompt_id=prompt.id,
            version_number=1,
            template="Unused template",
            variables=[],
            is_active=True,
            usage_count=0,
            created_by=test_user.id
        )
        db.add(version)
        db.flush()

        prompt.current_version_id = version.id
        db.commit()

        response = client.get(
            f"/api/v1/prompts/{prompt.id}/analytics",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_usage_count"] == 0
        assert data["version_usage"][0]["usage_count"] == 0
