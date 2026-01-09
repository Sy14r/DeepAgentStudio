"""Tests for the evaluator engine - all 17 evaluator implementations"""

import pytest
from decimal import Decimal
from app.services.evaluator_engine import (
    EvaluatorInput,
    EvaluatorResult,
    ExactMatchEvaluator,
    ContainsEvaluator,
    RegexMatchEvaluator,
    JsonMatchEvaluator,
    SemanticSimilarityEvaluator,
    LLMJudgeEvaluator,
    CustomCodeEvaluator,
    TokenEfficiencyEvaluator,
    LatencyThresholdEvaluator,
    CostThresholdEvaluator,
    ChainLengthEvaluator,
    ToolCallSuccessRateEvaluator,
    ToolSelectionEvaluator,
    ErrorRateEvaluator,
    SpanCountEvaluator,
    CustomMetadataEvaluator,
    get_evaluator,
    run_evaluator,
    EVALUATOR_REGISTRY,
)
from app.models.evaluation import EvaluatorType, EvaluatorCategory


class TestEvaluatorInput:
    """Tests for EvaluatorInput data structure"""

    def test_create_evaluator_input(self):
        """Test creating evaluator input"""
        data = EvaluatorInput(
            input="What is 2+2?",
            expected_output="4",
            actual_output="4",
            run_metadata={"token_usage": {"input": 10, "output": 5}},
            context={"additional": "info"}
        )

        assert data.input == "What is 2+2?"
        assert data.expected_output == "4"
        assert data.actual_output == "4"
        assert data.run_metadata is not None
        assert data.context is not None


class TestExactMatchEvaluator:
    """Tests for ExactMatchEvaluator"""

    def test_exact_match_pass(self):
        """Test exact match with matching output"""
        evaluator = ExactMatchEvaluator({"case_sensitive": True, "strip_whitespace": True})
        data = EvaluatorInput(input="test", expected_output="Hello World", actual_output="Hello World")

        result = evaluator.evaluate(data)

        assert result.passed is True
        assert result.score == Decimal("1.0")

    def test_exact_match_fail(self):
        """Test exact match with non-matching output"""
        evaluator = ExactMatchEvaluator({"case_sensitive": True})
        data = EvaluatorInput(input="test", expected_output="Hello", actual_output="Goodbye")

        result = evaluator.evaluate(data)

        assert result.passed is False
        assert result.score == Decimal("0.0")

    def test_exact_match_case_insensitive(self):
        """Test case-insensitive matching"""
        evaluator = ExactMatchEvaluator({"case_sensitive": False})
        data = EvaluatorInput(input="test", expected_output="Hello World", actual_output="hello world")

        result = evaluator.evaluate(data)

        assert result.passed is True

    def test_exact_match_case_sensitive(self):
        """Test case-sensitive matching fails on different case"""
        evaluator = ExactMatchEvaluator({"case_sensitive": True})
        data = EvaluatorInput(input="test", expected_output="Hello", actual_output="hello")

        result = evaluator.evaluate(data)

        assert result.passed is False

    def test_exact_match_strip_whitespace(self):
        """Test whitespace stripping"""
        evaluator = ExactMatchEvaluator({"strip_whitespace": True})
        data = EvaluatorInput(input="test", expected_output="Hello", actual_output="  Hello  ")

        result = evaluator.evaluate(data)

        assert result.passed is True

    def test_exact_match_no_strip_whitespace(self):
        """Test without whitespace stripping"""
        evaluator = ExactMatchEvaluator({"strip_whitespace": False})
        data = EvaluatorInput(input="test", expected_output="Hello", actual_output="  Hello  ")

        result = evaluator.evaluate(data)

        assert result.passed is False


class TestContainsEvaluator:
    """Tests for ContainsEvaluator"""

    def test_contains_pass(self):
        """Test contains with substring present"""
        evaluator = ContainsEvaluator({})
        data = EvaluatorInput(
            input="test",
            expected_output="Paris",
            actual_output="The capital of France is Paris."
        )

        result = evaluator.evaluate(data)

        assert result.passed is True
        assert result.score == Decimal("1.0")

    def test_contains_fail(self):
        """Test contains with substring absent"""
        evaluator = ContainsEvaluator({})
        data = EvaluatorInput(
            input="test",
            expected_output="London",
            actual_output="The capital of France is Paris."
        )

        result = evaluator.evaluate(data)

        assert result.passed is False
        assert result.score == Decimal("0.0")

    def test_contains_case_insensitive(self):
        """Test case-insensitive contains"""
        evaluator = ContainsEvaluator({"case_sensitive": False})
        data = EvaluatorInput(input="test", expected_output="PARIS", actual_output="paris is great")

        result = evaluator.evaluate(data)

        assert result.passed is True

    def test_contains_case_sensitive(self):
        """Test case-sensitive contains"""
        evaluator = ContainsEvaluator({"case_sensitive": True})
        data = EvaluatorInput(input="test", expected_output="PARIS", actual_output="paris is great")

        result = evaluator.evaluate(data)

        assert result.passed is False


class TestRegexMatchEvaluator:
    """Tests for RegexMatchEvaluator"""

    def test_regex_match_pass(self):
        """Test regex match with matching pattern"""
        evaluator = RegexMatchEvaluator({"use_expected_as_pattern": True})
        data = EvaluatorInput(
            input="test",
            expected_output=r"\d{3}-\d{4}",
            actual_output="Call me at 555-1234"
        )

        result = evaluator.evaluate(data)

        assert result.passed is True

    def test_regex_match_fail(self):
        """Test regex match with non-matching pattern"""
        evaluator = RegexMatchEvaluator({"use_expected_as_pattern": True})
        data = EvaluatorInput(
            input="test",
            expected_output=r"\d{3}-\d{4}",
            actual_output="No phone number here"
        )

        result = evaluator.evaluate(data)

        assert result.passed is False

    def test_regex_match_with_flags(self):
        """Test regex match with IGNORECASE flag"""
        evaluator = RegexMatchEvaluator({
            "use_expected_as_pattern": True,
            "flags": ["IGNORECASE"]
        })
        data = EvaluatorInput(input="test", expected_output="hello", actual_output="HELLO world")

        result = evaluator.evaluate(data)

        assert result.passed is True

    def test_regex_invalid_pattern(self):
        """Test regex match with invalid pattern"""
        evaluator = RegexMatchEvaluator({"use_expected_as_pattern": True})
        data = EvaluatorInput(
            input="test",
            expected_output="[invalid",  # Invalid regex
            actual_output="test"
        )

        result = evaluator.evaluate(data)

        assert result.passed is None
        assert result.error is not None


class TestJsonMatchEvaluator:
    """Tests for JsonMatchEvaluator"""

    def test_json_match_pass(self):
        """Test JSON match with identical structures"""
        evaluator = JsonMatchEvaluator({})
        data = EvaluatorInput(
            input="test",
            expected_output='{"name": "John", "age": 30}',
            actual_output='{"name": "John", "age": 30}'
        )

        result = evaluator.evaluate(data)

        assert result.passed is True

    def test_json_match_different_order(self):
        """Test JSON match with different key order"""
        evaluator = JsonMatchEvaluator({"ignore_order": True})
        data = EvaluatorInput(
            input="test",
            expected_output='{"age": 30, "name": "John"}',
            actual_output='{"name": "John", "age": 30}'
        )

        result = evaluator.evaluate(data)

        assert result.passed is True

    def test_json_match_fail_different_values(self):
        """Test JSON match with different values"""
        evaluator = JsonMatchEvaluator({})
        data = EvaluatorInput(
            input="test",
            expected_output='{"name": "John"}',
            actual_output='{"name": "Jane"}'
        )

        result = evaluator.evaluate(data)

        assert result.passed is False

    def test_json_match_extra_keys(self):
        """Test JSON match with extra keys not allowed"""
        evaluator = JsonMatchEvaluator({"ignore_extra_keys": False})
        data = EvaluatorInput(
            input="test",
            expected_output='{"name": "John"}',
            actual_output='{"name": "John", "extra": "key"}'
        )

        result = evaluator.evaluate(data)

        assert result.passed is False

    def test_json_match_ignore_extra_keys(self):
        """Test JSON match with extra keys allowed"""
        evaluator = JsonMatchEvaluator({"ignore_extra_keys": True})
        data = EvaluatorInput(
            input="test",
            expected_output='{"name": "John"}',
            actual_output='{"name": "John", "extra": "key"}'
        )

        result = evaluator.evaluate(data)

        assert result.passed is True

    def test_json_match_array_order_sensitive(self):
        """Test JSON array matching with order"""
        evaluator = JsonMatchEvaluator({"ignore_order": False})
        data = EvaluatorInput(
            input="test",
            expected_output='[1, 2, 3]',
            actual_output='[1, 2, 3]'
        )

        result = evaluator.evaluate(data)

        assert result.passed is True

    def test_json_match_array_order_insensitive(self):
        """Test JSON array matching ignoring order"""
        evaluator = JsonMatchEvaluator({"ignore_order": True})
        data = EvaluatorInput(
            input="test",
            expected_output='[1, 2, 3]',
            actual_output='[3, 1, 2]'
        )

        result = evaluator.evaluate(data)

        assert result.passed is True

    def test_json_match_invalid_json(self):
        """Test JSON match with invalid JSON"""
        evaluator = JsonMatchEvaluator({})
        data = EvaluatorInput(
            input="test",
            expected_output='{"valid": true}',
            actual_output='not json'
        )

        result = evaluator.evaluate(data)

        assert result.passed is None
        assert result.error is not None


class TestSemanticSimilarityEvaluator:
    """Tests for SemanticSimilarityEvaluator (word overlap fallback)"""

    def test_semantic_similarity_identical(self):
        """Test semantic similarity with identical text"""
        evaluator = SemanticSimilarityEvaluator({"threshold": 0.8})
        data = EvaluatorInput(
            input="test",
            expected_output="The quick brown fox",
            actual_output="The quick brown fox"
        )

        result = evaluator.evaluate(data)

        assert result.passed is True
        assert result.score == Decimal("1.0")

    def test_semantic_similarity_similar(self):
        """Test semantic similarity with similar text"""
        evaluator = SemanticSimilarityEvaluator({"threshold": 0.5})
        data = EvaluatorInput(
            input="test",
            expected_output="The quick brown fox jumps",
            actual_output="The fast brown fox leaps"
        )

        result = evaluator.evaluate(data)

        # Should have some overlap (the, brown, fox)
        assert result.score > Decimal("0.0")

    def test_semantic_similarity_different(self):
        """Test semantic similarity with very different text"""
        evaluator = SemanticSimilarityEvaluator({"threshold": 0.8})
        data = EvaluatorInput(
            input="test",
            expected_output="apple banana cherry",
            actual_output="dog cat elephant"
        )

        result = evaluator.evaluate(data)

        assert result.passed is False
        assert result.score == Decimal("0.0")

    def test_semantic_similarity_empty(self):
        """Test semantic similarity with empty output"""
        evaluator = SemanticSimilarityEvaluator({"threshold": 0.5})
        data = EvaluatorInput(
            input="test",
            expected_output="test",
            actual_output=""
        )

        result = evaluator.evaluate(data)

        assert result.passed is False


class TestLLMJudgeEvaluator:
    """Tests for LLMJudgeEvaluator (placeholder)"""

    def test_llm_judge_returns_pending(self):
        """Test that LLM judge returns pending status"""
        evaluator = LLMJudgeEvaluator({
            "model": "gpt-4o",
            "criteria": "correctness"
        })
        data = EvaluatorInput(
            input="test",
            expected_output="expected",
            actual_output="actual"
        )

        result = evaluator.evaluate(data)

        # Placeholder returns pending
        assert result.metadata["status"] == "pending_llm_call"


class TestCustomCodeEvaluator:
    """Tests for CustomCodeEvaluator (placeholder)"""

    def test_custom_code_not_implemented(self):
        """Test that custom code returns not implemented"""
        evaluator = CustomCodeEvaluator({"code": "def evaluate(): pass"})
        data = EvaluatorInput(input="test", expected_output="expected", actual_output="actual")

        result = evaluator.evaluate(data)

        assert result.metadata["status"] == "not_implemented"


class TestTokenEfficiencyEvaluator:
    """Tests for TokenEfficiencyEvaluator"""

    def test_token_efficiency_pass(self):
        """Test token efficiency within limits"""
        evaluator = TokenEfficiencyEvaluator({
            "max_total_tokens": 1000,
            "efficiency_mode": "total"
        })
        data = EvaluatorInput(
            input="test",
            expected_output="expected",
            actual_output="actual",
            run_metadata={"token_usage": {"input": 100, "output": 50}}
        )

        result = evaluator.evaluate(data)

        assert result.passed is True

    def test_token_efficiency_fail(self):
        """Test token efficiency exceeding limits"""
        evaluator = TokenEfficiencyEvaluator({
            "max_total_tokens": 100,
            "efficiency_mode": "total"
        })
        data = EvaluatorInput(
            input="test",
            expected_output="expected",
            actual_output="actual",
            run_metadata={"token_usage": {"input": 100, "output": 100}}
        )

        result = evaluator.evaluate(data)

        assert result.passed is False

    def test_token_efficiency_no_metadata(self):
        """Test token efficiency with no metadata"""
        evaluator = TokenEfficiencyEvaluator({"max_total_tokens": 1000})
        data = EvaluatorInput(input="test", expected_output="expected", actual_output="actual")

        result = evaluator.evaluate(data)

        assert result.passed is None
        assert result.error is not None


class TestLatencyThresholdEvaluator:
    """Tests for LatencyThresholdEvaluator"""

    def test_latency_pass(self):
        """Test latency within threshold"""
        evaluator = LatencyThresholdEvaluator({"max_ms": 5000, "warning_ms": 2000})
        data = EvaluatorInput(
            input="test",
            expected_output="expected",
            actual_output="actual",
            run_metadata={"latency_ms": 1000}
        )

        result = evaluator.evaluate(data)

        assert result.passed is True
        assert result.score == Decimal("1.0")

    def test_latency_fail(self):
        """Test latency exceeding threshold"""
        evaluator = LatencyThresholdEvaluator({"max_ms": 5000})
        data = EvaluatorInput(
            input="test",
            expected_output="expected",
            actual_output="actual",
            run_metadata={"latency_ms": 10000}
        )

        result = evaluator.evaluate(data)

        assert result.passed is False

    def test_latency_warning_zone(self):
        """Test latency in warning zone"""
        evaluator = LatencyThresholdEvaluator({"max_ms": 5000, "warning_ms": 2000})
        data = EvaluatorInput(
            input="test",
            expected_output="expected",
            actual_output="actual",
            run_metadata={"latency_ms": 3500}
        )

        result = evaluator.evaluate(data)

        assert result.passed is True
        # Score should be between 0.5 and 1.0
        assert Decimal("0.5") <= result.score <= Decimal("1.0")


class TestCostThresholdEvaluator:
    """Tests for CostThresholdEvaluator"""

    def test_cost_pass(self):
        """Test cost within threshold"""
        evaluator = CostThresholdEvaluator({"max_cost_usd": 0.10})
        data = EvaluatorInput(
            input="test",
            expected_output="expected",
            actual_output="actual",
            run_metadata={"cost": 0.05}
        )

        result = evaluator.evaluate(data)

        assert result.passed is True

    def test_cost_fail(self):
        """Test cost exceeding threshold"""
        evaluator = CostThresholdEvaluator({"max_cost_usd": 0.10})
        data = EvaluatorInput(
            input="test",
            expected_output="expected",
            actual_output="actual",
            run_metadata={"cost": 0.50}
        )

        result = evaluator.evaluate(data)

        assert result.passed is False


class TestChainLengthEvaluator:
    """Tests for ChainLengthEvaluator"""

    def test_chain_length_pass(self):
        """Test chain length within limits"""
        evaluator = ChainLengthEvaluator({"max_steps": 10, "warning_steps": 5})
        data = EvaluatorInput(
            input="test",
            expected_output="expected",
            actual_output="actual",
            run_metadata={"chain_length": 3}
        )

        result = evaluator.evaluate(data)

        assert result.passed is True
        assert result.score == Decimal("1.0")

    def test_chain_length_fail(self):
        """Test chain length exceeding limits"""
        evaluator = ChainLengthEvaluator({"max_steps": 5})
        data = EvaluatorInput(
            input="test",
            expected_output="expected",
            actual_output="actual",
            run_metadata={"chain_length": 10}
        )

        result = evaluator.evaluate(data)

        assert result.passed is False

    def test_chain_length_optimal(self):
        """Test chain length with optimal target"""
        evaluator = ChainLengthEvaluator({"max_steps": 10, "optimal_steps": 3})
        data = EvaluatorInput(
            input="test",
            expected_output="expected",
            actual_output="actual",
            run_metadata={"chain_length": 3}
        )

        result = evaluator.evaluate(data)

        assert result.passed is True
        assert result.score == Decimal("1.0")


class TestToolCallSuccessRateEvaluator:
    """Tests for ToolCallSuccessRateEvaluator"""

    def test_tool_success_rate_pass(self):
        """Test high tool success rate"""
        evaluator = ToolCallSuccessRateEvaluator({"min_success_rate": 0.8})
        data = EvaluatorInput(
            input="test",
            expected_output="expected",
            actual_output="actual",
            run_metadata={
                "tool_calls": [
                    {"tool_name": "search", "success": True},
                    {"tool_name": "fetch", "success": True},
                    {"tool_name": "parse", "success": True},
                ]
            }
        )

        result = evaluator.evaluate(data)

        assert result.passed is True
        assert result.score == Decimal("1.0")

    def test_tool_success_rate_fail(self):
        """Test low tool success rate"""
        evaluator = ToolCallSuccessRateEvaluator({"min_success_rate": 0.8})
        data = EvaluatorInput(
            input="test",
            expected_output="expected",
            actual_output="actual",
            run_metadata={
                "tool_calls": [
                    {"tool_name": "search", "success": True},
                    {"tool_name": "fetch", "success": False},
                    {"tool_name": "parse", "success": False},
                ]
            }
        )

        result = evaluator.evaluate(data)

        assert result.passed is False

    def test_tool_success_rate_no_calls(self):
        """Test with no tool calls"""
        evaluator = ToolCallSuccessRateEvaluator({"min_success_rate": 0.8})
        data = EvaluatorInput(
            input="test",
            expected_output="expected",
            actual_output="actual",
            run_metadata={"tool_calls": []}
        )

        result = evaluator.evaluate(data)

        assert result.passed is True

    def test_tool_success_rate_ignore_tools(self):
        """Test ignoring specific tools"""
        evaluator = ToolCallSuccessRateEvaluator({
            "min_success_rate": 0.9,
            "ignore_tools": ["flaky_tool"]
        })
        data = EvaluatorInput(
            input="test",
            expected_output="expected",
            actual_output="actual",
            run_metadata={
                "tool_calls": [
                    {"tool_name": "search", "success": True},
                    {"tool_name": "flaky_tool", "success": False},  # Ignored
                ]
            }
        )

        result = evaluator.evaluate(data)

        assert result.passed is True


class TestToolSelectionEvaluator:
    """Tests for ToolSelectionEvaluator"""

    def test_tool_selection_required_pass(self):
        """Test required tools were used"""
        evaluator = ToolSelectionEvaluator({
            "required_tools": ["search", "parse"],
            "mode": "required"
        })
        data = EvaluatorInput(
            input="test",
            expected_output="expected",
            actual_output="actual",
            run_metadata={
                "tool_calls": [
                    {"tool_name": "search"},
                    {"tool_name": "parse"},
                ]
            }
        )

        result = evaluator.evaluate(data)

        assert result.passed is True

    def test_tool_selection_required_fail(self):
        """Test required tools missing"""
        evaluator = ToolSelectionEvaluator({
            "required_tools": ["search", "parse"],
            "mode": "required"
        })
        data = EvaluatorInput(
            input="test",
            expected_output="expected",
            actual_output="actual",
            run_metadata={
                "tool_calls": [
                    {"tool_name": "search"},
                    # parse missing
                ]
            }
        )

        result = evaluator.evaluate(data)

        assert result.passed is False

    def test_tool_selection_forbidden_pass(self):
        """Test forbidden tools not used"""
        evaluator = ToolSelectionEvaluator({
            "forbidden_tools": ["dangerous_tool"],
            "mode": "forbidden"
        })
        data = EvaluatorInput(
            input="test",
            expected_output="expected",
            actual_output="actual",
            run_metadata={
                "tool_calls": [
                    {"tool_name": "safe_tool"},
                ]
            }
        )

        result = evaluator.evaluate(data)

        assert result.passed is True

    def test_tool_selection_forbidden_fail(self):
        """Test forbidden tools used"""
        evaluator = ToolSelectionEvaluator({
            "forbidden_tools": ["dangerous_tool"],
            "mode": "forbidden"
        })
        data = EvaluatorInput(
            input="test",
            expected_output="expected",
            actual_output="actual",
            run_metadata={
                "tool_calls": [
                    {"tool_name": "dangerous_tool"},
                ]
            }
        )

        result = evaluator.evaluate(data)

        assert result.passed is False


class TestErrorRateEvaluator:
    """Tests for ErrorRateEvaluator"""

    def test_error_rate_pass(self):
        """Test error rate within limits"""
        evaluator = ErrorRateEvaluator({"max_errors": 2, "max_retries": 3})
        data = EvaluatorInput(
            input="test",
            expected_output="expected",
            actual_output="actual",
            run_metadata={"error_count": 1, "retry_count": 1}
        )

        result = evaluator.evaluate(data)

        assert result.passed is True

    def test_error_rate_fail_errors(self):
        """Test too many errors"""
        evaluator = ErrorRateEvaluator({"max_errors": 2})
        data = EvaluatorInput(
            input="test",
            expected_output="expected",
            actual_output="actual",
            run_metadata={"error_count": 5, "retry_count": 0}
        )

        result = evaluator.evaluate(data)

        assert result.passed is False

    def test_error_rate_fail_retries(self):
        """Test too many retries"""
        evaluator = ErrorRateEvaluator({"max_retries": 2})
        data = EvaluatorInput(
            input="test",
            expected_output="expected",
            actual_output="actual",
            run_metadata={"error_count": 0, "retry_count": 5}
        )

        result = evaluator.evaluate(data)

        assert result.passed is False

    def test_error_rate_no_errors(self):
        """Test with no errors"""
        evaluator = ErrorRateEvaluator({})
        data = EvaluatorInput(
            input="test",
            expected_output="expected",
            actual_output="actual",
            run_metadata={"error_count": 0, "retry_count": 0}
        )

        result = evaluator.evaluate(data)

        assert result.passed is True
        assert result.score == Decimal("1.0")


class TestSpanCountEvaluator:
    """Tests for SpanCountEvaluator"""

    def test_span_count_pass(self):
        """Test span count within limits"""
        evaluator = SpanCountEvaluator({
            "max_total_spans": 50,
            "max_llm_spans": 10,
            "max_tool_spans": 20
        })
        data = EvaluatorInput(
            input="test",
            expected_output="expected",
            actual_output="actual",
            run_metadata={
                "spans": {"total": 15, "llm": 3, "tool": 5}
            }
        )

        result = evaluator.evaluate(data)

        assert result.passed is True

    def test_span_count_fail(self):
        """Test span count exceeding limits"""
        evaluator = SpanCountEvaluator({
            "max_total_spans": 10,
            "max_llm_spans": 5,
            "max_tool_spans": 5
        })
        data = EvaluatorInput(
            input="test",
            expected_output="expected",
            actual_output="actual",
            run_metadata={
                "spans": {"total": 50, "llm": 10, "tool": 30}
            }
        )

        result = evaluator.evaluate(data)

        assert result.passed is False


class TestCustomMetadataEvaluator:
    """Tests for CustomMetadataEvaluator (placeholder)"""

    def test_custom_metadata_not_implemented(self):
        """Test that custom metadata returns not implemented"""
        evaluator = CustomMetadataEvaluator({})
        data = EvaluatorInput(input="test", expected_output="expected", actual_output="actual")

        result = evaluator.evaluate(data)

        assert result.metadata["status"] == "not_implemented"


class TestEvaluatorRegistry:
    """Tests for evaluator registry and factory functions"""

    def test_registry_contains_all_types(self):
        """Test that registry contains all evaluator types"""
        for eval_type in EvaluatorType:
            assert eval_type.value in EVALUATOR_REGISTRY

    def test_get_evaluator(self):
        """Test getting evaluator by type"""
        evaluator = get_evaluator(EvaluatorType.EXACT_MATCH.value, {"case_sensitive": True})

        assert isinstance(evaluator, ExactMatchEvaluator)

    def test_get_evaluator_unknown_type(self):
        """Test getting unknown evaluator type raises error"""
        with pytest.raises(ValueError, match="Unknown evaluator type"):
            get_evaluator("nonexistent_type", {})

    def test_run_evaluator(self):
        """Test convenience run_evaluator function"""
        result = run_evaluator(
            evaluator_type=EvaluatorType.EXACT_MATCH.value,
            config={"case_sensitive": True},
            input_data="What is 2+2?",
            expected_output="4",
            actual_output="4"
        )

        assert result.passed is True
        assert result.score == Decimal("1.0")

    def test_run_evaluator_with_metadata(self):
        """Test run_evaluator with run metadata"""
        result = run_evaluator(
            evaluator_type=EvaluatorType.TOKEN_EFFICIENCY.value,
            config={"max_total_tokens": 1000},
            input_data="test",
            expected_output="expected",
            actual_output="actual",
            run_metadata={"token_usage": {"input": 100, "output": 50}}
        )

        assert result.passed is True


class TestEvaluatorCategories:
    """Tests verifying evaluator categories are correct"""

    def test_output_evaluators_have_correct_category(self):
        """Test output evaluators return OUTPUT category"""
        output_types = [
            EvaluatorType.EXACT_MATCH,
            EvaluatorType.CONTAINS,
            EvaluatorType.REGEX_MATCH,
            EvaluatorType.JSON_MATCH,
            EvaluatorType.SEMANTIC_SIMILARITY,
            EvaluatorType.LLM_JUDGE,
            EvaluatorType.CUSTOM_CODE,
        ]

        for eval_type in output_types:
            evaluator = get_evaluator(eval_type.value, {})
            assert evaluator.category == EvaluatorCategory.OUTPUT

    def test_run_metadata_evaluators_have_correct_category(self):
        """Test run metadata evaluators return RUN_METADATA category"""
        run_metadata_types = [
            EvaluatorType.TOKEN_EFFICIENCY,
            EvaluatorType.LATENCY_THRESHOLD,
            EvaluatorType.COST_THRESHOLD,
            EvaluatorType.CHAIN_LENGTH,
            EvaluatorType.TOOL_CALL_SUCCESS_RATE,
            EvaluatorType.TOOL_SELECTION,
            EvaluatorType.ERROR_RATE,
            EvaluatorType.SPAN_COUNT,
            EvaluatorType.CUSTOM_METADATA,
        ]

        for eval_type in run_metadata_types:
            evaluator = get_evaluator(eval_type.value, {})
            assert evaluator.category == EvaluatorCategory.RUN_METADATA
