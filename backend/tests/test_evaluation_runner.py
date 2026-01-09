"""Tests for the EvaluationRunner - evaluation run orchestration"""

import pytest
import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.services.evaluation_runner import EvaluationRunner
from app.services.dataset_service import DatasetService
from app.services.evaluator_service import EvaluatorService
from app.schemas.evaluation import (
    EvaluationRunCreate,
    EvaluationRunConfig,
    EvaluationDatasetCreate,
    DatasetExampleCreate,
    EvaluatorCreate,
    EvaluatorType,
    EvaluatorCategory,
)
from app.models.evaluation import (
    EvaluationRun,
    EvaluationResult,
    EvaluationScore,
    EvaluationStatus,
)
from app.models.agent import Agent, AgentVersion
from app.models.agent_type import AgentTypeConfig, ExecutionStrategy


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


@pytest.fixture
def test_dataset(db, test_user):
    """Create a test dataset with examples"""
    dataset_service = DatasetService(db)

    dataset = dataset_service.create_dataset(
        test_user.id,
        EvaluationDatasetCreate(name="Test Dataset", description="For testing")
    )

    # Add examples
    for i in range(3):
        dataset_service.create_example(
            dataset.id,
            test_user.id,
            DatasetExampleCreate(
                name=f"Example {i}",
                input=f"Question {i}",
                expected_output=f"Answer {i}"
            )
        )

    return dataset


@pytest.fixture
def test_evaluator(db, test_user):
    """Create a test evaluator"""
    evaluator_service = EvaluatorService(db)

    return evaluator_service.create_evaluator(
        test_user.id,
        EvaluatorCreate(
            name="Test Exact Match",
            type=EvaluatorType.EXACT_MATCH,
            category=EvaluatorCategory.OUTPUT,
            config={"case_sensitive": False}
        )
    )


class TestEvaluationRunCreation:
    """Tests for creating evaluation runs"""

    def test_create_run(self, db, test_user, test_dataset, test_agent, test_evaluator):
        """Test creating a new evaluation run"""
        runner = EvaluationRunner(db)

        data = EvaluationRunCreate(
            name="Test Run",
            dataset_id=test_dataset.id,
            agent_id=test_agent.id,
            evaluator_ids=[test_evaluator.id],
            config=EvaluationRunConfig(
                timeout_per_example_ms=30000,
                concurrency=2
            )
        )

        run = runner.create_run(test_user.id, data)

        assert run is not None
        assert run.id is not None
        assert run.name == "Test Run"
        assert run.status == EvaluationStatus.PENDING.value
        assert run.progress == 0
        assert run.total_examples == 3
        assert len(run.evaluators) == 1

    def test_create_run_invalid_dataset(self, db, test_user, test_agent, test_evaluator):
        """Test creating run with invalid dataset fails"""
        runner = EvaluationRunner(db)

        data = EvaluationRunCreate(
            name="Test Run",
            dataset_id=99999,  # Non-existent
            agent_id=test_agent.id,
            evaluator_ids=[test_evaluator.id]
        )

        with pytest.raises(ValueError, match="Dataset .* not found"):
            runner.create_run(test_user.id, data)

    def test_create_run_invalid_evaluator(self, db, test_user, test_dataset, test_agent):
        """Test creating run with invalid evaluator fails"""
        runner = EvaluationRunner(db)

        data = EvaluationRunCreate(
            name="Test Run",
            dataset_id=test_dataset.id,
            agent_id=test_agent.id,
            evaluator_ids=[99999]  # Non-existent
        )

        with pytest.raises(ValueError, match="One or more evaluators not found"):
            runner.create_run(test_user.id, data)

    def test_create_run_multiple_evaluators(self, db, test_user, test_dataset, test_agent):
        """Test creating run with multiple evaluators"""
        evaluator_service = EvaluatorService(db)

        eval1 = evaluator_service.create_evaluator(
            test_user.id,
            EvaluatorCreate(name="Eval 1", type=EvaluatorType.EXACT_MATCH, category=EvaluatorCategory.OUTPUT)
        )
        eval2 = evaluator_service.create_evaluator(
            test_user.id,
            EvaluatorCreate(name="Eval 2", type=EvaluatorType.CONTAINS, category=EvaluatorCategory.OUTPUT)
        )

        runner = EvaluationRunner(db)
        data = EvaluationRunCreate(
            name="Multi-Eval Run",
            dataset_id=test_dataset.id,
            agent_id=test_agent.id,
            evaluator_ids=[eval1.id, eval2.id]
        )

        run = runner.create_run(test_user.id, data)

        assert len(run.evaluators) == 2


class TestEvaluationRunRetrieval:
    """Tests for retrieving evaluation runs"""

    def test_get_run(self, db, test_user, test_dataset, test_agent, test_evaluator):
        """Test getting a run by ID"""
        runner = EvaluationRunner(db)

        created = runner.create_run(
            test_user.id,
            EvaluationRunCreate(
                name="Test Run",
                dataset_id=test_dataset.id,
                agent_id=test_agent.id,
                evaluator_ids=[test_evaluator.id]
            )
        )

        retrieved = runner.get_run(created.id, test_user.id)

        assert retrieved is not None
        assert retrieved.id == created.id

    def test_get_run_wrong_user(self, db, test_user, second_test_user, test_dataset, test_agent, test_evaluator):
        """Test that users can't get other users' runs"""
        runner = EvaluationRunner(db)

        created = runner.create_run(
            test_user.id,
            EvaluationRunCreate(
                name="Test Run",
                dataset_id=test_dataset.id,
                agent_id=test_agent.id,
                evaluator_ids=[test_evaluator.id]
            )
        )

        retrieved = runner.get_run(created.id, second_test_user.id)

        assert retrieved is None

    def test_get_run_with_details(self, db, test_user, test_dataset, test_agent, test_evaluator):
        """Test getting run with evaluators and results loaded"""
        runner = EvaluationRunner(db)

        created = runner.create_run(
            test_user.id,
            EvaluationRunCreate(
                name="Test Run",
                dataset_id=test_dataset.id,
                agent_id=test_agent.id,
                evaluator_ids=[test_evaluator.id]
            )
        )

        retrieved = runner.get_run_with_details(created.id, test_user.id)

        assert retrieved is not None
        # Check that relationships are loaded
        assert hasattr(retrieved, 'evaluators')
        assert hasattr(retrieved, 'dataset')

    def test_list_runs(self, db, test_user, test_dataset, test_agent, test_evaluator):
        """Test listing runs with pagination"""
        runner = EvaluationRunner(db)

        # Create multiple runs
        for i in range(5):
            runner.create_run(
                test_user.id,
                EvaluationRunCreate(
                    name=f"Run {i}",
                    dataset_id=test_dataset.id,
                    agent_id=test_agent.id,
                    evaluator_ids=[test_evaluator.id]
                )
            )

        runs, total = runner.list_runs(test_user.id, page=1, page_size=3)

        assert total == 5
        assert len(runs) == 3

    def test_list_runs_filter_by_status(self, db, test_user, test_dataset, test_agent, test_evaluator):
        """Test filtering runs by status"""
        runner = EvaluationRunner(db)

        run1 = runner.create_run(
            test_user.id,
            EvaluationRunCreate(
                name="Run 1",
                dataset_id=test_dataset.id,
                agent_id=test_agent.id,
                evaluator_ids=[test_evaluator.id]
            )
        )

        run2 = runner.create_run(
            test_user.id,
            EvaluationRunCreate(
                name="Run 2",
                dataset_id=test_dataset.id,
                agent_id=test_agent.id,
                evaluator_ids=[test_evaluator.id]
            )
        )

        # Update run2 status
        run2.status = EvaluationStatus.COMPLETED.value
        db.commit()

        runs, total = runner.list_runs(test_user.id, status=EvaluationStatus.COMPLETED.value)

        assert total == 1

    def test_list_runs_filter_by_dataset(self, db, test_user, test_dataset, test_agent, test_evaluator):
        """Test filtering runs by dataset"""
        runner = EvaluationRunner(db)
        dataset_service = DatasetService(db)

        # Create another dataset
        other_dataset = dataset_service.create_dataset(
            test_user.id,
            EvaluationDatasetCreate(name="Other Dataset")
        )
        dataset_service.create_example(
            other_dataset.id,
            test_user.id,
            DatasetExampleCreate(input="test", expected_output="test")
        )

        runner.create_run(
            test_user.id,
            EvaluationRunCreate(
                name="Run 1",
                dataset_id=test_dataset.id,
                agent_id=test_agent.id,
                evaluator_ids=[test_evaluator.id]
            )
        )

        runner.create_run(
            test_user.id,
            EvaluationRunCreate(
                name="Run 2",
                dataset_id=other_dataset.id,
                agent_id=test_agent.id,
                evaluator_ids=[test_evaluator.id]
            )
        )

        runs, total = runner.list_runs(test_user.id, dataset_id=test_dataset.id)

        assert total == 1


class TestEvaluationRunExecution:
    """Tests for executing evaluation runs"""

    @pytest.mark.asyncio
    async def test_execute_run(self, db, test_user, test_dataset, test_agent, test_evaluator):
        """Test executing an evaluation run"""
        runner = EvaluationRunner(db)

        run = runner.create_run(
            test_user.id,
            EvaluationRunCreate(
                name="Test Run",
                dataset_id=test_dataset.id,
                agent_id=test_agent.id,
                evaluator_ids=[test_evaluator.id],
                config=EvaluationRunConfig(concurrency=1)
            )
        )

        completed_run = await runner.execute_run(run.id, test_user.id)

        assert completed_run.status == EvaluationStatus.COMPLETED.value
        assert completed_run.progress == 100
        assert completed_run.completed_at is not None
        assert completed_run.metrics is not None

    @pytest.mark.asyncio
    async def test_execute_run_creates_results(self, db, test_user, test_dataset, test_agent, test_evaluator):
        """Test that execution creates result records"""
        runner = EvaluationRunner(db)

        run = runner.create_run(
            test_user.id,
            EvaluationRunCreate(
                name="Test Run",
                dataset_id=test_dataset.id,
                agent_id=test_agent.id,
                evaluator_ids=[test_evaluator.id]
            )
        )

        await runner.execute_run(run.id, test_user.id)

        # Check results were created
        results = db.query(EvaluationResult).filter(
            EvaluationResult.run_id == run.id
        ).all()

        assert len(results) == 3  # One per example

    @pytest.mark.asyncio
    async def test_execute_run_creates_scores(self, db, test_user, test_dataset, test_agent, test_evaluator):
        """Test that execution creates score records"""
        runner = EvaluationRunner(db)

        run = runner.create_run(
            test_user.id,
            EvaluationRunCreate(
                name="Test Run",
                dataset_id=test_dataset.id,
                agent_id=test_agent.id,
                evaluator_ids=[test_evaluator.id]
            )
        )

        await runner.execute_run(run.id, test_user.id)

        # Check scores were created
        scores = db.query(EvaluationScore).join(EvaluationResult).filter(
            EvaluationResult.run_id == run.id
        ).all()

        # 3 examples × 1 evaluator = 3 scores
        assert len(scores) == 3

    @pytest.mark.asyncio
    async def test_execute_run_not_found(self, db, test_user):
        """Test executing non-existent run fails"""
        runner = EvaluationRunner(db)

        with pytest.raises(ValueError, match="Run .* not found"):
            await runner.execute_run(99999, test_user.id)

    @pytest.mark.asyncio
    async def test_execute_run_already_running(self, db, test_user, test_dataset, test_agent, test_evaluator):
        """Test executing already running run fails"""
        runner = EvaluationRunner(db)

        run = runner.create_run(
            test_user.id,
            EvaluationRunCreate(
                name="Test Run",
                dataset_id=test_dataset.id,
                agent_id=test_agent.id,
                evaluator_ids=[test_evaluator.id]
            )
        )

        # Manually set to running
        run.status = EvaluationStatus.RUNNING.value
        db.commit()

        with pytest.raises(ValueError, match="Run is already"):
            await runner.execute_run(run.id, test_user.id)

    @pytest.mark.asyncio
    async def test_execute_run_with_callbacks(self, db, test_user, test_dataset, test_agent, test_evaluator):
        """Test that callbacks are called during execution"""
        progress_events = []
        result_events = []

        def progress_callback(event):
            progress_events.append(event)

        def result_callback(event):
            result_events.append(event)

        runner = EvaluationRunner(
            db,
            progress_callback=progress_callback,
            result_callback=result_callback
        )

        run = runner.create_run(
            test_user.id,
            EvaluationRunCreate(
                name="Test Run",
                dataset_id=test_dataset.id,
                agent_id=test_agent.id,
                evaluator_ids=[test_evaluator.id]
            )
        )

        await runner.execute_run(run.id, test_user.id)

        assert len(progress_events) > 0
        assert len(result_events) == 3  # One per example


class TestEvaluationRunResults:
    """Tests for retrieving evaluation results"""

    @pytest.mark.asyncio
    async def test_get_results(self, db, test_user, test_dataset, test_agent, test_evaluator):
        """Test getting results for a run"""
        runner = EvaluationRunner(db)

        run = runner.create_run(
            test_user.id,
            EvaluationRunCreate(
                name="Test Run",
                dataset_id=test_dataset.id,
                agent_id=test_agent.id,
                evaluator_ids=[test_evaluator.id]
            )
        )

        await runner.execute_run(run.id, test_user.id)

        results, total = runner.get_results(run.id, test_user.id)

        assert total == 3
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_get_results_pagination(self, db, test_user, test_agent, test_evaluator):
        """Test paginating results"""
        dataset_service = DatasetService(db)
        runner = EvaluationRunner(db)

        # Create dataset with more examples
        dataset = dataset_service.create_dataset(
            test_user.id,
            EvaluationDatasetCreate(name="Large Dataset")
        )
        for i in range(10):
            dataset_service.create_example(
                dataset.id,
                test_user.id,
                DatasetExampleCreate(input=f"Q{i}", expected_output=f"A{i}")
            )

        run = runner.create_run(
            test_user.id,
            EvaluationRunCreate(
                name="Test Run",
                dataset_id=dataset.id,
                agent_id=test_agent.id,
                evaluator_ids=[test_evaluator.id]
            )
        )

        await runner.execute_run(run.id, test_user.id)

        results, total = runner.get_results(run.id, test_user.id, page=1, page_size=5)

        assert total == 10
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_get_result_detail(self, db, test_user, test_dataset, test_agent, test_evaluator):
        """Test getting detailed result with scores"""
        runner = EvaluationRunner(db)

        run = runner.create_run(
            test_user.id,
            EvaluationRunCreate(
                name="Test Run",
                dataset_id=test_dataset.id,
                agent_id=test_agent.id,
                evaluator_ids=[test_evaluator.id]
            )
        )

        await runner.execute_run(run.id, test_user.id)

        results, _ = runner.get_results(run.id, test_user.id)
        result_id = results[0].id

        detail = runner.get_result_detail(run.id, result_id, test_user.id)

        assert detail is not None
        assert len(detail.scores) == 1


class TestEvaluationRunManagement:
    """Tests for managing evaluation runs"""

    def test_cancel_run(self, db, test_user, test_dataset, test_agent, test_evaluator):
        """Test cancelling a pending run"""
        runner = EvaluationRunner(db)

        run = runner.create_run(
            test_user.id,
            EvaluationRunCreate(
                name="Test Run",
                dataset_id=test_dataset.id,
                agent_id=test_agent.id,
                evaluator_ids=[test_evaluator.id]
            )
        )

        result = runner.cancel_run(run.id, test_user.id)

        assert result is True

        db.refresh(run)
        assert run.status == EvaluationStatus.CANCELLED.value

    def test_cancel_completed_run_fails(self, db, test_user, test_dataset, test_agent, test_evaluator):
        """Test that cancelling completed run fails"""
        runner = EvaluationRunner(db)

        run = runner.create_run(
            test_user.id,
            EvaluationRunCreate(
                name="Test Run",
                dataset_id=test_dataset.id,
                agent_id=test_agent.id,
                evaluator_ids=[test_evaluator.id]
            )
        )

        # Mark as completed
        run.status = EvaluationStatus.COMPLETED.value
        db.commit()

        result = runner.cancel_run(run.id, test_user.id)

        assert result is False

    def test_delete_run(self, db, test_user, test_dataset, test_agent, test_evaluator):
        """Test deleting a run"""
        runner = EvaluationRunner(db)

        run = runner.create_run(
            test_user.id,
            EvaluationRunCreate(
                name="Test Run",
                dataset_id=test_dataset.id,
                agent_id=test_agent.id,
                evaluator_ids=[test_evaluator.id]
            )
        )

        run_id = run.id
        result = runner.delete_run(run_id, test_user.id)

        assert result is True

        retrieved = runner.get_run(run_id, test_user.id)
        assert retrieved is None

    def test_delete_run_wrong_user(self, db, test_user, second_test_user, test_dataset, test_agent, test_evaluator):
        """Test that users can't delete other users' runs"""
        runner = EvaluationRunner(db)

        run = runner.create_run(
            test_user.id,
            EvaluationRunCreate(
                name="Test Run",
                dataset_id=test_dataset.id,
                agent_id=test_agent.id,
                evaluator_ids=[test_evaluator.id]
            )
        )

        result = runner.delete_run(run.id, second_test_user.id)

        assert result is False


class TestEvaluationMetrics:
    """Tests for metrics calculation"""

    @pytest.mark.asyncio
    async def test_metrics_calculated(self, db, test_user, test_dataset, test_agent, test_evaluator):
        """Test that metrics are calculated after run"""
        runner = EvaluationRunner(db)

        run = runner.create_run(
            test_user.id,
            EvaluationRunCreate(
                name="Test Run",
                dataset_id=test_dataset.id,
                agent_id=test_agent.id,
                evaluator_ids=[test_evaluator.id]
            )
        )

        completed = await runner.execute_run(run.id, test_user.id)

        metrics = completed.metrics

        assert metrics is not None
        assert "total_examples" in metrics
        assert "completed" in metrics
        assert "failed" in metrics
        assert "pass_rate" in metrics
        assert "avg_score" in metrics

    @pytest.mark.asyncio
    async def test_metrics_evaluator_scores(self, db, test_user, test_dataset, test_agent):
        """Test per-evaluator score aggregates"""
        evaluator_service = EvaluatorService(db)

        eval1 = evaluator_service.create_evaluator(
            test_user.id,
            EvaluatorCreate(name="Eval 1", type=EvaluatorType.EXACT_MATCH, category=EvaluatorCategory.OUTPUT)
        )
        eval2 = evaluator_service.create_evaluator(
            test_user.id,
            EvaluatorCreate(name="Eval 2", type=EvaluatorType.CONTAINS, category=EvaluatorCategory.OUTPUT)
        )

        runner = EvaluationRunner(db)

        run = runner.create_run(
            test_user.id,
            EvaluationRunCreate(
                name="Test Run",
                dataset_id=test_dataset.id,
                agent_id=test_agent.id,
                evaluator_ids=[eval1.id, eval2.id]
            )
        )

        completed = await runner.execute_run(run.id, test_user.id)

        evaluator_scores = completed.metrics.get("evaluator_scores", [])

        assert len(evaluator_scores) == 2


class TestEvaluationRunConfig:
    """Tests for run configuration options"""

    @pytest.mark.asyncio
    async def test_sample_size(self, db, test_user, test_agent, test_evaluator):
        """Test sampling dataset examples"""
        dataset_service = DatasetService(db)

        dataset = dataset_service.create_dataset(
            test_user.id,
            EvaluationDatasetCreate(name="Large Dataset")
        )
        for i in range(10):
            dataset_service.create_example(
                dataset.id,
                test_user.id,
                DatasetExampleCreate(input=f"Q{i}", expected_output=f"A{i}")
            )

        runner = EvaluationRunner(db)

        run = runner.create_run(
            test_user.id,
            EvaluationRunCreate(
                name="Sampled Run",
                dataset_id=dataset.id,
                agent_id=test_agent.id,
                evaluator_ids=[test_evaluator.id],
                config=EvaluationRunConfig(
                    sample_size=5,
                    sample_seed=42
                )
            )
        )

        completed = await runner.execute_run(run.id, test_user.id)

        # Should only process 5 examples
        assert completed.total_examples == 5
        assert completed.completed_examples == 5
