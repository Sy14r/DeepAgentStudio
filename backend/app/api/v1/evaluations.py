"""Evaluation API endpoints for datasets, evaluators, and runs"""

import base64
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Response
from sqlalchemy.orm import Session

from ...database import get_db
from ..deps import get_current_user
from ...models.user import User
from ...schemas.evaluation import (
    # Dataset schemas
    EvaluationDatasetCreate,
    EvaluationDatasetUpdate,
    EvaluationDatasetResponse,
    EvaluationDatasetDetailResponse,
    EvaluationDatasetListResponse,
    DatasetExampleCreate,
    DatasetExampleUpdate,
    DatasetExampleResponse,
    DatasetExampleBatchCreate,
    DatasetImportRequest,
    DatasetImportResponse,
    DatasetExportRequest,
    # Evaluator schemas
    EvaluatorCreate,
    EvaluatorUpdate,
    EvaluatorResponse,
    EvaluatorListResponse,
    EvaluatorTestRequest,
    EvaluatorTestResponse,
    # Evaluation config schemas
    EvaluationCreate,
    EvaluationUpdate,
    EvaluationResponse,
    EvaluationDetailResponse,
    EvaluationListResponse,
    # Run schemas
    EvaluationRunCreate,
    EvaluationRunResponse,
    EvaluationRunDetailResponse,
    EvaluationRunListResponse,
    # Result schemas
    EvaluationResultResponse,
    EvaluationResultDetailResponse,
    EvaluationResultListResponse,
    # Enums
    EvaluatorCategory,
)
from ...services.dataset_service import DatasetService
from ...services.evaluator_service import EvaluatorService
from ...services.evaluation_service import EvaluationService
from ...services.evaluation_runner import EvaluationRunner
from ...services.evaluator_engine import run_evaluator, EvaluatorInput

router = APIRouter()


# ===== Dataset Endpoints =====

@router.post("/datasets", response_model=EvaluationDatasetResponse)
async def create_dataset(
    data: EvaluationDatasetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new evaluation dataset"""
    service = DatasetService(db)
    dataset = service.create_dataset(current_user.id, data)
    return dataset


@router.get("/datasets", response_model=EvaluationDatasetListResponse)
async def list_datasets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    tags: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all datasets for the current user"""
    service = DatasetService(db)
    tag_list = tags.split(",") if tags else None
    datasets, total = service.list_datasets(
        current_user.id,
        page=page,
        page_size=page_size,
        search=search,
        tags=tag_list
    )
    return EvaluationDatasetListResponse(
        datasets=datasets,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/datasets/{dataset_id}", response_model=EvaluationDatasetDetailResponse)
async def get_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a dataset with all examples"""
    service = DatasetService(db)
    dataset = service.get_dataset_with_examples(dataset_id, current_user.id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.put("/datasets/{dataset_id}", response_model=EvaluationDatasetResponse)
async def update_dataset(
    dataset_id: int,
    data: EvaluationDatasetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a dataset"""
    service = DatasetService(db)
    dataset = service.update_dataset(dataset_id, current_user.id, data)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.delete("/datasets/{dataset_id}")
async def delete_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a dataset and all its examples"""
    service = DatasetService(db)
    success = service.delete_dataset(dataset_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return {"message": "Dataset deleted"}


# ===== Dataset Example Endpoints =====

@router.post("/datasets/{dataset_id}/examples", response_model=DatasetExampleResponse)
async def create_example(
    dataset_id: int,
    data: DatasetExampleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new example in a dataset"""
    service = DatasetService(db)
    example = service.create_example(dataset_id, current_user.id, data)
    if not example:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return example


@router.post("/datasets/{dataset_id}/examples/batch")
async def create_examples_batch(
    dataset_id: int,
    data: DatasetExampleBatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create multiple examples at once"""
    service = DatasetService(db)
    examples, count = service.create_examples_batch(dataset_id, current_user.id, data)
    if not examples:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return {"examples": examples, "count": count}


@router.get("/datasets/{dataset_id}/examples")
async def list_examples(
    dataset_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    tags: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List examples in a dataset with pagination"""
    service = DatasetService(db)
    tag_list = tags.split(",") if tags else None
    examples, total = service.list_examples(
        dataset_id,
        current_user.id,
        page=page,
        page_size=page_size,
        search=search,
        tags=tag_list
    )
    return {"examples": examples, "total": total, "page": page, "page_size": page_size}


@router.get("/datasets/{dataset_id}/examples/{example_id}", response_model=DatasetExampleResponse)
async def get_example(
    dataset_id: int,
    example_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific example"""
    service = DatasetService(db)
    example = service.get_example(dataset_id, example_id, current_user.id)
    if not example:
        raise HTTPException(status_code=404, detail="Example not found")
    return example


@router.put("/datasets/{dataset_id}/examples/{example_id}", response_model=DatasetExampleResponse)
async def update_example(
    dataset_id: int,
    example_id: int,
    data: DatasetExampleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an example"""
    service = DatasetService(db)
    example = service.update_example(dataset_id, example_id, current_user.id, data)
    if not example:
        raise HTTPException(status_code=404, detail="Example not found")
    return example


@router.delete("/datasets/{dataset_id}/examples/{example_id}")
async def delete_example(
    dataset_id: int,
    example_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an example"""
    service = DatasetService(db)
    success = service.delete_example(dataset_id, example_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Example not found")
    return {"message": "Example deleted"}


@router.delete("/datasets/{dataset_id}/examples")
async def delete_examples_batch(
    dataset_id: int,
    example_ids: str = Query(..., description="Comma-separated example IDs"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete multiple examples at once"""
    service = DatasetService(db)
    ids = [int(id.strip()) for id in example_ids.split(",")]
    deleted = service.delete_examples_batch(dataset_id, ids, current_user.id)
    return {"deleted": deleted}


# ===== Dataset Import/Export Endpoints =====

@router.post("/datasets/{dataset_id}/import", response_model=DatasetImportResponse)
async def import_examples(
    dataset_id: int,
    data: DatasetImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Import examples from CSV or JSON"""
    service = DatasetService(db)

    # Decode content if base64 encoded
    try:
        content = base64.b64decode(data.data).decode("utf-8")
    except Exception:
        content = data.data  # Assume it's already plain text

    if data.format == "csv":
        imported, skipped, errors = service.import_from_csv(dataset_id, current_user.id, content)
    else:
        imported, skipped, errors = service.import_from_json(dataset_id, current_user.id, content)

    return DatasetImportResponse(
        imported_count=imported,
        skipped_count=skipped,
        errors=errors
    )


@router.post("/datasets/{dataset_id}/export")
async def export_examples(
    dataset_id: int,
    data: DatasetExportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export examples to CSV or JSON"""
    service = DatasetService(db)

    if data.format == "csv":
        content = service.export_to_csv(dataset_id, current_user.id)
        if not content:
            raise HTTPException(status_code=404, detail="Dataset not found")
        return Response(
            content=content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=dataset_{dataset_id}.csv"}
        )
    else:
        content = service.export_to_json(dataset_id, current_user.id)
        if not content:
            raise HTTPException(status_code=404, detail="Dataset not found")
        return Response(
            content=content,
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=dataset_{dataset_id}.json"}
        )


# ===== Evaluator Endpoints =====

@router.get("/evaluators", response_model=EvaluatorListResponse)
async def list_evaluators(
    category: Optional[str] = None,
    type_filter: Optional[str] = Query(None, alias="type"),
    include_builtin: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all evaluators (built-in and custom)"""
    service = EvaluatorService(db)
    evaluators, total = service.list_evaluators(
        current_user.id,
        category=category,
        type_filter=type_filter,
        include_builtin=include_builtin
    )
    return EvaluatorListResponse(evaluators=evaluators, total=total)


@router.post("/evaluators", response_model=EvaluatorResponse)
async def create_evaluator(
    data: EvaluatorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a custom evaluator"""
    service = EvaluatorService(db)
    evaluator = service.create_evaluator(current_user.id, data)
    return evaluator


@router.get("/evaluators/{evaluator_id}", response_model=EvaluatorResponse)
async def get_evaluator(
    evaluator_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get an evaluator by ID"""
    service = EvaluatorService(db)
    evaluator = service.get_evaluator(evaluator_id, current_user.id)
    if not evaluator:
        raise HTTPException(status_code=404, detail="Evaluator not found")
    return evaluator


@router.put("/evaluators/{evaluator_id}", response_model=EvaluatorResponse)
async def update_evaluator(
    evaluator_id: int,
    data: EvaluatorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a custom evaluator (cannot update built-in)"""
    service = EvaluatorService(db)
    evaluator = service.update_evaluator(evaluator_id, current_user.id, data)
    if not evaluator:
        raise HTTPException(status_code=404, detail="Evaluator not found or cannot update built-in")
    return evaluator


@router.delete("/evaluators/{evaluator_id}")
async def delete_evaluator(
    evaluator_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a custom evaluator (cannot delete built-in)"""
    service = EvaluatorService(db)
    success = service.delete_evaluator(evaluator_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Evaluator not found or cannot delete built-in")
    return {"message": "Evaluator deleted"}


@router.post("/evaluators/{evaluator_id}/clone", response_model=EvaluatorResponse)
async def clone_evaluator(
    evaluator_id: int,
    new_name: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Clone an evaluator (built-in or custom) as a custom evaluator"""
    service = EvaluatorService(db)
    evaluator = service.clone_evaluator(evaluator_id, current_user.id, new_name)
    if not evaluator:
        raise HTTPException(status_code=404, detail="Evaluator not found")
    return evaluator


@router.post("/evaluators/{evaluator_id}/test", response_model=EvaluatorTestResponse)
async def test_evaluator(
    evaluator_id: int,
    data: EvaluatorTestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Test an evaluator with sample data"""
    service = EvaluatorService(db)
    evaluator = service.get_evaluator(evaluator_id, current_user.id)
    if not evaluator:
        raise HTTPException(status_code=404, detail="Evaluator not found")

    try:
        result = run_evaluator(
            evaluator_type=evaluator.type,
            config=evaluator.config or {},
            input_data=data.input,
            expected_output=data.expected_output,
            actual_output=data.actual_output,
            run_metadata=data.run_metadata
        )

        return EvaluatorTestResponse(
            score=float(result.score) if result.score is not None else 0,
            passed=result.passed if result.passed is not None else False,
            feedback=result.feedback,
            metadata=result.metadata,
            error=result.error
        )
    except Exception as e:
        return EvaluatorTestResponse(
            score=0,
            passed=False,
            feedback="Evaluation failed",
            error=str(e)
        )


@router.post("/evaluators/seed")
async def seed_builtin_evaluators(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Seed built-in evaluators (admin only)"""
    # TODO: Add admin check
    service = EvaluatorService(db)
    created = service.seed_builtin_evaluators()
    return {"message": f"Seeded {created} built-in evaluators"}


# ===== Evaluation Config Endpoints =====

@router.post("", response_model=EvaluationResponse)
async def create_evaluation(
    data: EvaluationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new reusable evaluation configuration"""
    service = EvaluationService(db)
    try:
        evaluation = service.create_evaluation(current_user.id, data)
        return _build_evaluation_response(evaluation)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=EvaluationListResponse)
async def list_evaluations(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    dataset_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all evaluations for the current user"""
    service = EvaluationService(db)
    evaluations, total = service.list_evaluations(
        current_user.id,
        page=page,
        page_size=page_size,
        search=search,
        dataset_id=dataset_id,
        is_active=is_active,
    )
    return EvaluationListResponse(
        evaluations=[_build_evaluation_response(e) for e in evaluations],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{evaluation_id}", response_model=EvaluationDetailResponse)
async def get_evaluation(
    evaluation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get an evaluation configuration with details"""
    service = EvaluationService(db)
    evaluation = service.get_evaluation_with_details(evaluation_id, current_user.id)
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return _build_evaluation_detail_response(evaluation)


@router.put("/{evaluation_id}", response_model=EvaluationResponse)
async def update_evaluation(
    evaluation_id: int,
    data: EvaluationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an evaluation configuration"""
    service = EvaluationService(db)
    try:
        evaluation = service.update_evaluation(evaluation_id, current_user.id, data)
        if not evaluation:
            raise HTTPException(status_code=404, detail="Evaluation not found")
        return _build_evaluation_response(evaluation)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{evaluation_id}")
async def delete_evaluation(
    evaluation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an evaluation and all its runs"""
    service = EvaluationService(db)
    success = service.delete_evaluation(evaluation_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return {"message": "Evaluation deleted"}


# ===== Evaluation Run Endpoints (nested under evaluation) =====

@router.post("/{evaluation_id}/runs", response_model=EvaluationRunResponse)
async def create_run(
    evaluation_id: int,
    data: EvaluationRunCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new run for an evaluation (specify agent to test)"""
    runner = EvaluationRunner(db)
    try:
        run = runner.create_run(current_user.id, evaluation_id, data)
        return _build_run_response(run)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{evaluation_id}/runs", response_model=EvaluationRunListResponse)
async def list_evaluation_runs(
    evaluation_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    agent_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List runs for a specific evaluation"""
    runner = EvaluationRunner(db)
    runs, total = runner.list_runs(
        current_user.id,
        page=page,
        page_size=page_size,
        status=status,
        evaluation_id=evaluation_id,
        agent_id=agent_id
    )

    run_responses = [_build_run_response(run) for run in runs]

    return EvaluationRunListResponse(
        runs=run_responses,
        total=total,
        page=page,
        page_size=page_size
    )


# NOTE: compare_runs must be defined BEFORE the dynamic /runs/{run_id} routes
@router.get("/runs/compare")
async def compare_runs(
    run_ids: str = Query(..., description="Comma-separated run IDs"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Compare multiple evaluation runs"""
    runner = EvaluationRunner(db)
    ids = [int(id.strip()) for id in run_ids.split(",")]

    runs = []
    metrics = {}

    for run_id in ids:
        run = runner.get_run_with_details(run_id, current_user.id)
        if run:
            runs.append({
                "run_id": run.id,
                "run_name": run.name,
                "agent_name": run.agent.name if run.agent else None,
                "agent_version_id": run.agent_version_id,
                "status": run.status,
                "pass_rate": run.metrics.get("pass_rate", 0) if run.metrics else 0,
                "avg_score": run.metrics.get("avg_score", 0) if run.metrics else 0,
                "total_examples": run.total_examples,
                "completed_at": run.completed_at
            })
            metrics[run.id] = run.metrics

    return {
        "runs": runs,
        "metrics_comparison": metrics
    }


@router.get("/{evaluation_id}/runs/{run_id}", response_model=EvaluationRunDetailResponse)
async def get_run(
    evaluation_id: int,
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get detailed evaluation run info"""
    runner = EvaluationRunner(db)
    run = runner.get_run_with_details(run_id, current_user.id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Verify run belongs to the specified evaluation
    if run.evaluation_id != evaluation_id:
        raise HTTPException(status_code=404, detail="Run not found in this evaluation")

    response = _build_run_response(run)
    response_dict = response.model_dump()
    # Get evaluation config response
    response_dict["evaluation"] = _build_evaluation_response(run.evaluation) if run.evaluation else None
    # Get evaluators from evaluation
    response_dict["evaluators"] = [
        EvaluatorResponse.model_validate(e) for e in (run.evaluation.evaluators if run.evaluation else [])
    ]

    return EvaluationRunDetailResponse(**response_dict)


@router.post("/{evaluation_id}/runs/{run_id}/execute", response_model=EvaluationRunResponse)
async def execute_run(
    evaluation_id: int,
    run_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start executing an evaluation run in the background"""
    from ...database import SessionLocal

    runner = EvaluationRunner(db, user_id=current_user.id)
    run = runner.get_run(run_id, current_user.id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if run.status not in ["pending", "failed"]:
        raise HTTPException(status_code=400, detail=f"Run is already {run.status}")

    # Mark as running immediately so the UI shows the status change
    run.status = "running"
    run.started_at = datetime.utcnow()
    db.commit()

    # Capture user_id for the background task (current_user won't be available)
    user_id = current_user.id

    # Execute in background with a fresh database session
    async def _execute():
        # Create a fresh database session for the background task
        # The original session from get_db() is closed when the request completes
        bg_db = SessionLocal()
        try:
            bg_runner = EvaluationRunner(bg_db, user_id=user_id)
            await bg_runner.execute_run(run_id, user_id)
        except Exception as e:
            # Log error - the run status should already be updated
            import logging
            logging.getLogger(__name__).exception(f"Evaluation run {run_id} failed: {e}")
        finally:
            bg_db.close()

    background_tasks.add_task(_execute)

    # Refresh the run to get the updated status and return it
    db.refresh(run)
    return _build_run_response(run)


@router.post("/{evaluation_id}/runs/{run_id}/cancel")
async def cancel_run(
    evaluation_id: int,
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel a running evaluation"""
    runner = EvaluationRunner(db)
    success = runner.cancel_run(run_id, current_user.id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot cancel run")
    return {"message": "Run cancelled"}


@router.delete("/{evaluation_id}/runs/{run_id}")
async def delete_run(
    evaluation_id: int,
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an evaluation run"""
    runner = EvaluationRunner(db)
    success = runner.delete_run(run_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"message": "Run deleted"}


# ===== Evaluation Result Endpoints =====

@router.get("/{evaluation_id}/runs/{run_id}/results")
async def list_results(
    evaluation_id: int,
    run_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status: Optional[str] = None,
    include_scores: bool = Query(False, description="Include individual evaluator scores for each result"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List results for an evaluation run"""
    runner = EvaluationRunner(db)
    results, total = runner.get_results(
        run_id,
        current_user.id,
        page=page,
        page_size=page_size,
        status=status
    )

    if include_scores:
        # Build detailed responses with scores
        result_responses = []
        for r in results:
            response = _build_result_response(r)
            response_dict = response.model_dump()
            response_dict["scores"] = [
                {
                    "id": s.id,
                    "evaluator_id": s.evaluator_id,
                    "evaluator_name": s.evaluator.name if s.evaluator else None,
                    "evaluator_type": s.evaluator.type if s.evaluator else None,
                    "evaluator_category": s.evaluator.category if s.evaluator else None,
                    "score": float(s.score) if s.score is not None else None,
                    "passed": s.passed,
                    "feedback": s.feedback,
                    "metadata": s.score_metadata,
                    "status": s.status,
                    "session_id": s.session_id,
                    "created_at": s.created_at
                }
                for s in (r.scores if hasattr(r, 'scores') and r.scores else [])
            ]
            result_responses.append(EvaluationResultDetailResponse(**response_dict))

        return {
            "results": result_responses,
            "total": total,
            "page": page,
            "page_size": page_size
        }
    else:
        result_responses = [_build_result_response(r) for r in results]
        return EvaluationResultListResponse(
            results=result_responses,
            total=total,
            page=page,
            page_size=page_size
        )


@router.get("/{evaluation_id}/runs/{run_id}/results/{result_id}", response_model=EvaluationResultDetailResponse)
async def get_result(
    evaluation_id: int,
    run_id: int,
    result_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get detailed result with all scores"""
    runner = EvaluationRunner(db)
    result = runner.get_result_detail(run_id, result_id, current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")

    response = _build_result_response(result)
    response_dict = response.model_dump()
    response_dict["scores"] = [
        {
            "id": s.id,
            "evaluator_id": s.evaluator_id,
            "evaluator_name": s.evaluator.name if s.evaluator else None,
            "evaluator_type": s.evaluator.type if s.evaluator else None,
            "evaluator_category": s.evaluator.category if s.evaluator else None,
            "score": s.score,
            "passed": s.passed,
            "feedback": s.feedback,
            "metadata": s.score_metadata,
            "status": s.status,
            "session_id": s.session_id,
            "created_at": s.created_at
        }
        for s in result.scores
    ]

    return EvaluationResultDetailResponse(**response_dict)


# ===== Helper Functions =====

def _build_evaluation_response(evaluation) -> EvaluationResponse:
    """Build evaluation response with nested info"""
    return EvaluationResponse(
        id=evaluation.id,
        user_id=evaluation.user_id,
        name=evaluation.name,
        description=evaluation.description,
        dataset_id=evaluation.dataset_id,
        config=evaluation.config or {},
        is_active=evaluation.is_active,
        created_at=evaluation.created_at,
        updated_at=evaluation.updated_at,
        dataset_name=evaluation.dataset.name if evaluation.dataset else None,
        evaluator_count=len(evaluation.evaluators) if evaluation.evaluators else 0,
        run_count=len(evaluation.runs) if evaluation.runs else 0,
    )


def _build_evaluation_detail_response(evaluation) -> EvaluationDetailResponse:
    """Build detailed evaluation response with evaluators and dataset"""
    response = _build_evaluation_response(evaluation)
    response_dict = response.model_dump()
    response_dict["evaluators"] = [
        EvaluatorResponse.model_validate(e) for e in (evaluation.evaluators or [])
    ]
    response_dict["dataset"] = evaluation.dataset
    return EvaluationDetailResponse(**response_dict)


def _build_run_response(run) -> EvaluationRunResponse:
    """Build run response with nested info and computed fields"""
    # Compute passed/failed examples from metrics
    passed_examples = 0
    failed_examples = 0
    if run.metrics:
        # Calculate from completed and pass_rate
        completed = run.metrics.get("completed", 0)
        pass_rate = run.metrics.get("pass_rate", 0)
        if completed > 0 and pass_rate is not None:
            # pass_rate is 0-1, multiply by completed to get passed count
            passed_examples = int(round(completed * pass_rate))
            failed_examples = completed - passed_examples

    # Get dataset name from evaluation
    dataset_name = None
    evaluation_name = None
    if run.evaluation:
        evaluation_name = run.evaluation.name
        if run.evaluation.dataset:
            dataset_name = run.evaluation.dataset.name

    return EvaluationRunResponse(
        id=run.id,
        user_id=run.user_id,
        evaluation_id=run.evaluation_id,
        name=run.name,
        agent_id=run.agent_id,
        agent_version_id=run.agent_version_id,
        status=run.status,
        progress=run.progress,
        total_examples=run.total_examples,
        completed_examples=run.completed_examples,
        passed_examples=passed_examples,
        failed_examples=failed_examples,
        metrics=run.metrics,
        started_at=run.started_at,
        completed_at=run.completed_at,
        created_at=run.created_at,
        evaluation_name=evaluation_name,
        dataset_name=dataset_name,
        agent_name=run.agent.name if run.agent else None
    )


def _build_result_response(result) -> EvaluationResultResponse:
    """Build result response with nested info and computed aggregates"""
    # Compute passed and aggregate_score from scores if available
    passed = None
    aggregate_score = None

    if hasattr(result, 'scores') and result.scores:
        # All scores must pass for the result to pass
        scores_with_passed = [s for s in result.scores if s.passed is not None]
        if scores_with_passed:
            passed = all(s.passed for s in scores_with_passed)

        # Calculate average score
        scores_with_value = [float(s.score) for s in result.scores if s.score is not None]
        if scores_with_value:
            aggregate_score = sum(scores_with_value) / len(scores_with_value)

    return EvaluationResultResponse(
        id=result.id,
        run_id=result.run_id,
        example_id=result.example_id,
        session_id=result.session_id,
        agent_output=result.agent_output,
        run_metadata=result.run_metadata,
        status=result.status,
        latency_ms=result.latency_ms,
        token_usage_input=result.token_usage_input or 0,
        token_usage_output=result.token_usage_output or 0,
        cost=result.cost,
        error_message=result.error_message,
        created_at=result.created_at,
        completed_at=result.completed_at,
        example_name=result.example.name if result.example else None,
        example_input=result.example.input if result.example else None,
        example_expected_output=result.example.expected_output if result.example else None,
        passed=passed,
        aggregate_score=aggregate_score
    )
