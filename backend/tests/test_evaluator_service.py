"""Tests for the EvaluatorService - evaluator CRUD and built-in seeding"""

import pytest
from app.services.evaluator_service import EvaluatorService, BUILTIN_EVALUATORS
from app.schemas.evaluation import EvaluatorCreate, EvaluatorUpdate, EvaluatorType, EvaluatorCategory
from app.models.evaluation import Evaluator


class TestBuiltinEvaluatorSeeding:
    """Tests for built-in evaluator seeding"""

    def test_seed_builtin_evaluators(self, db):
        """Test that built-in evaluators are seeded correctly"""
        service = EvaluatorService(db)

        created_count = service.seed_builtin_evaluators()

        # Should create all built-in evaluators
        assert created_count == len(BUILTIN_EVALUATORS)

        # Verify they exist in database
        evaluators = db.query(Evaluator).filter(Evaluator.is_builtin == True).all()
        assert len(evaluators) == len(BUILTIN_EVALUATORS)

    def test_seed_builtin_evaluators_idempotent(self, db):
        """Test that seeding is idempotent - doesn't create duplicates"""
        service = EvaluatorService(db)

        # Seed first time
        first_count = service.seed_builtin_evaluators()
        assert first_count == len(BUILTIN_EVALUATORS)

        # Seed second time
        second_count = service.seed_builtin_evaluators()
        assert second_count == 0

        # Verify no duplicates
        evaluators = db.query(Evaluator).filter(Evaluator.is_builtin == True).all()
        assert len(evaluators) == len(BUILTIN_EVALUATORS)

    def test_seed_builtin_evaluators_updates_config(self, db):
        """Test that seeding updates config/description if changed"""
        service = EvaluatorService(db)

        # First seed
        service.seed_builtin_evaluators()

        # Manually modify a built-in evaluator's config
        exact_match = db.query(Evaluator).filter(
            Evaluator.name == "Exact Match",
            Evaluator.is_builtin == True
        ).first()

        old_description = exact_match.description
        exact_match.description = "Modified description"
        db.commit()

        # Seed again - should update description back to original
        service.seed_builtin_evaluators()
        db.refresh(exact_match)

        assert exact_match.description == old_description

    def test_builtin_evaluator_has_all_categories(self, db):
        """Test that both evaluator categories are represented"""
        service = EvaluatorService(db)
        service.seed_builtin_evaluators()

        output_evaluators = db.query(Evaluator).filter(
            Evaluator.is_builtin == True,
            Evaluator.category == EvaluatorCategory.OUTPUT.value
        ).all()

        run_metadata_evaluators = db.query(Evaluator).filter(
            Evaluator.is_builtin == True,
            Evaluator.category == EvaluatorCategory.RUN_METADATA.value
        ).all()

        assert len(output_evaluators) > 0
        assert len(run_metadata_evaluators) > 0


class TestEvaluatorService:
    """Tests for Evaluator CRUD operations"""

    def test_create_evaluator(self, db, test_user):
        """Test creating a custom evaluator"""
        service = EvaluatorService(db)

        data = EvaluatorCreate(
            name="My Custom Evaluator",
            type=EvaluatorType.EXACT_MATCH,
            category=EvaluatorCategory.OUTPUT,
            description="A custom exact match evaluator",
            config={"case_sensitive": False, "strip_whitespace": True}
        )

        evaluator = service.create_evaluator(test_user.id, data)

        assert evaluator is not None
        assert evaluator.id is not None
        assert evaluator.name == "My Custom Evaluator"
        assert evaluator.type == EvaluatorType.EXACT_MATCH.value
        assert evaluator.category == EvaluatorCategory.OUTPUT.value
        assert evaluator.is_builtin is False
        assert evaluator.user_id == test_user.id
        assert evaluator.config["case_sensitive"] is False

    def test_create_evaluator_llm_judge(self, db, test_user):
        """Test creating an LLM judge evaluator with custom prompt"""
        service = EvaluatorService(db)

        data = EvaluatorCreate(
            name="Custom LLM Judge",
            type=EvaluatorType.LLM_JUDGE,
            category=EvaluatorCategory.OUTPUT,
            config={
                "model": "gpt-4o",
                "criteria": "custom_criteria",
                "prompt_template": "Evaluate if {actual_output} is better than {expected_output}"
            }
        )

        evaluator = service.create_evaluator(test_user.id, data)

        assert evaluator.type == EvaluatorType.LLM_JUDGE.value
        assert evaluator.config["model"] == "gpt-4o"

    def test_get_evaluator_own(self, db, test_user):
        """Test retrieving user's own evaluator"""
        service = EvaluatorService(db)

        created = service.create_evaluator(
            test_user.id,
            EvaluatorCreate(name="My Evaluator", type=EvaluatorType.CONTAINS, category=EvaluatorCategory.OUTPUT)
        )

        retrieved = service.get_evaluator(created.id, test_user.id)

        assert retrieved is not None
        assert retrieved.id == created.id

    def test_get_evaluator_builtin(self, db, test_user):
        """Test that users can retrieve built-in evaluators"""
        service = EvaluatorService(db)
        service.seed_builtin_evaluators()

        # Get a built-in evaluator
        builtin = db.query(Evaluator).filter(Evaluator.is_builtin == True).first()

        retrieved = service.get_evaluator(builtin.id, test_user.id)

        assert retrieved is not None
        assert retrieved.is_builtin is True

    def test_get_evaluator_other_user(self, db, test_user, second_test_user):
        """Test that users can't retrieve other users' evaluators"""
        service = EvaluatorService(db)

        # Create evaluator for first user
        created = service.create_evaluator(
            test_user.id,
            EvaluatorCreate(name="Private", type=EvaluatorType.CONTAINS, category=EvaluatorCategory.OUTPUT)
        )

        # Try to get as second user
        retrieved = service.get_evaluator(created.id, second_test_user.id)

        assert retrieved is None

    def test_get_evaluator_by_id_internal(self, db, test_user):
        """Test internal method to get any evaluator by ID"""
        service = EvaluatorService(db)

        created = service.create_evaluator(
            test_user.id,
            EvaluatorCreate(name="Test", type=EvaluatorType.CONTAINS, category=EvaluatorCategory.OUTPUT)
        )

        # Internal method doesn't check user_id
        retrieved = service.get_evaluator_by_id(created.id)

        assert retrieved is not None

    def test_list_evaluators_with_builtin(self, db, test_user):
        """Test listing evaluators includes built-in ones"""
        service = EvaluatorService(db)
        service.seed_builtin_evaluators()

        # Create a custom evaluator
        service.create_evaluator(
            test_user.id,
            EvaluatorCreate(name="Custom", type=EvaluatorType.CONTAINS, category=EvaluatorCategory.OUTPUT)
        )

        evaluators, total = service.list_evaluators(test_user.id, include_builtin=True)

        # Should include both custom and all built-in
        assert total == len(BUILTIN_EVALUATORS) + 1
        assert any(e.is_builtin for e in evaluators)
        assert any(not e.is_builtin for e in evaluators)

    def test_list_evaluators_exclude_builtin(self, db, test_user):
        """Test listing evaluators without built-in ones"""
        service = EvaluatorService(db)
        service.seed_builtin_evaluators()

        # Create custom evaluators
        service.create_evaluator(
            test_user.id,
            EvaluatorCreate(name="Custom 1", type=EvaluatorType.CONTAINS, category=EvaluatorCategory.OUTPUT)
        )
        service.create_evaluator(
            test_user.id,
            EvaluatorCreate(name="Custom 2", type=EvaluatorType.EXACT_MATCH, category=EvaluatorCategory.OUTPUT)
        )

        evaluators, total = service.list_evaluators(test_user.id, include_builtin=False)

        assert total == 2
        assert all(not e.is_builtin for e in evaluators)

    def test_list_evaluators_filter_by_category(self, db, test_user):
        """Test filtering evaluators by category"""
        service = EvaluatorService(db)
        service.seed_builtin_evaluators()

        evaluators, total = service.list_evaluators(
            test_user.id,
            category=EvaluatorCategory.OUTPUT.value
        )

        assert all(e.category == EvaluatorCategory.OUTPUT.value for e in evaluators)

    def test_list_evaluators_filter_by_type(self, db, test_user):
        """Test filtering evaluators by type"""
        service = EvaluatorService(db)
        service.seed_builtin_evaluators()

        evaluators, total = service.list_evaluators(
            test_user.id,
            type_filter=EvaluatorType.EXACT_MATCH.value
        )

        assert all(e.type == EvaluatorType.EXACT_MATCH.value for e in evaluators)

    def test_update_evaluator(self, db, test_user):
        """Test updating a custom evaluator"""
        service = EvaluatorService(db)

        created = service.create_evaluator(
            test_user.id,
            EvaluatorCreate(
                name="Original",
                type=EvaluatorType.CONTAINS,
                category=EvaluatorCategory.OUTPUT,
                config={"case_sensitive": True}
            )
        )

        updated = service.update_evaluator(
            created.id,
            test_user.id,
            EvaluatorUpdate(name="Updated", config={"case_sensitive": False})
        )

        assert updated is not None
        assert updated.name == "Updated"
        assert updated.config["case_sensitive"] is False

    def test_update_evaluator_builtin_fails(self, db, test_user):
        """Test that built-in evaluators cannot be updated"""
        service = EvaluatorService(db)
        service.seed_builtin_evaluators()

        builtin = db.query(Evaluator).filter(Evaluator.is_builtin == True).first()

        updated = service.update_evaluator(
            builtin.id,
            test_user.id,
            EvaluatorUpdate(name="Hacked")
        )

        assert updated is None

        # Verify name unchanged
        db.refresh(builtin)
        assert builtin.name != "Hacked"

    def test_update_evaluator_wrong_user(self, db, test_user, second_test_user):
        """Test that users can't update other users' evaluators"""
        service = EvaluatorService(db)

        created = service.create_evaluator(
            test_user.id,
            EvaluatorCreate(name="Private", type=EvaluatorType.CONTAINS, category=EvaluatorCategory.OUTPUT)
        )

        updated = service.update_evaluator(
            created.id,
            second_test_user.id,
            EvaluatorUpdate(name="Hacked")
        )

        assert updated is None

    def test_delete_evaluator(self, db, test_user):
        """Test deleting a custom evaluator"""
        service = EvaluatorService(db)

        created = service.create_evaluator(
            test_user.id,
            EvaluatorCreate(name="To Delete", type=EvaluatorType.CONTAINS, category=EvaluatorCategory.OUTPUT)
        )

        result = service.delete_evaluator(created.id, test_user.id)

        assert result is True

        # Verify deleted
        retrieved = service.get_evaluator(created.id, test_user.id)
        assert retrieved is None

    def test_delete_evaluator_builtin_fails(self, db, test_user):
        """Test that built-in evaluators cannot be deleted"""
        service = EvaluatorService(db)
        service.seed_builtin_evaluators()

        builtin = db.query(Evaluator).filter(Evaluator.is_builtin == True).first()

        result = service.delete_evaluator(builtin.id, test_user.id)

        assert result is False

        # Verify still exists
        exists = service.get_evaluator(builtin.id, test_user.id)
        assert exists is not None

    def test_delete_evaluator_wrong_user(self, db, test_user, second_test_user):
        """Test that users can't delete other users' evaluators"""
        service = EvaluatorService(db)

        created = service.create_evaluator(
            test_user.id,
            EvaluatorCreate(name="Private", type=EvaluatorType.CONTAINS, category=EvaluatorCategory.OUTPUT)
        )

        result = service.delete_evaluator(created.id, second_test_user.id)

        assert result is False


class TestEvaluatorCloning:
    """Tests for evaluator cloning functionality"""

    def test_clone_builtin_evaluator(self, db, test_user):
        """Test cloning a built-in evaluator"""
        service = EvaluatorService(db)
        service.seed_builtin_evaluators()

        # Get exact match evaluator
        builtin = db.query(Evaluator).filter(
            Evaluator.name == "Exact Match",
            Evaluator.is_builtin == True
        ).first()

        clone = service.clone_evaluator(builtin.id, test_user.id)

        assert clone is not None
        assert clone.id != builtin.id
        assert clone.name == "Exact Match (Copy)"
        assert clone.type == builtin.type
        assert clone.category == builtin.category
        assert clone.config == builtin.config
        assert clone.is_builtin is False
        assert clone.user_id == test_user.id

    def test_clone_with_custom_name(self, db, test_user):
        """Test cloning with a custom name"""
        service = EvaluatorService(db)
        service.seed_builtin_evaluators()

        builtin = db.query(Evaluator).filter(Evaluator.is_builtin == True).first()

        clone = service.clone_evaluator(builtin.id, test_user.id, new_name="My Custom Clone")

        assert clone.name == "My Custom Clone"

    def test_clone_handles_name_collision(self, db, test_user):
        """Test that cloning handles name collisions"""
        service = EvaluatorService(db)
        service.seed_builtin_evaluators()

        builtin = db.query(Evaluator).filter(Evaluator.is_builtin == True).first()

        # Clone first time
        clone1 = service.clone_evaluator(builtin.id, test_user.id)
        assert clone1.name == f"{builtin.name} (Copy)"

        # Clone second time - should add number
        clone2 = service.clone_evaluator(builtin.id, test_user.id)
        assert clone2.name == f"{builtin.name} (Copy) 2"

    def test_clone_custom_evaluator(self, db, test_user):
        """Test cloning a custom evaluator"""
        service = EvaluatorService(db)

        original = service.create_evaluator(
            test_user.id,
            EvaluatorCreate(
                name="Custom Evaluator",
                type=EvaluatorType.REGEX_MATCH,
                category=EvaluatorCategory.OUTPUT,
                config={"pattern": "test.*pattern"}
            )
        )

        clone = service.clone_evaluator(original.id, test_user.id)

        assert clone is not None
        assert clone.config["pattern"] == "test.*pattern"
        assert clone.is_builtin is False

    def test_clone_nonexistent_evaluator(self, db, test_user):
        """Test cloning a non-existent evaluator"""
        service = EvaluatorService(db)

        clone = service.clone_evaluator(99999, test_user.id)

        assert clone is None

    def test_clone_other_users_evaluator(self, db, test_user, second_test_user):
        """Test that users can't clone other users' evaluators"""
        service = EvaluatorService(db)

        original = service.create_evaluator(
            test_user.id,
            EvaluatorCreate(name="Private", type=EvaluatorType.CONTAINS, category=EvaluatorCategory.OUTPUT)
        )

        clone = service.clone_evaluator(original.id, second_test_user.id)

        assert clone is None


class TestEvaluatorBatchOperations:
    """Tests for batch evaluator operations"""

    def test_get_evaluators_by_ids(self, db, test_user):
        """Test getting multiple evaluators by IDs"""
        service = EvaluatorService(db)
        service.seed_builtin_evaluators()

        # Create custom evaluators
        custom1 = service.create_evaluator(
            test_user.id,
            EvaluatorCreate(name="Custom 1", type=EvaluatorType.CONTAINS, category=EvaluatorCategory.OUTPUT)
        )
        custom2 = service.create_evaluator(
            test_user.id,
            EvaluatorCreate(name="Custom 2", type=EvaluatorType.EXACT_MATCH, category=EvaluatorCategory.OUTPUT)
        )

        # Get builtin
        builtin = db.query(Evaluator).filter(Evaluator.is_builtin == True).first()

        # Get multiple by IDs
        evaluators = service.get_evaluators_by_ids(
            [custom1.id, custom2.id, builtin.id],
            test_user.id
        )

        assert len(evaluators) == 3

    def test_get_evaluators_by_ids_filters_inaccessible(self, db, test_user, second_test_user):
        """Test that inaccessible evaluators are filtered out"""
        service = EvaluatorService(db)

        # Create evaluator for different user
        other_user_eval = service.create_evaluator(
            second_test_user.id,
            EvaluatorCreate(name="Other User", type=EvaluatorType.CONTAINS, category=EvaluatorCategory.OUTPUT)
        )

        # Create for test user
        my_eval = service.create_evaluator(
            test_user.id,
            EvaluatorCreate(name="Mine", type=EvaluatorType.CONTAINS, category=EvaluatorCategory.OUTPUT)
        )

        # Try to get both
        evaluators = service.get_evaluators_by_ids(
            [my_eval.id, other_user_eval.id],
            test_user.id
        )

        # Should only get own evaluator
        assert len(evaluators) == 1
        assert evaluators[0].id == my_eval.id
