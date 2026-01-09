"""Tests for evaluation API endpoints"""

import pytest
import json
import base64
from app.services.dataset_service import DatasetService
from app.services.evaluator_service import EvaluatorService
from app.services.evaluation_runner import EvaluationRunner
from app.schemas.evaluation import (
    EvaluationDatasetCreate,
    DatasetExampleCreate,
    EvaluatorCreate,
    EvaluationRunCreate,
    EvaluatorType,
    EvaluatorCategory,
)
from app.models.agent import Agent, AgentVersion
from app.models.agent_type import AgentTypeConfig, ExecutionStrategy
from app.models.evaluation import Evaluator


@pytest.fixture
def test_agent_type(db, test_user):
    """Create a test agent type"""
    agent_type = AgentTypeConfig(
        user_id=test_user.id,
        name="Test ReAct Agent",
        execution_strategy=ExecutionStrategy.react,
        max_iterations=5,
        is_builtin=False
    )
    db.add(agent_type)
    db.commit()
    db.refresh(agent_type)
    return agent_type


@pytest.fixture
def test_agent(db, test_user, test_agent_type):
    """Create a test agent"""
    agent = Agent(
        user_id=test_user.id,
        name="Test Agent",
        description="A test agent for evaluations",
        agent_type_id=test_agent_type.id,
        is_active=True
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)

    # Create initial version
    version = AgentVersion(
        agent_id=agent.id,
        version_number=1,
        config={
            "llm_config": {"provider": "openai", "model": "gpt-4"},
            "system_prompt": "You are a helpful assistant."
        },
        created_by=test_user.id
    )
    db.add(version)
    db.commit()
    db.refresh(version)

    agent.current_version_id = version.id
    db.commit()
    db.refresh(agent)

    return agent


class TestDatasetEndpoints:
    """Tests for dataset API endpoints"""

    def test_create_dataset(self, client, auth_headers):
        """Test POST /api/v1/evaluations/datasets"""
        response = client.post(
            "/api/v1/evaluations/datasets",
            json={
                "name": "Test Dataset",
                "description": "A test dataset",
                "tags": ["test", "demo"]
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Dataset"
        assert data["description"] == "A test dataset"
        assert data["tags"] == ["test", "demo"]

    def test_create_dataset_unauthorized(self, client):
        """Test dataset creation requires auth"""
        response = client.post(
            "/api/v1/evaluations/datasets",
            json={"name": "Test Dataset"}
        )

        assert response.status_code == 401

    def test_list_datasets(self, client, auth_headers, db, test_user):
        """Test GET /api/v1/evaluations/datasets"""
        service = DatasetService(db)
        service.create_dataset(test_user.id, EvaluationDatasetCreate(name="Dataset 1"))
        service.create_dataset(test_user.id, EvaluationDatasetCreate(name="Dataset 2"))

        response = client.get(
            "/api/v1/evaluations/datasets",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["datasets"]) == 2

    def test_list_datasets_pagination(self, client, auth_headers, db, test_user):
        """Test dataset pagination"""
        service = DatasetService(db)
        for i in range(5):
            service.create_dataset(test_user.id, EvaluationDatasetCreate(name=f"Dataset {i}"))

        response = client.get(
            "/api/v1/evaluations/datasets?page=1&page_size=2",
            headers=auth_headers
        )

        data = response.json()
        assert data["total"] == 5
        assert len(data["datasets"]) == 2

    def test_list_datasets_search(self, client, auth_headers, db, test_user):
        """Test dataset search"""
        service = DatasetService(db)
        service.create_dataset(test_user.id, EvaluationDatasetCreate(name="Alpha Dataset"))
        service.create_dataset(test_user.id, EvaluationDatasetCreate(name="Beta Dataset"))

        response = client.get(
            "/api/v1/evaluations/datasets?search=Alpha",
            headers=auth_headers
        )

        data = response.json()
        assert data["total"] == 1

    def test_get_dataset(self, client, auth_headers, db, test_user):
        """Test GET /api/v1/evaluations/datasets/{dataset_id}"""
        service = DatasetService(db)
        dataset = service.create_dataset(test_user.id, EvaluationDatasetCreate(name="Test"))

        response = client.get(
            f"/api/v1/evaluations/datasets/{dataset.id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Test"

    def test_get_dataset_not_found(self, client, auth_headers):
        """Test getting non-existent dataset"""
        response = client.get(
            "/api/v1/evaluations/datasets/99999",
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_update_dataset(self, client, auth_headers, db, test_user):
        """Test PUT /api/v1/evaluations/datasets/{dataset_id}"""
        service = DatasetService(db)
        dataset = service.create_dataset(test_user.id, EvaluationDatasetCreate(name="Original"))

        response = client.put(
            f"/api/v1/evaluations/datasets/{dataset.id}",
            json={"name": "Updated", "description": "New description"},
            headers=auth_headers
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Updated"

    def test_delete_dataset(self, client, auth_headers, db, test_user):
        """Test DELETE /api/v1/evaluations/datasets/{dataset_id}"""
        service = DatasetService(db)
        dataset = service.create_dataset(test_user.id, EvaluationDatasetCreate(name="To Delete"))

        response = client.delete(
            f"/api/v1/evaluations/datasets/{dataset.id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        assert "deleted" in response.json()["message"].lower()


class TestDatasetExampleEndpoints:
    """Tests for dataset example API endpoints"""

    def test_create_example(self, client, auth_headers, db, test_user):
        """Test POST /api/v1/evaluations/datasets/{dataset_id}/examples"""
        service = DatasetService(db)
        dataset = service.create_dataset(test_user.id, EvaluationDatasetCreate(name="Test"))

        response = client.post(
            f"/api/v1/evaluations/datasets/{dataset.id}/examples",
            json={
                "name": "Test Example",
                "input": "What is 2+2?",
                "expected_output": "4"
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Test Example"

    def test_create_examples_batch(self, client, auth_headers, db, test_user):
        """Test POST /api/v1/evaluations/datasets/{dataset_id}/examples/batch"""
        service = DatasetService(db)
        dataset = service.create_dataset(test_user.id, EvaluationDatasetCreate(name="Test"))

        response = client.post(
            f"/api/v1/evaluations/datasets/{dataset.id}/examples/batch",
            json={
                "examples": [
                    {"input": "Q1", "expected_output": "A1"},
                    {"input": "Q2", "expected_output": "A2"},
                ]
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        assert response.json()["count"] == 2

    def test_list_examples(self, client, auth_headers, db, test_user):
        """Test GET /api/v1/evaluations/datasets/{dataset_id}/examples"""
        service = DatasetService(db)
        dataset = service.create_dataset(test_user.id, EvaluationDatasetCreate(name="Test"))
        service.create_example(dataset.id, test_user.id, DatasetExampleCreate(input="Q1", expected_output="A1"))

        response = client.get(
            f"/api/v1/evaluations/datasets/{dataset.id}/examples",
            headers=auth_headers
        )

        assert response.status_code == 200
        assert response.json()["total"] == 1

    def test_get_example(self, client, auth_headers, db, test_user):
        """Test GET /api/v1/evaluations/datasets/{dataset_id}/examples/{example_id}"""
        service = DatasetService(db)
        dataset = service.create_dataset(test_user.id, EvaluationDatasetCreate(name="Test"))
        example = service.create_example(dataset.id, test_user.id, DatasetExampleCreate(name="Ex1", input="Q", expected_output="A"))

        response = client.get(
            f"/api/v1/evaluations/datasets/{dataset.id}/examples/{example.id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Ex1"

    def test_update_example(self, client, auth_headers, db, test_user):
        """Test PUT /api/v1/evaluations/datasets/{dataset_id}/examples/{example_id}"""
        service = DatasetService(db)
        dataset = service.create_dataset(test_user.id, EvaluationDatasetCreate(name="Test"))
        example = service.create_example(dataset.id, test_user.id, DatasetExampleCreate(name="Original", input="Q", expected_output="A"))

        response = client.put(
            f"/api/v1/evaluations/datasets/{dataset.id}/examples/{example.id}",
            json={"name": "Updated"},
            headers=auth_headers
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Updated"

    def test_delete_example(self, client, auth_headers, db, test_user):
        """Test DELETE /api/v1/evaluations/datasets/{dataset_id}/examples/{example_id}"""
        service = DatasetService(db)
        dataset = service.create_dataset(test_user.id, EvaluationDatasetCreate(name="Test"))
        example = service.create_example(dataset.id, test_user.id, DatasetExampleCreate(input="Q", expected_output="A"))

        response = client.delete(
            f"/api/v1/evaluations/datasets/{dataset.id}/examples/{example.id}",
            headers=auth_headers
        )

        assert response.status_code == 200

    def test_delete_examples_batch(self, client, auth_headers, db, test_user):
        """Test DELETE /api/v1/evaluations/datasets/{dataset_id}/examples?example_ids=..."""
        service = DatasetService(db)
        dataset = service.create_dataset(test_user.id, EvaluationDatasetCreate(name="Test"))
        ex1 = service.create_example(dataset.id, test_user.id, DatasetExampleCreate(input="Q1", expected_output="A1"))
        ex2 = service.create_example(dataset.id, test_user.id, DatasetExampleCreate(input="Q2", expected_output="A2"))

        response = client.delete(
            f"/api/v1/evaluations/datasets/{dataset.id}/examples?example_ids={ex1.id},{ex2.id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        assert response.json()["deleted"] == 2


class TestDatasetImportExportEndpoints:
    """Tests for dataset import/export API endpoints"""

    def test_import_csv(self, client, auth_headers, db, test_user):
        """Test POST /api/v1/evaluations/datasets/{dataset_id}/import with CSV"""
        service = DatasetService(db)
        dataset = service.create_dataset(test_user.id, EvaluationDatasetCreate(name="Test"))

        csv_content = "input,expected_output\nQ1,A1\nQ2,A2"
        encoded = base64.b64encode(csv_content.encode()).decode()

        response = client.post(
            f"/api/v1/evaluations/datasets/{dataset.id}/import",
            json={"format": "csv", "data": encoded},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["imported_count"] == 2

    def test_import_json(self, client, auth_headers, db, test_user):
        """Test POST /api/v1/evaluations/datasets/{dataset_id}/import with JSON"""
        service = DatasetService(db)
        dataset = service.create_dataset(test_user.id, EvaluationDatasetCreate(name="Test"))

        json_content = json.dumps({
            "examples": [
                {"input": "Q1", "expected_output": "A1"},
                {"input": "Q2", "expected_output": "A2"}
            ]
        })
        encoded = base64.b64encode(json_content.encode()).decode()

        response = client.post(
            f"/api/v1/evaluations/datasets/{dataset.id}/import",
            json={"format": "json", "data": encoded},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["imported_count"] == 2

    def test_export_csv(self, client, auth_headers, db, test_user):
        """Test POST /api/v1/evaluations/datasets/{dataset_id}/export with CSV"""
        service = DatasetService(db)
        dataset = service.create_dataset(test_user.id, EvaluationDatasetCreate(name="Test"))
        service.create_example(dataset.id, test_user.id, DatasetExampleCreate(name="Ex1", input="Q1", expected_output="A1"))

        response = client.post(
            f"/api/v1/evaluations/datasets/{dataset.id}/export",
            json={"format": "csv"},
            headers=auth_headers
        )

        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        assert "Q1" in response.text

    def test_export_json(self, client, auth_headers, db, test_user):
        """Test POST /api/v1/evaluations/datasets/{dataset_id}/export with JSON"""
        service = DatasetService(db)
        dataset = service.create_dataset(test_user.id, EvaluationDatasetCreate(name="Test"))
        service.create_example(dataset.id, test_user.id, DatasetExampleCreate(name="Ex1", input="Q1", expected_output="A1"))

        response = client.post(
            f"/api/v1/evaluations/datasets/{dataset.id}/export",
            json={"format": "json"},
            headers=auth_headers
        )

        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]
        data = response.json()
        assert data["dataset"]["name"] == "Test"


class TestEvaluatorEndpoints:
    """Tests for evaluator API endpoints"""

    def test_list_evaluators(self, client, auth_headers, db):
        """Test GET /api/v1/evaluations/evaluators"""
        # Seed built-in evaluators
        service = EvaluatorService(db)
        service.seed_builtin_evaluators()

        response = client.get(
            "/api/v1/evaluations/evaluators",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] > 0

    def test_list_evaluators_filter_category(self, client, auth_headers, db):
        """Test filtering evaluators by category"""
        service = EvaluatorService(db)
        service.seed_builtin_evaluators()

        response = client.get(
            "/api/v1/evaluations/evaluators?category=output",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        for evaluator in data["evaluators"]:
            assert evaluator["category"] == "output"

    def test_create_evaluator(self, client, auth_headers):
        """Test POST /api/v1/evaluations/evaluators"""
        response = client.post(
            "/api/v1/evaluations/evaluators",
            json={
                "name": "My Custom Evaluator",
                "type": "exact_match",
                "category": "output",
                "config": {"case_sensitive": False}
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "My Custom Evaluator"
        assert data["is_builtin"] is False

    def test_get_evaluator(self, client, auth_headers, db, test_user):
        """Test GET /api/v1/evaluations/evaluators/{evaluator_id}"""
        service = EvaluatorService(db)
        evaluator = service.create_evaluator(
            test_user.id,
            EvaluatorCreate(name="Test", type=EvaluatorType.CONTAINS, category=EvaluatorCategory.OUTPUT)
        )

        response = client.get(
            f"/api/v1/evaluations/evaluators/{evaluator.id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Test"

    def test_get_builtin_evaluator(self, client, auth_headers, db):
        """Test getting a built-in evaluator"""
        service = EvaluatorService(db)
        service.seed_builtin_evaluators()

        builtin = db.query(Evaluator).filter(Evaluator.is_builtin == True).first()

        response = client.get(
            f"/api/v1/evaluations/evaluators/{builtin.id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        assert response.json()["is_builtin"] is True

    def test_update_evaluator(self, client, auth_headers, db, test_user):
        """Test PUT /api/v1/evaluations/evaluators/{evaluator_id}"""
        service = EvaluatorService(db)
        evaluator = service.create_evaluator(
            test_user.id,
            EvaluatorCreate(name="Original", type=EvaluatorType.CONTAINS, category=EvaluatorCategory.OUTPUT)
        )

        response = client.put(
            f"/api/v1/evaluations/evaluators/{evaluator.id}",
            json={"name": "Updated"},
            headers=auth_headers
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Updated"

    def test_update_builtin_evaluator_fails(self, client, auth_headers, db):
        """Test that updating built-in evaluator fails"""
        service = EvaluatorService(db)
        service.seed_builtin_evaluators()

        builtin = db.query(Evaluator).filter(Evaluator.is_builtin == True).first()

        response = client.put(
            f"/api/v1/evaluations/evaluators/{builtin.id}",
            json={"name": "Hacked"},
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_delete_evaluator(self, client, auth_headers, db, test_user):
        """Test DELETE /api/v1/evaluations/evaluators/{evaluator_id}"""
        service = EvaluatorService(db)
        evaluator = service.create_evaluator(
            test_user.id,
            EvaluatorCreate(name="To Delete", type=EvaluatorType.CONTAINS, category=EvaluatorCategory.OUTPUT)
        )

        response = client.delete(
            f"/api/v1/evaluations/evaluators/{evaluator.id}",
            headers=auth_headers
        )

        assert response.status_code == 200

    def test_delete_builtin_evaluator_fails(self, client, auth_headers, db):
        """Test that deleting built-in evaluator fails"""
        service = EvaluatorService(db)
        service.seed_builtin_evaluators()

        builtin = db.query(Evaluator).filter(Evaluator.is_builtin == True).first()

        response = client.delete(
            f"/api/v1/evaluations/evaluators/{builtin.id}",
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_clone_evaluator(self, client, auth_headers, db):
        """Test POST /api/v1/evaluations/evaluators/{evaluator_id}/clone"""
        service = EvaluatorService(db)
        service.seed_builtin_evaluators()

        builtin = db.query(Evaluator).filter(Evaluator.is_builtin == True).first()

        response = client.post(
            f"/api/v1/evaluations/evaluators/{builtin.id}/clone",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_builtin"] is False
        assert "(Copy)" in data["name"]

    def test_clone_evaluator_with_name(self, client, auth_headers, db):
        """Test cloning evaluator with custom name"""
        service = EvaluatorService(db)
        service.seed_builtin_evaluators()

        builtin = db.query(Evaluator).filter(Evaluator.is_builtin == True).first()

        response = client.post(
            f"/api/v1/evaluations/evaluators/{builtin.id}/clone?new_name=My%20Clone",
            headers=auth_headers
        )

        assert response.status_code == 200
        assert response.json()["name"] == "My Clone"

    def test_test_evaluator(self, client, auth_headers, db, test_user):
        """Test POST /api/v1/evaluations/evaluators/{evaluator_id}/test"""
        service = EvaluatorService(db)
        evaluator = service.create_evaluator(
            test_user.id,
            EvaluatorCreate(
                name="Test Exact Match",
                type=EvaluatorType.EXACT_MATCH,
                category=EvaluatorCategory.OUTPUT,
                config={"case_sensitive": False}
            )
        )

        response = client.post(
            f"/api/v1/evaluations/evaluators/{evaluator.id}/test",
            json={
                "input": "What is 2+2?",
                "expected_output": "4",
                "actual_output": "4"
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["passed"] is True
        assert data["score"] == 1.0

    def test_seed_builtin_evaluators(self, client, auth_headers, db):
        """Test POST /api/v1/evaluations/evaluators/seed"""
        response = client.post(
            "/api/v1/evaluations/evaluators/seed",
            headers=auth_headers
        )

        assert response.status_code == 200
        assert "Seeded" in response.json()["message"]


class TestEvaluationRunEndpoints:
    """Tests for evaluation run API endpoints"""

    def test_create_run(self, client, auth_headers, db, test_user, test_agent):
        """Test POST /api/v1/evaluations/runs"""
        dataset_service = DatasetService(db)
        evaluator_service = EvaluatorService(db)

        dataset = dataset_service.create_dataset(test_user.id, EvaluationDatasetCreate(name="Test Dataset"))
        dataset_service.create_example(dataset.id, test_user.id, DatasetExampleCreate(input="Q", expected_output="A"))

        evaluator = evaluator_service.create_evaluator(
            test_user.id,
            EvaluatorCreate(name="Test Eval", type=EvaluatorType.EXACT_MATCH, category=EvaluatorCategory.OUTPUT)
        )

        response = client.post(
            "/api/v1/evaluations/runs",
            json={
                "name": "Test Run",
                "dataset_id": dataset.id,
                "agent_id": test_agent.id,
                "evaluator_ids": [evaluator.id]
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Run"
        assert data["status"] == "pending"

    def test_create_run_invalid_dataset(self, client, auth_headers, db, test_user, test_agent):
        """Test creating run with invalid dataset"""
        evaluator_service = EvaluatorService(db)
        evaluator = evaluator_service.create_evaluator(
            test_user.id,
            EvaluatorCreate(name="Test", type=EvaluatorType.EXACT_MATCH, category=EvaluatorCategory.OUTPUT)
        )

        response = client.post(
            "/api/v1/evaluations/runs",
            json={
                "name": "Test Run",
                "dataset_id": 99999,
                "agent_id": test_agent.id,
                "evaluator_ids": [evaluator.id]
            },
            headers=auth_headers
        )

        assert response.status_code == 400

    def test_list_runs(self, client, auth_headers, db, test_user, test_agent):
        """Test GET /api/v1/evaluations/runs"""
        dataset_service = DatasetService(db)
        evaluator_service = EvaluatorService(db)

        dataset = dataset_service.create_dataset(test_user.id, EvaluationDatasetCreate(name="Test"))
        dataset_service.create_example(dataset.id, test_user.id, DatasetExampleCreate(input="Q", expected_output="A"))

        evaluator = evaluator_service.create_evaluator(
            test_user.id,
            EvaluatorCreate(name="Eval", type=EvaluatorType.EXACT_MATCH, category=EvaluatorCategory.OUTPUT)
        )

        runner = EvaluationRunner(db)
        runner.create_run(test_user.id, EvaluationRunCreate(
            name="Run 1",
            dataset_id=dataset.id,
            agent_id=test_agent.id,
            evaluator_ids=[evaluator.id]
        ))

        response = client.get(
            "/api/v1/evaluations/runs",
            headers=auth_headers
        )

        assert response.status_code == 200
        assert response.json()["total"] >= 1

    def test_get_run(self, client, auth_headers, db, test_user, test_agent):
        """Test GET /api/v1/evaluations/runs/{run_id}"""
        dataset_service = DatasetService(db)
        evaluator_service = EvaluatorService(db)

        dataset = dataset_service.create_dataset(test_user.id, EvaluationDatasetCreate(name="Test"))
        dataset_service.create_example(dataset.id, test_user.id, DatasetExampleCreate(input="Q", expected_output="A"))

        evaluator = evaluator_service.create_evaluator(
            test_user.id,
            EvaluatorCreate(name="Eval", type=EvaluatorType.EXACT_MATCH, category=EvaluatorCategory.OUTPUT)
        )

        runner = EvaluationRunner(db)
        run = runner.create_run(test_user.id, EvaluationRunCreate(
            name="Test Run",
            dataset_id=dataset.id,
            agent_id=test_agent.id,
            evaluator_ids=[evaluator.id]
        ))

        response = client.get(
            f"/api/v1/evaluations/runs/{run.id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Test Run"

    def test_get_run_not_found(self, client, auth_headers):
        """Test getting non-existent run"""
        response = client.get(
            "/api/v1/evaluations/runs/99999",
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_execute_run(self, client, auth_headers, db, test_user, test_agent):
        """Test POST /api/v1/evaluations/runs/{run_id}/execute"""
        dataset_service = DatasetService(db)
        evaluator_service = EvaluatorService(db)

        dataset = dataset_service.create_dataset(test_user.id, EvaluationDatasetCreate(name="Test"))
        dataset_service.create_example(dataset.id, test_user.id, DatasetExampleCreate(input="Q", expected_output="A"))

        evaluator = evaluator_service.create_evaluator(
            test_user.id,
            EvaluatorCreate(name="Eval", type=EvaluatorType.EXACT_MATCH, category=EvaluatorCategory.OUTPUT)
        )

        runner = EvaluationRunner(db)
        run = runner.create_run(test_user.id, EvaluationRunCreate(
            name="Test Run",
            dataset_id=dataset.id,
            agent_id=test_agent.id,
            evaluator_ids=[evaluator.id]
        ))

        response = client.post(
            f"/api/v1/evaluations/runs/{run.id}/execute",
            headers=auth_headers
        )

        assert response.status_code == 200
        assert "Evaluation started" in response.json()["message"]

    def test_cancel_run(self, client, auth_headers, db, test_user, test_agent):
        """Test POST /api/v1/evaluations/runs/{run_id}/cancel"""
        dataset_service = DatasetService(db)
        evaluator_service = EvaluatorService(db)

        dataset = dataset_service.create_dataset(test_user.id, EvaluationDatasetCreate(name="Test"))
        dataset_service.create_example(dataset.id, test_user.id, DatasetExampleCreate(input="Q", expected_output="A"))

        evaluator = evaluator_service.create_evaluator(
            test_user.id,
            EvaluatorCreate(name="Eval", type=EvaluatorType.EXACT_MATCH, category=EvaluatorCategory.OUTPUT)
        )

        runner = EvaluationRunner(db)
        run = runner.create_run(test_user.id, EvaluationRunCreate(
            name="Test Run",
            dataset_id=dataset.id,
            agent_id=test_agent.id,
            evaluator_ids=[evaluator.id]
        ))

        response = client.post(
            f"/api/v1/evaluations/runs/{run.id}/cancel",
            headers=auth_headers
        )

        assert response.status_code == 200

    def test_delete_run(self, client, auth_headers, db, test_user, test_agent):
        """Test DELETE /api/v1/evaluations/runs/{run_id}"""
        dataset_service = DatasetService(db)
        evaluator_service = EvaluatorService(db)

        dataset = dataset_service.create_dataset(test_user.id, EvaluationDatasetCreate(name="Test"))
        dataset_service.create_example(dataset.id, test_user.id, DatasetExampleCreate(input="Q", expected_output="A"))

        evaluator = evaluator_service.create_evaluator(
            test_user.id,
            EvaluatorCreate(name="Eval", type=EvaluatorType.EXACT_MATCH, category=EvaluatorCategory.OUTPUT)
        )

        runner = EvaluationRunner(db)
        run = runner.create_run(test_user.id, EvaluationRunCreate(
            name="Test Run",
            dataset_id=dataset.id,
            agent_id=test_agent.id,
            evaluator_ids=[evaluator.id]
        ))

        response = client.delete(
            f"/api/v1/evaluations/runs/{run.id}",
            headers=auth_headers
        )

        assert response.status_code == 200


class TestEvaluationResultEndpoints:
    """Tests for evaluation result API endpoints"""

    @pytest.mark.asyncio
    async def test_list_results(self, client, auth_headers, db, test_user, test_agent):
        """Test GET /api/v1/evaluations/runs/{run_id}/results"""
        dataset_service = DatasetService(db)
        evaluator_service = EvaluatorService(db)

        dataset = dataset_service.create_dataset(test_user.id, EvaluationDatasetCreate(name="Test"))
        dataset_service.create_example(dataset.id, test_user.id, DatasetExampleCreate(input="Q", expected_output="A"))

        evaluator = evaluator_service.create_evaluator(
            test_user.id,
            EvaluatorCreate(name="Eval", type=EvaluatorType.EXACT_MATCH, category=EvaluatorCategory.OUTPUT)
        )

        runner = EvaluationRunner(db)
        run = runner.create_run(test_user.id, EvaluationRunCreate(
            name="Test Run",
            dataset_id=dataset.id,
            agent_id=test_agent.id,
            evaluator_ids=[evaluator.id]
        ))

        # Execute the run
        await runner.execute_run(run.id, test_user.id)

        response = client.get(
            f"/api/v1/evaluations/runs/{run.id}/results",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1


class TestComparisonEndpoints:
    """Tests for run comparison API endpoints"""

    def test_compare_runs(self, client, auth_headers, db, test_user, test_agent):
        """Test GET /api/v1/evaluations/runs/compare"""
        dataset_service = DatasetService(db)
        evaluator_service = EvaluatorService(db)

        dataset = dataset_service.create_dataset(test_user.id, EvaluationDatasetCreate(name="Test"))
        dataset_service.create_example(dataset.id, test_user.id, DatasetExampleCreate(input="Q", expected_output="A"))

        evaluator = evaluator_service.create_evaluator(
            test_user.id,
            EvaluatorCreate(name="Eval", type=EvaluatorType.EXACT_MATCH, category=EvaluatorCategory.OUTPUT)
        )

        runner = EvaluationRunner(db)
        run1 = runner.create_run(test_user.id, EvaluationRunCreate(
            name="Run 1",
            dataset_id=dataset.id,
            agent_id=test_agent.id,
            evaluator_ids=[evaluator.id]
        ))
        run2 = runner.create_run(test_user.id, EvaluationRunCreate(
            name="Run 2",
            dataset_id=dataset.id,
            agent_id=test_agent.id,
            evaluator_ids=[evaluator.id]
        ))

        response = client.get(
            f"/api/v1/evaluations/runs/compare?run_ids={run1.id},{run2.id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["runs"]) == 2
