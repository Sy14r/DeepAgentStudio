"""Tests for the DatasetService - evaluation dataset and example operations"""

import pytest
import json
from app.services.dataset_service import DatasetService
from app.schemas.evaluation import (
    EvaluationDatasetCreate,
    EvaluationDatasetUpdate,
    DatasetExampleCreate,
    DatasetExampleUpdate,
    DatasetExampleBatchCreate,
    DatasetSchemaType,
)
from app.models.evaluation import EvaluationDataset, DatasetExample


class TestDatasetService:
    """Tests for Dataset CRUD operations"""

    def test_create_dataset(self, db, test_user):
        """Test creating a new dataset"""
        service = DatasetService(db)

        data = EvaluationDatasetCreate(
            name="Test Dataset",
            description="A test dataset for evaluation",
            schema_type=DatasetSchemaType.TEXT,
            tags=["test", "evaluation"]
        )

        dataset = service.create_dataset(test_user.id, data)

        assert dataset is not None
        assert dataset.id is not None
        assert dataset.name == "Test Dataset"
        assert dataset.description == "A test dataset for evaluation"
        assert dataset.schema_type == "text"
        assert dataset.tags == ["test", "evaluation"]
        assert dataset.example_count == 0
        assert dataset.user_id == test_user.id

    def test_create_dataset_with_schema(self, db, test_user):
        """Test creating a dataset with input/output schemas"""
        service = DatasetService(db)

        data = EvaluationDatasetCreate(
            name="Structured Dataset",
            schema_type=DatasetSchemaType.STRUCTURED,
            input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
            output_schema={"type": "object", "properties": {"answer": {"type": "string"}}}
        )

        dataset = service.create_dataset(test_user.id, data)

        assert dataset.schema_type == "structured"
        assert dataset.input_schema is not None
        assert dataset.output_schema is not None

    def test_get_dataset(self, db, test_user):
        """Test retrieving a dataset by ID"""
        service = DatasetService(db)

        # Create a dataset first
        data = EvaluationDatasetCreate(name="Get Test Dataset")
        created = service.create_dataset(test_user.id, data)

        # Retrieve it
        dataset = service.get_dataset(created.id, test_user.id)

        assert dataset is not None
        assert dataset.id == created.id
        assert dataset.name == "Get Test Dataset"

    def test_get_dataset_wrong_user(self, db, test_user, second_test_user):
        """Test that users can't access other users' datasets"""
        service = DatasetService(db)

        # Create dataset for first user
        data = EvaluationDatasetCreate(name="Private Dataset")
        created = service.create_dataset(test_user.id, data)

        # Try to get it as second user
        dataset = service.get_dataset(created.id, second_test_user.id)

        assert dataset is None

    def test_get_dataset_not_found(self, db, test_user):
        """Test getting a non-existent dataset"""
        service = DatasetService(db)

        dataset = service.get_dataset(99999, test_user.id)

        assert dataset is None

    def test_list_datasets(self, db, test_user):
        """Test listing datasets with pagination"""
        service = DatasetService(db)

        # Create multiple datasets
        for i in range(5):
            data = EvaluationDatasetCreate(name=f"Dataset {i}")
            service.create_dataset(test_user.id, data)

        # List first page
        datasets, total = service.list_datasets(test_user.id, page=1, page_size=3)

        assert total == 5
        assert len(datasets) == 3

    def test_list_datasets_search(self, db, test_user):
        """Test searching datasets"""
        service = DatasetService(db)

        # Create datasets with different names
        service.create_dataset(test_user.id, EvaluationDatasetCreate(name="Alpha Dataset"))
        service.create_dataset(test_user.id, EvaluationDatasetCreate(name="Beta Dataset"))
        service.create_dataset(test_user.id, EvaluationDatasetCreate(name="Alpha Test"))

        # Search for "Alpha"
        datasets, total = service.list_datasets(test_user.id, search="Alpha")

        assert total == 2

    def test_list_datasets_tags_filter(self, db, test_user):
        """Test filtering datasets by tags"""
        service = DatasetService(db)

        service.create_dataset(test_user.id, EvaluationDatasetCreate(name="Dataset 1", tags=["qa", "test"]))
        service.create_dataset(test_user.id, EvaluationDatasetCreate(name="Dataset 2", tags=["prod"]))
        service.create_dataset(test_user.id, EvaluationDatasetCreate(name="Dataset 3", tags=["qa"]))

        # Filter by "qa" tag
        datasets, total = service.list_datasets(test_user.id, tags=["qa"])

        assert total == 2

    def test_update_dataset(self, db, test_user):
        """Test updating a dataset"""
        service = DatasetService(db)

        # Create dataset
        data = EvaluationDatasetCreate(name="Original Name")
        created = service.create_dataset(test_user.id, data)

        # Update it
        update_data = EvaluationDatasetUpdate(
            name="Updated Name",
            description="New description"
        )
        updated = service.update_dataset(created.id, test_user.id, update_data)

        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.description == "New description"

    def test_update_dataset_wrong_user(self, db, test_user, second_test_user):
        """Test that users can't update other users' datasets"""
        service = DatasetService(db)

        # Create dataset for first user
        created = service.create_dataset(test_user.id, EvaluationDatasetCreate(name="My Dataset"))

        # Try to update as second user
        updated = service.update_dataset(
            created.id,
            second_test_user.id,
            EvaluationDatasetUpdate(name="Hacked")
        )

        assert updated is None

    def test_delete_dataset(self, db, test_user):
        """Test deleting a dataset"""
        service = DatasetService(db)

        # Create dataset
        created = service.create_dataset(test_user.id, EvaluationDatasetCreate(name="To Delete"))

        # Delete it
        result = service.delete_dataset(created.id, test_user.id)

        assert result is True

        # Verify it's gone
        dataset = service.get_dataset(created.id, test_user.id)
        assert dataset is None

    def test_delete_dataset_wrong_user(self, db, test_user, second_test_user):
        """Test that users can't delete other users' datasets"""
        service = DatasetService(db)

        # Create dataset for first user
        created = service.create_dataset(test_user.id, EvaluationDatasetCreate(name="Protected"))

        # Try to delete as second user
        result = service.delete_dataset(created.id, second_test_user.id)

        assert result is False

        # Verify it still exists
        dataset = service.get_dataset(created.id, test_user.id)
        assert dataset is not None


class TestDatasetExampleService:
    """Tests for Dataset Example CRUD operations"""

    def test_create_example(self, db, test_user):
        """Test creating a dataset example"""
        service = DatasetService(db)

        # Create dataset first
        dataset = service.create_dataset(test_user.id, EvaluationDatasetCreate(name="Test Dataset"))

        # Create example
        example_data = DatasetExampleCreate(
            name="Test Example",
            input="What is the capital of France?",
            expected_output="Paris",
            tags=["geography"]
        )

        example = service.create_example(dataset.id, test_user.id, example_data)

        assert example is not None
        assert example.name == "Test Example"
        assert example.input == "What is the capital of France?"
        assert example.expected_output == "Paris"
        assert example.tags == ["geography"]

        # Verify example count updated
        updated_dataset = service.get_dataset(dataset.id, test_user.id)
        assert updated_dataset.example_count == 1

    def test_create_example_with_context(self, db, test_user):
        """Test creating an example with context and metadata"""
        service = DatasetService(db)

        dataset = service.create_dataset(test_user.id, EvaluationDatasetCreate(name="Test Dataset"))

        example_data = DatasetExampleCreate(
            name="Context Example",
            input="Summarize the passage",
            expected_output="The passage discusses...",
            context={"passage": "Long text here..."},
            metadata={"source": "wikipedia", "difficulty": "easy"}
        )

        example = service.create_example(dataset.id, test_user.id, example_data)

        assert example.context is not None
        assert example.example_metadata is not None
        assert example.example_metadata["source"] == "wikipedia"

    def test_create_example_wrong_dataset(self, db, test_user, second_test_user):
        """Test that examples can't be added to other users' datasets"""
        service = DatasetService(db)

        # Create dataset for first user
        dataset = service.create_dataset(test_user.id, EvaluationDatasetCreate(name="Private"))

        # Try to add example as second user
        example_data = DatasetExampleCreate(input="test", expected_output="test")
        example = service.create_example(dataset.id, second_test_user.id, example_data)

        assert example is None

    def test_create_examples_batch(self, db, test_user):
        """Test batch creation of examples"""
        service = DatasetService(db)

        dataset = service.create_dataset(test_user.id, EvaluationDatasetCreate(name="Batch Dataset"))

        batch_data = DatasetExampleBatchCreate(
            examples=[
                DatasetExampleCreate(name="Ex1", input="Input 1", expected_output="Output 1"),
                DatasetExampleCreate(name="Ex2", input="Input 2", expected_output="Output 2"),
                DatasetExampleCreate(name="Ex3", input="Input 3", expected_output="Output 3"),
            ]
        )

        examples, count = service.create_examples_batch(dataset.id, test_user.id, batch_data)

        assert count == 3
        assert len(examples) == 3

        # Verify dataset example count
        updated_dataset = service.get_dataset(dataset.id, test_user.id)
        assert updated_dataset.example_count == 3

    def test_get_example(self, db, test_user):
        """Test retrieving a specific example"""
        service = DatasetService(db)

        dataset = service.create_dataset(test_user.id, EvaluationDatasetCreate(name="Test"))
        example = service.create_example(
            dataset.id, test_user.id,
            DatasetExampleCreate(input="test", expected_output="expected")
        )

        retrieved = service.get_example(dataset.id, example.id, test_user.id)

        assert retrieved is not None
        assert retrieved.id == example.id

    def test_list_examples(self, db, test_user):
        """Test listing examples with pagination"""
        service = DatasetService(db)

        dataset = service.create_dataset(test_user.id, EvaluationDatasetCreate(name="Test"))

        for i in range(10):
            service.create_example(
                dataset.id, test_user.id,
                DatasetExampleCreate(name=f"Example {i}", input=f"input {i}", expected_output=f"output {i}")
            )

        examples, total = service.list_examples(dataset.id, test_user.id, page=1, page_size=5)

        assert total == 10
        assert len(examples) == 5

    def test_list_examples_search(self, db, test_user):
        """Test searching examples by name"""
        service = DatasetService(db)

        dataset = service.create_dataset(test_user.id, EvaluationDatasetCreate(name="Test"))

        service.create_example(dataset.id, test_user.id, DatasetExampleCreate(name="Capital Question", input="a", expected_output="b"))
        service.create_example(dataset.id, test_user.id, DatasetExampleCreate(name="Math Question", input="c", expected_output="d"))
        service.create_example(dataset.id, test_user.id, DatasetExampleCreate(name="Capital Test", input="e", expected_output="f"))

        examples, total = service.list_examples(dataset.id, test_user.id, search="Capital")

        assert total == 2

    def test_update_example(self, db, test_user):
        """Test updating an example"""
        service = DatasetService(db)

        dataset = service.create_dataset(test_user.id, EvaluationDatasetCreate(name="Test"))
        example = service.create_example(
            dataset.id, test_user.id,
            DatasetExampleCreate(name="Original", input="test", expected_output="expected")
        )

        updated = service.update_example(
            dataset.id, example.id, test_user.id,
            DatasetExampleUpdate(name="Updated", expected_output="new expected")
        )

        assert updated is not None
        assert updated.name == "Updated"
        assert updated.expected_output == "new expected"
        assert updated.input == "test"  # Unchanged

    def test_delete_example(self, db, test_user):
        """Test deleting an example"""
        service = DatasetService(db)

        dataset = service.create_dataset(test_user.id, EvaluationDatasetCreate(name="Test"))
        example = service.create_example(
            dataset.id, test_user.id,
            DatasetExampleCreate(input="test", expected_output="expected")
        )

        result = service.delete_example(dataset.id, example.id, test_user.id)

        assert result is True

        # Verify it's gone
        retrieved = service.get_example(dataset.id, example.id, test_user.id)
        assert retrieved is None

        # Verify example count updated
        updated_dataset = service.get_dataset(dataset.id, test_user.id)
        assert updated_dataset.example_count == 0

    def test_delete_examples_batch(self, db, test_user):
        """Test batch deletion of examples"""
        service = DatasetService(db)

        dataset = service.create_dataset(test_user.id, EvaluationDatasetCreate(name="Test"))

        examples = []
        for i in range(5):
            ex = service.create_example(
                dataset.id, test_user.id,
                DatasetExampleCreate(input=f"input {i}", expected_output=f"output {i}")
            )
            examples.append(ex)

        # Delete first 3 examples
        ids_to_delete = [examples[0].id, examples[1].id, examples[2].id]
        deleted = service.delete_examples_batch(dataset.id, ids_to_delete, test_user.id)

        assert deleted == 3

        # Verify count updated
        updated_dataset = service.get_dataset(dataset.id, test_user.id)
        assert updated_dataset.example_count == 2


class TestDatasetImportExport:
    """Tests for dataset import/export functionality"""

    def test_import_from_csv(self, db, test_user):
        """Test importing examples from CSV"""
        service = DatasetService(db)

        dataset = service.create_dataset(test_user.id, EvaluationDatasetCreate(name="CSV Import"))

        csv_content = """name,input,expected_output,tags
Example 1,What is 2+2?,4,math
Example 2,What is the capital of Spain?,Madrid,geography
"""

        imported, skipped, errors = service.import_from_csv(dataset.id, test_user.id, csv_content)

        assert imported == 2
        assert skipped == 0
        assert len(errors) == 0

        # Verify examples were created
        examples, total = service.list_examples(dataset.id, test_user.id)
        assert total == 2

    def test_import_from_csv_missing_columns(self, db, test_user):
        """Test CSV import fails with missing required columns"""
        service = DatasetService(db)

        dataset = service.create_dataset(test_user.id, EvaluationDatasetCreate(name="CSV Import"))

        csv_content = """name,input
Example 1,What is 2+2?
"""

        imported, skipped, errors = service.import_from_csv(dataset.id, test_user.id, csv_content)

        assert imported == 0
        assert "must have 'input' and 'expected_output' columns" in errors[0]

    def test_import_from_csv_skip_empty_rows(self, db, test_user):
        """Test that CSV import skips rows with empty required fields"""
        service = DatasetService(db)

        dataset = service.create_dataset(test_user.id, EvaluationDatasetCreate(name="CSV Import"))

        csv_content = """name,input,expected_output
Example 1,What is 2+2?,4
Example 2,,Missing input
Example 3,Has input,
"""

        imported, skipped, errors = service.import_from_csv(dataset.id, test_user.id, csv_content)

        assert imported == 1
        assert skipped == 2

    def test_import_from_json(self, db, test_user):
        """Test importing examples from JSON"""
        service = DatasetService(db)

        dataset = service.create_dataset(test_user.id, EvaluationDatasetCreate(name="JSON Import"))

        json_content = json.dumps({
            "examples": [
                {"name": "Ex1", "input": "Question 1", "expected_output": "Answer 1"},
                {"name": "Ex2", "input": "Question 2", "expected_output": "Answer 2", "tags": ["tag1"]}
            ]
        })

        imported, skipped, errors = service.import_from_json(dataset.id, test_user.id, json_content)

        assert imported == 2
        assert skipped == 0

    def test_import_from_json_invalid(self, db, test_user):
        """Test JSON import with invalid JSON"""
        service = DatasetService(db)

        dataset = service.create_dataset(test_user.id, EvaluationDatasetCreate(name="JSON Import"))

        imported, skipped, errors = service.import_from_json(dataset.id, test_user.id, "not valid json")

        assert imported == 0
        assert "JSON parsing error" in errors[0]

    def test_import_from_json_no_examples(self, db, test_user):
        """Test JSON import with missing examples array"""
        service = DatasetService(db)

        dataset = service.create_dataset(test_user.id, EvaluationDatasetCreate(name="JSON Import"))

        json_content = json.dumps({"data": []})

        imported, skipped, errors = service.import_from_json(dataset.id, test_user.id, json_content)

        assert imported == 0
        assert "No examples found" in errors[0]

    def test_export_to_csv(self, db, test_user):
        """Test exporting dataset to CSV"""
        service = DatasetService(db)

        dataset = service.create_dataset(test_user.id, EvaluationDatasetCreate(name="Export Test"))

        service.create_example(
            dataset.id, test_user.id,
            DatasetExampleCreate(name="Ex1", input="Question", expected_output="Answer", tags=["tag1", "tag2"])
        )

        csv_output = service.export_to_csv(dataset.id, test_user.id)

        assert csv_output is not None
        assert "name,input,expected_output" in csv_output
        assert "Ex1" in csv_output
        assert "Question" in csv_output
        assert "tag1,tag2" in csv_output

    def test_export_to_csv_not_found(self, db, test_user):
        """Test CSV export with non-existent dataset"""
        service = DatasetService(db)

        result = service.export_to_csv(99999, test_user.id)

        assert result is None

    def test_export_to_json(self, db, test_user):
        """Test exporting dataset to JSON"""
        service = DatasetService(db)

        dataset = service.create_dataset(
            test_user.id,
            EvaluationDatasetCreate(name="Export Test", description="Test description")
        )

        service.create_example(
            dataset.id, test_user.id,
            DatasetExampleCreate(
                name="Ex1",
                input="Question",
                expected_output="Answer",
                context={"key": "value"}
            )
        )

        json_output = service.export_to_json(dataset.id, test_user.id)

        assert json_output is not None

        data = json.loads(json_output)
        assert data["dataset"]["name"] == "Export Test"
        assert data["dataset"]["description"] == "Test description"
        assert len(data["examples"]) == 1
        assert data["examples"][0]["name"] == "Ex1"
        assert data["examples"][0]["context"] == {"key": "value"}

    def test_export_to_json_not_found(self, db, test_user):
        """Test JSON export with non-existent dataset"""
        service = DatasetService(db)

        result = service.export_to_json(99999, test_user.id)

        assert result is None

    def test_import_wrong_dataset_user(self, db, test_user, second_test_user):
        """Test that users can't import to other users' datasets"""
        service = DatasetService(db)

        # Create dataset for first user
        dataset = service.create_dataset(test_user.id, EvaluationDatasetCreate(name="Private"))

        # Try to import as second user
        json_content = json.dumps({"examples": [{"input": "test", "expected_output": "test"}]})
        imported, skipped, errors = service.import_from_json(dataset.id, second_test_user.id, json_content)

        assert imported == 0
        assert "Dataset not found" in errors[0]
