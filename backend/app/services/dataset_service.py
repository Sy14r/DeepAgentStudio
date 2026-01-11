"""Service for managing evaluation datasets and examples"""

import csv
import io
import json
import base64
from typing import Optional
from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from ..models.evaluation import EvaluationDataset, DatasetExample
from ..schemas.evaluation import (
    EvaluationDatasetCreate,
    EvaluationDatasetUpdate,
    DatasetExampleCreate,
    DatasetExampleUpdate,
    DatasetExampleBatchCreate,
)


class DatasetService:
    """Service for evaluation dataset operations"""

    def __init__(self, db: Session):
        self.db = db

    # ===== Dataset Operations =====

    def create_dataset(self, user_id: int, data: EvaluationDatasetCreate) -> EvaluationDataset:
        """Create a new evaluation dataset"""
        dataset = EvaluationDataset(
            user_id=user_id,
            name=data.name,
            description=data.description,
            schema_type=data.schema_type.value if data.schema_type else "text",
            input_schema=data.input_schema,
            output_schema=data.output_schema,
            tags=data.tags,
            example_count=0,
        )
        self.db.add(dataset)
        self.db.commit()
        self.db.refresh(dataset)
        return dataset

    def get_dataset(self, dataset_id: int, user_id: int) -> Optional[EvaluationDataset]:
        """Get a dataset by ID for a specific user"""
        return self.db.query(EvaluationDataset).filter(
            EvaluationDataset.id == dataset_id,
            EvaluationDataset.user_id == user_id
        ).first()

    def get_dataset_with_examples(self, dataset_id: int, user_id: int) -> Optional[EvaluationDataset]:
        """Get a dataset with all examples loaded"""
        return self.db.query(EvaluationDataset).options(
            joinedload(EvaluationDataset.examples)
        ).filter(
            EvaluationDataset.id == dataset_id,
            EvaluationDataset.user_id == user_id
        ).first()

    def list_datasets(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> tuple[list[EvaluationDataset], int]:
        """List datasets with pagination and filtering"""
        query = self.db.query(EvaluationDataset).filter(
            EvaluationDataset.user_id == user_id
        )

        # Search filter
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                EvaluationDataset.name.ilike(search_term) |
                EvaluationDataset.description.ilike(search_term)
            )

        # Tags filter
        if tags:
            query = query.filter(EvaluationDataset.tags.overlap(tags))

        # Get total count
        total = query.count()

        # Apply pagination
        datasets = query.order_by(EvaluationDataset.updated_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size).all()

        return datasets, total

    def update_dataset(
        self, dataset_id: int, user_id: int, data: EvaluationDatasetUpdate
    ) -> Optional[EvaluationDataset]:
        """Update a dataset"""
        dataset = self.get_dataset(dataset_id, user_id)
        if not dataset:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "schema_type" and value:
                setattr(dataset, field, value.value)
            else:
                setattr(dataset, field, value)

        dataset.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(dataset)
        return dataset

    def delete_dataset(self, dataset_id: int, user_id: int) -> bool:
        """Delete a dataset and all its examples"""
        dataset = self.get_dataset(dataset_id, user_id)
        if not dataset:
            return False

        self.db.delete(dataset)
        self.db.commit()
        return True

    def _update_example_count(self, dataset_id: int):
        """Update the cached example count for a dataset"""
        count = self.db.query(func.count(DatasetExample.id)).filter(
            DatasetExample.dataset_id == dataset_id
        ).scalar()

        self.db.query(EvaluationDataset).filter(
            EvaluationDataset.id == dataset_id
        ).update({"example_count": count, "updated_at": datetime.utcnow()})
        self.db.commit()

    # ===== Example Operations =====

    def create_example(
        self, dataset_id: int, user_id: int, data: DatasetExampleCreate
    ) -> Optional[DatasetExample]:
        """Create a new example in a dataset"""
        # Verify dataset ownership
        dataset = self.get_dataset(dataset_id, user_id)
        if not dataset:
            return None

        example = DatasetExample(
            dataset_id=dataset_id,
            name=data.name,
            input=data.input,
            expected_output=data.expected_output,
            context=data.context,
            example_metadata=data.metadata,
            tags=data.tags,
        )
        self.db.add(example)
        self.db.commit()
        self.db.refresh(example)

        # Update count
        self._update_example_count(dataset_id)

        return example

    def create_examples_batch(
        self, dataset_id: int, user_id: int, data: DatasetExampleBatchCreate
    ) -> tuple[list[DatasetExample], int]:
        """Create multiple examples at once"""
        # Verify dataset ownership
        dataset = self.get_dataset(dataset_id, user_id)
        if not dataset:
            return [], 0

        examples = []
        for example_data in data.examples:
            example = DatasetExample(
                dataset_id=dataset_id,
                name=example_data.name,
                input=example_data.input,
                expected_output=example_data.expected_output,
                context=example_data.context,
                example_metadata=example_data.metadata,
                tags=example_data.tags,
            )
            self.db.add(example)
            examples.append(example)

        self.db.commit()
        for example in examples:
            self.db.refresh(example)

        # Update count
        self._update_example_count(dataset_id)

        return examples, len(examples)

    def get_example(
        self, dataset_id: int, example_id: int, user_id: int
    ) -> Optional[DatasetExample]:
        """Get a specific example"""
        # Verify dataset ownership first
        dataset = self.get_dataset(dataset_id, user_id)
        if not dataset:
            return None

        return self.db.query(DatasetExample).filter(
            DatasetExample.id == example_id,
            DatasetExample.dataset_id == dataset_id
        ).first()

    def list_examples(
        self,
        dataset_id: int,
        user_id: int,
        page: int = 1,
        page_size: int = 50,
        search: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> tuple[list[DatasetExample], int]:
        """List examples with pagination"""
        # Verify dataset ownership
        dataset = self.get_dataset(dataset_id, user_id)
        if not dataset:
            return [], 0

        query = self.db.query(DatasetExample).filter(
            DatasetExample.dataset_id == dataset_id
        )

        # Search filter (searches in name and input)
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                DatasetExample.name.ilike(search_term)
            )

        # Tags filter
        if tags:
            query = query.filter(DatasetExample.tags.overlap(tags))

        total = query.count()

        examples = query.order_by(DatasetExample.id).offset(
            (page - 1) * page_size
        ).limit(page_size).all()

        return examples, total

    def update_example(
        self, dataset_id: int, example_id: int, user_id: int, data: DatasetExampleUpdate
    ) -> Optional[DatasetExample]:
        """Update an example"""
        example = self.get_example(dataset_id, example_id, user_id)
        if not example:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(example, field, value)

        example.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(example)
        return example

    def delete_example(self, dataset_id: int, example_id: int, user_id: int) -> bool:
        """Delete an example"""
        example = self.get_example(dataset_id, example_id, user_id)
        if not example:
            return False

        self.db.delete(example)
        self.db.commit()

        # Update count
        self._update_example_count(dataset_id)

        return True

    def delete_examples_batch(
        self, dataset_id: int, example_ids: list[int], user_id: int
    ) -> int:
        """Delete multiple examples at once"""
        # Verify dataset ownership
        dataset = self.get_dataset(dataset_id, user_id)
        if not dataset:
            return 0

        deleted = self.db.query(DatasetExample).filter(
            DatasetExample.id.in_(example_ids),
            DatasetExample.dataset_id == dataset_id
        ).delete(synchronize_session=False)

        self.db.commit()

        # Update count
        self._update_example_count(dataset_id)

        return deleted

    # ===== Import/Export Operations =====

    def import_from_csv(
        self, dataset_id: int, user_id: int, csv_content: str
    ) -> tuple[int, int, list[str]]:
        """
        Import examples from CSV content.
        Expected columns: name (optional), input, expected_output, tags (optional, comma-separated)
        Returns: (imported_count, skipped_count, errors)
        """
        dataset = self.get_dataset(dataset_id, user_id)
        if not dataset:
            return 0, 0, ["Dataset not found"]

        errors = []
        imported = 0
        skipped = 0

        try:
            reader = csv.DictReader(io.StringIO(csv_content))

            # Validate required columns
            if "input" not in reader.fieldnames or "expected_output" not in reader.fieldnames:
                return 0, 0, ["CSV must have 'input' and 'expected_output' columns"]

            for row_num, row in enumerate(reader, start=2):
                try:
                    input_val = row.get("input", "").strip()
                    expected_output = row.get("expected_output", "").strip()

                    if not input_val or not expected_output:
                        skipped += 1
                        errors.append(f"Row {row_num}: Missing input or expected_output")
                        continue

                    # Parse tags if present
                    tags = None
                    if row.get("tags"):
                        tags = [t.strip() for t in row["tags"].split(",") if t.strip()]

                    # Parse metadata if present
                    metadata = None
                    if row.get("metadata"):
                        try:
                            metadata = json.loads(row["metadata"])
                        except json.JSONDecodeError:
                            pass

                    example = DatasetExample(
                        dataset_id=dataset_id,
                        name=row.get("name", "").strip() or None,
                        input=input_val,
                        expected_output=expected_output,
                        context=row.get("context"),
                        example_metadata=metadata,
                        tags=tags,
                    )
                    self.db.add(example)
                    imported += 1

                except Exception as e:
                    skipped += 1
                    errors.append(f"Row {row_num}: {str(e)}")

            self.db.commit()
            self._update_example_count(dataset_id)

        except Exception as e:
            self.db.rollback()
            return 0, 0, [f"CSV parsing error: {str(e)}"]

        return imported, skipped, errors[:10]  # Limit errors returned

    def import_from_json(
        self, dataset_id: int, user_id: int, json_content: str
    ) -> tuple[int, int, list[str]]:
        """
        Import examples from JSON content.
        Expected format: {"examples": [{"input": "...", "expected_output": "...", ...}]}
        Returns: (imported_count, skipped_count, errors)
        """
        dataset = self.get_dataset(dataset_id, user_id)
        if not dataset:
            return 0, 0, ["Dataset not found"]

        errors = []
        imported = 0
        skipped = 0

        try:
            data = json.loads(json_content)
            examples_data = data.get("examples", [])

            if not examples_data:
                return 0, 0, ["No examples found in JSON"]

            for idx, example_data in enumerate(examples_data):
                try:
                    input_val = example_data.get("input")
                    expected_output = example_data.get("expected_output")

                    if not input_val or not expected_output:
                        skipped += 1
                        errors.append(f"Example {idx}: Missing input or expected_output")
                        continue

                    example = DatasetExample(
                        dataset_id=dataset_id,
                        name=example_data.get("name"),
                        input=input_val,
                        expected_output=expected_output,
                        context=example_data.get("context"),
                        example_metadata=example_data.get("metadata"),
                        tags=example_data.get("tags"),
                    )
                    self.db.add(example)
                    imported += 1

                except Exception as e:
                    skipped += 1
                    errors.append(f"Example {idx}: {str(e)}")

            self.db.commit()
            self._update_example_count(dataset_id)

        except json.JSONDecodeError as e:
            return 0, 0, [f"JSON parsing error: {str(e)}"]
        except Exception as e:
            self.db.rollback()
            return 0, 0, [f"Import error: {str(e)}"]

        return imported, skipped, errors[:10]

    def export_to_csv(self, dataset_id: int, user_id: int) -> Optional[str]:
        """Export dataset examples to CSV format"""
        dataset = self.get_dataset_with_examples(dataset_id, user_id)
        if not dataset:
            return None

        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(["name", "input", "expected_output", "context", "tags", "metadata"])

        for example in dataset.examples:
            writer.writerow([
                example.name or "",
                json.dumps(example.input) if isinstance(example.input, (dict, list)) else str(example.input),
                json.dumps(example.expected_output) if isinstance(example.expected_output, (dict, list)) else str(example.expected_output),
                json.dumps(example.context) if example.context else "",
                ",".join(example.tags) if example.tags else "",
                json.dumps(example.example_metadata) if example.example_metadata else "",
            ])

        return output.getvalue()

    def export_to_json(self, dataset_id: int, user_id: int) -> Optional[str]:
        """Export dataset examples to JSON format"""
        dataset = self.get_dataset_with_examples(dataset_id, user_id)
        if not dataset:
            return None

        examples_data = []
        for example in dataset.examples:
            examples_data.append({
                "name": example.name,
                "input": example.input,
                "expected_output": example.expected_output,
                "context": example.context,
                "metadata": example.example_metadata,
                "tags": example.tags,
            })

        return json.dumps({
            "dataset": {
                "id": dataset.id,
                "name": dataset.name,
                "description": dataset.description,
                "schema_type": dataset.schema_type,
            },
            "examples": examples_data
        }, indent=2)
