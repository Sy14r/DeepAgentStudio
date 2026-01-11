"""Service for managing evaluation configurations"""

from typing import Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc

from ..models.evaluation import Evaluation, EvaluationDataset, Evaluator, EvaluationRun
from ..schemas.evaluation import EvaluationCreate, EvaluationUpdate


class EvaluationService:
    """Service for CRUD operations on evaluation configurations"""

    def __init__(self, db: Session):
        self.db = db

    def create_evaluation(self, user_id: int, data: EvaluationCreate) -> Evaluation:
        """Create a new evaluation configuration"""
        # Verify dataset exists and belongs to user
        dataset = self.db.query(EvaluationDataset).filter(
            EvaluationDataset.id == data.dataset_id,
            EvaluationDataset.user_id == user_id
        ).first()

        if not dataset:
            raise ValueError(f"Dataset {data.dataset_id} not found or does not belong to user")

        # Verify all evaluators exist and are accessible (built-in or owned by user)
        evaluators = self.db.query(Evaluator).filter(
            Evaluator.id.in_(data.evaluator_ids),
            (Evaluator.is_builtin == True) | (Evaluator.user_id == user_id)
        ).all()

        if len(evaluators) != len(data.evaluator_ids):
            found_ids = {e.id for e in evaluators}
            missing_ids = set(data.evaluator_ids) - found_ids
            raise ValueError(f"Evaluators not found or not accessible: {missing_ids}")

        # Create evaluation
        evaluation = Evaluation(
            user_id=user_id,
            name=data.name,
            description=data.description,
            dataset_id=data.dataset_id,
            config=data.config.model_dump() if data.config else {},
        )
        self.db.add(evaluation)
        self.db.flush()

        # Associate evaluators
        evaluation.evaluators = evaluators
        self.db.commit()
        self.db.refresh(evaluation)

        return evaluation

    def get_evaluation(self, evaluation_id: int, user_id: int) -> Optional[Evaluation]:
        """Get evaluation by ID"""
        return self.db.query(Evaluation).filter(
            Evaluation.id == evaluation_id,
            Evaluation.user_id == user_id
        ).first()

    def get_evaluation_with_details(self, evaluation_id: int, user_id: int) -> Optional[Evaluation]:
        """Get evaluation with dataset, evaluators, and runs loaded"""
        return self.db.query(Evaluation).options(
            joinedload(Evaluation.dataset),
            joinedload(Evaluation.evaluators),
            joinedload(Evaluation.runs)
        ).filter(
            Evaluation.id == evaluation_id,
            Evaluation.user_id == user_id
        ).first()

    def list_evaluations(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 50,
        search: Optional[str] = None,
        dataset_id: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> tuple[list[Evaluation], int]:
        """List evaluations with pagination and filtering"""
        query = self.db.query(Evaluation).filter(Evaluation.user_id == user_id)

        if search:
            query = query.filter(Evaluation.name.ilike(f"%{search}%"))

        if dataset_id is not None:
            query = query.filter(Evaluation.dataset_id == dataset_id)

        if is_active is not None:
            query = query.filter(Evaluation.is_active == is_active)

        total = query.count()

        evaluations = query.options(
            joinedload(Evaluation.dataset),
            joinedload(Evaluation.evaluators),
        ).order_by(desc(Evaluation.updated_at)).offset(
            (page - 1) * page_size
        ).limit(page_size).all()

        return evaluations, total

    def update_evaluation(
        self,
        evaluation_id: int,
        user_id: int,
        data: EvaluationUpdate
    ) -> Optional[Evaluation]:
        """Update an evaluation configuration"""
        evaluation = self.get_evaluation(evaluation_id, user_id)
        if not evaluation:
            return None

        # Update simple fields
        if data.name is not None:
            evaluation.name = data.name
        if data.description is not None:
            evaluation.description = data.description
        if data.config is not None:
            evaluation.config = data.config.model_dump()

        # Update evaluators if provided
        if data.evaluator_ids is not None:
            evaluators = self.db.query(Evaluator).filter(
                Evaluator.id.in_(data.evaluator_ids),
                (Evaluator.is_builtin == True) | (Evaluator.user_id == user_id)
            ).all()

            if len(evaluators) != len(data.evaluator_ids):
                found_ids = {e.id for e in evaluators}
                missing_ids = set(data.evaluator_ids) - found_ids
                raise ValueError(f"Evaluators not found or not accessible: {missing_ids}")

            evaluation.evaluators = evaluators

        self.db.commit()
        self.db.refresh(evaluation)
        return evaluation

    def delete_evaluation(self, evaluation_id: int, user_id: int) -> bool:
        """Delete an evaluation and all its runs"""
        evaluation = self.get_evaluation(evaluation_id, user_id)
        if not evaluation:
            return False

        self.db.delete(evaluation)
        self.db.commit()
        return True

    def get_runs_for_evaluation(
        self,
        evaluation_id: int,
        user_id: int,
        page: int = 1,
        page_size: int = 50,
        status: Optional[str] = None,
    ) -> tuple[list[EvaluationRun], int]:
        """Get all runs for a specific evaluation"""
        # Verify evaluation belongs to user
        evaluation = self.get_evaluation(evaluation_id, user_id)
        if not evaluation:
            raise ValueError(f"Evaluation {evaluation_id} not found or does not belong to user")

        query = self.db.query(EvaluationRun).filter(
            EvaluationRun.evaluation_id == evaluation_id
        )

        if status:
            query = query.filter(EvaluationRun.status == status)

        total = query.count()

        runs = query.order_by(desc(EvaluationRun.created_at)).offset(
            (page - 1) * page_size
        ).limit(page_size).all()

        return runs, total

    def get_evaluation_stats(self, evaluation_id: int, user_id: int) -> dict:
        """Get statistics for an evaluation"""
        evaluation = self.get_evaluation_with_details(evaluation_id, user_id)
        if not evaluation:
            return {}

        # Count runs by status
        run_counts = self.db.query(
            EvaluationRun.status,
            func.count(EvaluationRun.id)
        ).filter(
            EvaluationRun.evaluation_id == evaluation_id
        ).group_by(EvaluationRun.status).all()

        status_counts = {status: count for status, count in run_counts}

        return {
            "total_runs": sum(status_counts.values()),
            "completed_runs": status_counts.get("completed", 0),
            "failed_runs": status_counts.get("failed", 0),
            "pending_runs": status_counts.get("pending", 0),
            "running_runs": status_counts.get("running", 0),
            "evaluator_count": len(evaluation.evaluators),
            "example_count": evaluation.dataset.example_count if evaluation.dataset else 0,
        }
