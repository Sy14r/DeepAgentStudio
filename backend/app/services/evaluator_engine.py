"""Engine for executing evaluators and computing scores"""

import re
import json
from abc import ABC, abstractmethod
from typing import Any, Optional
from decimal import Decimal
from dataclasses import dataclass

from ..models.evaluation import EvaluatorType, EvaluatorCategory


@dataclass
class EvaluatorInput:
    """Input data for evaluator execution"""
    input: Any  # The original input to the agent
    expected_output: Any  # The expected output
    actual_output: Any  # The agent's actual output
    run_metadata: Optional[dict] = None  # Metadata from the agent run
    context: Optional[Any] = None  # Additional context


@dataclass
class EvaluatorResult:
    """Result from evaluator execution"""
    score: Optional[Decimal]  # 0.0 - 1.0 score
    passed: Optional[bool]  # True/False pass indicator
    feedback: str  # Human-readable feedback
    metadata: Optional[dict] = None  # Additional result metadata
    error: Optional[str] = None  # Error message if evaluation failed


class BaseEvaluator(ABC):
    """Base class for all evaluators"""

    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    def evaluate(self, data: EvaluatorInput) -> EvaluatorResult:
        """Execute the evaluation"""
        pass

    @property
    @abstractmethod
    def category(self) -> EvaluatorCategory:
        """Return the evaluator category"""
        pass


# ===== Output Evaluators =====

class ExactMatchEvaluator(BaseEvaluator):
    """Checks if output exactly matches expected output"""

    @property
    def category(self) -> EvaluatorCategory:
        return EvaluatorCategory.OUTPUT

    def evaluate(self, data: EvaluatorInput) -> EvaluatorResult:
        try:
            actual = self._normalize(data.actual_output)
            expected = self._normalize(data.expected_output)

            passed = actual == expected
            score = Decimal("1.0") if passed else Decimal("0.0")

            if passed:
                feedback = "Output exactly matches expected output"
            else:
                feedback = f"Output does not match. Expected: {expected[:100]}..., Got: {actual[:100]}..."

            return EvaluatorResult(
                score=score,
                passed=passed,
                feedback=feedback,
                metadata={"comparison_type": "exact_match"}
            )
        except Exception as e:
            return EvaluatorResult(
                score=None,
                passed=None,
                feedback="Evaluation failed",
                error=str(e)
            )

    def _normalize(self, value: Any) -> str:
        """Normalize value for comparison"""
        text = str(value) if not isinstance(value, str) else value

        if self.config.get("strip_whitespace", True):
            text = text.strip()

        if not self.config.get("case_sensitive", True):
            text = text.lower()

        return text


class ContainsEvaluator(BaseEvaluator):
    """Checks if output contains the expected output"""

    @property
    def category(self) -> EvaluatorCategory:
        return EvaluatorCategory.OUTPUT

    def evaluate(self, data: EvaluatorInput) -> EvaluatorResult:
        try:
            actual = str(data.actual_output)
            expected = str(data.expected_output)

            if not self.config.get("case_sensitive", False):
                actual = actual.lower()
                expected = expected.lower()

            passed = expected in actual
            score = Decimal("1.0") if passed else Decimal("0.0")

            if passed:
                feedback = "Output contains expected substring"
            else:
                feedback = f"Output does not contain: {expected[:100]}..."

            return EvaluatorResult(
                score=score,
                passed=passed,
                feedback=feedback,
                metadata={"comparison_type": "contains"}
            )
        except Exception as e:
            return EvaluatorResult(
                score=None,
                passed=None,
                feedback="Evaluation failed",
                error=str(e)
            )


class RegexMatchEvaluator(BaseEvaluator):
    """Checks if output matches a regex pattern"""

    @property
    def category(self) -> EvaluatorCategory:
        return EvaluatorCategory.OUTPUT

    def evaluate(self, data: EvaluatorInput) -> EvaluatorResult:
        try:
            actual = str(data.actual_output)

            # Use expected output as pattern if configured
            if self.config.get("use_expected_as_pattern", True):
                pattern = str(data.expected_output)
            else:
                pattern = self.config.get("pattern", "")

            # Build regex flags
            flags = 0
            flag_names = self.config.get("flags", [])
            if "IGNORECASE" in flag_names:
                flags |= re.IGNORECASE
            if "MULTILINE" in flag_names:
                flags |= re.MULTILINE
            if "DOTALL" in flag_names:
                flags |= re.DOTALL

            match = re.search(pattern, actual, flags)
            passed = match is not None
            score = Decimal("1.0") if passed else Decimal("0.0")

            if passed:
                feedback = f"Output matches pattern. Match: {match.group()[:100]}"
            else:
                feedback = f"Output does not match pattern: {pattern[:100]}"

            return EvaluatorResult(
                score=score,
                passed=passed,
                feedback=feedback,
                metadata={
                    "pattern": pattern,
                    "match": match.group() if match else None
                }
            )
        except re.error as e:
            return EvaluatorResult(
                score=None,
                passed=None,
                feedback=f"Invalid regex pattern: {pattern}",
                error=str(e)
            )
        except Exception as e:
            return EvaluatorResult(
                score=None,
                passed=None,
                feedback="Evaluation failed",
                error=str(e)
            )


class JsonMatchEvaluator(BaseEvaluator):
    """Compares JSON structures"""

    @property
    def category(self) -> EvaluatorCategory:
        return EvaluatorCategory.OUTPUT

    def evaluate(self, data: EvaluatorInput) -> EvaluatorResult:
        try:
            # Parse JSON if strings
            if isinstance(data.actual_output, str):
                actual = json.loads(data.actual_output)
            else:
                actual = data.actual_output

            if isinstance(data.expected_output, str):
                expected = json.loads(data.expected_output)
            else:
                expected = data.expected_output

            ignore_order = self.config.get("ignore_order", True)
            subset_match = self.config.get("subset_match", False)
            ignore_extra_keys = self.config.get("ignore_extra_keys", False)

            passed, details = self._compare_json(actual, expected, ignore_order, subset_match, ignore_extra_keys)
            score = Decimal("1.0") if passed else Decimal("0.0")

            if passed:
                feedback = "JSON structures match"
            else:
                feedback = f"JSON mismatch: {details}"

            return EvaluatorResult(
                score=score,
                passed=passed,
                feedback=feedback,
                metadata={"differences": details if not passed else None}
            )
        except json.JSONDecodeError as e:
            return EvaluatorResult(
                score=None,
                passed=None,
                feedback="Invalid JSON",
                error=str(e)
            )
        except Exception as e:
            return EvaluatorResult(
                score=None,
                passed=None,
                feedback="Evaluation failed",
                error=str(e)
            )

    def _compare_json(
        self,
        actual: Any,
        expected: Any,
        ignore_order: bool,
        subset_match: bool,
        ignore_extra_keys: bool
    ) -> tuple[bool, Optional[str]]:
        """Compare two JSON structures recursively"""
        if type(actual) != type(expected):
            return False, f"Type mismatch: {type(actual).__name__} vs {type(expected).__name__}"

        if isinstance(expected, dict):
            if not ignore_extra_keys and set(actual.keys()) != set(expected.keys()):
                extra = set(actual.keys()) - set(expected.keys())
                missing = set(expected.keys()) - set(actual.keys())
                return False, f"Key mismatch. Extra: {extra}, Missing: {missing}"

            for key in expected:
                if key not in actual:
                    return False, f"Missing key: {key}"
                match, detail = self._compare_json(
                    actual[key], expected[key], ignore_order, subset_match, ignore_extra_keys
                )
                if not match:
                    return False, f"At key '{key}': {detail}"

            return True, None

        elif isinstance(expected, list):
            if len(actual) != len(expected) and not subset_match:
                return False, f"Array length mismatch: {len(actual)} vs {len(expected)}"

            if ignore_order:
                # Try to match elements in any order
                unmatched = list(range(len(expected)))
                for act_item in actual:
                    matched = False
                    for i in unmatched:
                        match, _ = self._compare_json(
                            act_item, expected[i], ignore_order, subset_match, ignore_extra_keys
                        )
                        if match:
                            unmatched.remove(i)
                            matched = True
                            break
                    if not matched and not subset_match:
                        return False, f"No match for array element: {act_item}"

                if unmatched and not subset_match:
                    return False, f"Unmatched expected elements at indices: {unmatched}"
                return True, None
            else:
                for i, (act_item, exp_item) in enumerate(zip(actual, expected)):
                    match, detail = self._compare_json(
                        act_item, exp_item, ignore_order, subset_match, ignore_extra_keys
                    )
                    if not match:
                        return False, f"At index {i}: {detail}"
                return True, None

        else:
            if actual == expected:
                return True, None
            else:
                return False, f"Value mismatch: {actual} vs {expected}"


class SemanticSimilarityEvaluator(BaseEvaluator):
    """Uses embeddings to measure semantic similarity (placeholder)"""

    @property
    def category(self) -> EvaluatorCategory:
        return EvaluatorCategory.OUTPUT

    def evaluate(self, data: EvaluatorInput) -> EvaluatorResult:
        # Note: Full implementation would require embedding API calls
        # This is a placeholder that falls back to string similarity
        try:
            threshold = self.config.get("threshold", 0.85)

            # Simple fallback: word overlap similarity
            actual_words = set(str(data.actual_output).lower().split())
            expected_words = set(str(data.expected_output).lower().split())

            if not actual_words or not expected_words:
                return EvaluatorResult(
                    score=Decimal("0.0"),
                    passed=False,
                    feedback="Empty output or expected output",
                    metadata={"method": "word_overlap"}
                )

            intersection = actual_words & expected_words
            union = actual_words | expected_words

            similarity = len(intersection) / len(union) if union else 0
            score = Decimal(str(round(similarity, 4)))
            passed = similarity >= threshold

            return EvaluatorResult(
                score=score,
                passed=passed,
                feedback=f"Semantic similarity: {similarity:.2%} (threshold: {threshold:.0%})",
                metadata={
                    "similarity": similarity,
                    "threshold": threshold,
                    "method": "word_overlap_fallback"
                }
            )
        except Exception as e:
            return EvaluatorResult(
                score=None,
                passed=None,
                feedback="Evaluation failed",
                error=str(e)
            )


class LLMJudgeEvaluator(BaseEvaluator):
    """Uses an LLM to evaluate output (placeholder)"""

    @property
    def category(self) -> EvaluatorCategory:
        return EvaluatorCategory.OUTPUT

    def evaluate(self, data: EvaluatorInput) -> EvaluatorResult:
        # Note: Full implementation requires LLM API integration
        # This is a placeholder that returns a pending result
        try:
            criteria = self.config.get("criteria", "correctness")
            model = self.config.get("model", "gpt-4o-mini")

            return EvaluatorResult(
                score=None,
                passed=None,
                feedback=f"LLM Judge evaluation pending (model: {model}, criteria: {criteria})",
                metadata={
                    "criteria": criteria,
                    "model": model,
                    "status": "pending_llm_call"
                }
            )
        except Exception as e:
            return EvaluatorResult(
                score=None,
                passed=None,
                feedback="Evaluation failed",
                error=str(e)
            )


class CustomCodeEvaluator(BaseEvaluator):
    """Executes custom Python code for evaluation (placeholder)"""

    @property
    def category(self) -> EvaluatorCategory:
        return EvaluatorCategory.OUTPUT

    def evaluate(self, data: EvaluatorInput) -> EvaluatorResult:
        # Note: Custom code execution requires sandboxing
        # This is a placeholder
        return EvaluatorResult(
            score=None,
            passed=None,
            feedback="Custom code evaluation not yet implemented",
            metadata={"status": "not_implemented"}
        )


# ===== Run Metadata Evaluators =====

class TokenEfficiencyEvaluator(BaseEvaluator):
    """Evaluates if token usage is within limits"""

    @property
    def category(self) -> EvaluatorCategory:
        return EvaluatorCategory.RUN_METADATA

    def evaluate(self, data: EvaluatorInput) -> EvaluatorResult:
        try:
            if not data.run_metadata:
                return EvaluatorResult(
                    score=None,
                    passed=None,
                    feedback="No run metadata available",
                    error="Missing run_metadata"
                )

            mode = self.config.get("efficiency_mode", "total")
            max_input = self.config.get("max_input_tokens", 5000)
            max_output = self.config.get("max_output_tokens", 2000)
            max_total = self.config.get("max_total_tokens", 7000)

            token_usage = data.run_metadata.get("token_usage", {})
            input_tokens = token_usage.get("input", 0)
            output_tokens = token_usage.get("output", 0)
            total_tokens = input_tokens + output_tokens

            if mode == "input":
                passed = input_tokens <= max_input
                score = Decimal(str(min(1.0, max_input / max(input_tokens, 1))))
                feedback = f"Input tokens: {input_tokens}/{max_input}"
            elif mode == "output":
                passed = output_tokens <= max_output
                score = Decimal(str(min(1.0, max_output / max(output_tokens, 1))))
                feedback = f"Output tokens: {output_tokens}/{max_output}"
            else:  # total
                passed = total_tokens <= max_total
                score = Decimal(str(min(1.0, max_total / max(total_tokens, 1))))
                feedback = f"Total tokens: {total_tokens}/{max_total}"

            return EvaluatorResult(
                score=score,
                passed=passed,
                feedback=feedback,
                metadata={
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens
                }
            )
        except Exception as e:
            return EvaluatorResult(
                score=None,
                passed=None,
                feedback="Evaluation failed",
                error=str(e)
            )


class LatencyThresholdEvaluator(BaseEvaluator):
    """Checks if response time is within limits"""

    @property
    def category(self) -> EvaluatorCategory:
        return EvaluatorCategory.RUN_METADATA

    def evaluate(self, data: EvaluatorInput) -> EvaluatorResult:
        try:
            if not data.run_metadata:
                return EvaluatorResult(
                    score=None,
                    passed=None,
                    feedback="No run metadata available",
                    error="Missing run_metadata"
                )

            max_ms = self.config.get("max_ms", 30000)
            warning_ms = self.config.get("warning_ms", 15000)

            latency_ms = data.run_metadata.get("latency_ms", 0)

            passed = latency_ms <= max_ms

            if latency_ms <= warning_ms:
                score = Decimal("1.0")
            elif latency_ms <= max_ms:
                # Linear scale from warning to max
                score = Decimal(str(1.0 - (latency_ms - warning_ms) / (max_ms - warning_ms) * 0.5))
            else:
                score = Decimal("0.0")

            return EvaluatorResult(
                score=score,
                passed=passed,
                feedback=f"Latency: {latency_ms}ms (max: {max_ms}ms)",
                metadata={
                    "latency_ms": latency_ms,
                    "max_ms": max_ms,
                    "warning_ms": warning_ms
                }
            )
        except Exception as e:
            return EvaluatorResult(
                score=None,
                passed=None,
                feedback="Evaluation failed",
                error=str(e)
            )


class CostThresholdEvaluator(BaseEvaluator):
    """Checks if execution cost is within budget"""

    @property
    def category(self) -> EvaluatorCategory:
        return EvaluatorCategory.RUN_METADATA

    def evaluate(self, data: EvaluatorInput) -> EvaluatorResult:
        try:
            if not data.run_metadata:
                return EvaluatorResult(
                    score=None,
                    passed=None,
                    feedback="No run metadata available",
                    error="Missing run_metadata"
                )

            max_cost = self.config.get("max_cost_usd", 0.10)
            warning_cost = self.config.get("warning_cost_usd", 0.05)

            cost = float(data.run_metadata.get("cost", 0) or 0)

            passed = cost <= max_cost

            if cost <= warning_cost:
                score = Decimal("1.0")
            elif cost <= max_cost:
                score = Decimal(str(1.0 - (cost - warning_cost) / (max_cost - warning_cost) * 0.5))
            else:
                score = Decimal("0.0")

            return EvaluatorResult(
                score=score,
                passed=passed,
                feedback=f"Cost: ${cost:.4f} (max: ${max_cost:.4f})",
                metadata={"cost": cost, "max_cost": max_cost}
            )
        except Exception as e:
            return EvaluatorResult(
                score=None,
                passed=None,
                feedback="Evaluation failed",
                error=str(e)
            )


class ChainLengthEvaluator(BaseEvaluator):
    """Evaluates if agent completed task in reasonable steps"""

    @property
    def category(self) -> EvaluatorCategory:
        return EvaluatorCategory.RUN_METADATA

    def evaluate(self, data: EvaluatorInput) -> EvaluatorResult:
        try:
            if not data.run_metadata:
                return EvaluatorResult(
                    score=None,
                    passed=None,
                    feedback="No run metadata available",
                    error="Missing run_metadata"
                )

            max_steps = self.config.get("max_steps", 10)
            warning_steps = self.config.get("warning_steps", 5)
            optimal_steps = self.config.get("optimal_steps")

            chain_length = data.run_metadata.get("chain_length", 0)

            passed = chain_length <= max_steps

            if optimal_steps:
                # Score based on closeness to optimal
                deviation = abs(chain_length - optimal_steps)
                score = Decimal(str(max(0, 1.0 - deviation / max_steps)))
            elif chain_length <= warning_steps:
                score = Decimal("1.0")
            elif chain_length <= max_steps:
                score = Decimal(str(1.0 - (chain_length - warning_steps) / (max_steps - warning_steps) * 0.5))
            else:
                score = Decimal("0.0")

            return EvaluatorResult(
                score=score,
                passed=passed,
                feedback=f"Chain length: {chain_length} steps (max: {max_steps})",
                metadata={
                    "chain_length": chain_length,
                    "max_steps": max_steps,
                    "optimal_steps": optimal_steps
                }
            )
        except Exception as e:
            return EvaluatorResult(
                score=None,
                passed=None,
                feedback="Evaluation failed",
                error=str(e)
            )


class ToolCallSuccessRateEvaluator(BaseEvaluator):
    """Evaluates tool call success rate"""

    @property
    def category(self) -> EvaluatorCategory:
        return EvaluatorCategory.RUN_METADATA

    def evaluate(self, data: EvaluatorInput) -> EvaluatorResult:
        try:
            if not data.run_metadata:
                return EvaluatorResult(
                    score=None,
                    passed=None,
                    feedback="No run metadata available",
                    error="Missing run_metadata"
                )

            min_rate = self.config.get("min_success_rate", 0.9)
            ignore_tools = self.config.get("ignore_tools", [])

            tool_calls = data.run_metadata.get("tool_calls", [])

            if not tool_calls:
                return EvaluatorResult(
                    score=Decimal("1.0"),
                    passed=True,
                    feedback="No tool calls made",
                    metadata={"total_calls": 0}
                )

            # Filter out ignored tools
            filtered_calls = [
                tc for tc in tool_calls
                if tc.get("tool_name") not in ignore_tools
            ]

            if not filtered_calls:
                return EvaluatorResult(
                    score=Decimal("1.0"),
                    passed=True,
                    feedback="No applicable tool calls",
                    metadata={"total_calls": 0, "ignored": len(tool_calls)}
                )

            successful = sum(1 for tc in filtered_calls if tc.get("success", False))
            total = len(filtered_calls)
            success_rate = successful / total

            passed = success_rate >= min_rate
            score = Decimal(str(round(success_rate, 4)))

            return EvaluatorResult(
                score=score,
                passed=passed,
                feedback=f"Tool success rate: {success_rate:.1%} ({successful}/{total})",
                metadata={
                    "successful_calls": successful,
                    "total_calls": total,
                    "success_rate": success_rate
                }
            )
        except Exception as e:
            return EvaluatorResult(
                score=None,
                passed=None,
                feedback="Evaluation failed",
                error=str(e)
            )


class ToolSelectionEvaluator(BaseEvaluator):
    """Evaluates if agent used required/forbidden tools"""

    @property
    def category(self) -> EvaluatorCategory:
        return EvaluatorCategory.RUN_METADATA

    def evaluate(self, data: EvaluatorInput) -> EvaluatorResult:
        try:
            if not data.run_metadata:
                return EvaluatorResult(
                    score=None,
                    passed=None,
                    feedback="No run metadata available",
                    error="Missing run_metadata"
                )

            required_tools = set(self.config.get("required_tools", []))
            forbidden_tools = set(self.config.get("forbidden_tools", []))
            preferred_tools = set(self.config.get("preferred_tools", []))
            mode = self.config.get("mode", "required")

            tool_calls = data.run_metadata.get("tool_calls", [])
            used_tools = set(tc.get("tool_name") for tc in tool_calls if tc.get("tool_name"))

            # Check required tools
            missing_required = required_tools - used_tools

            # Check forbidden tools
            used_forbidden = forbidden_tools & used_tools

            # Check preferred tools
            used_preferred = preferred_tools & used_tools if preferred_tools else set()

            if mode == "required":
                passed = len(missing_required) == 0 and len(used_forbidden) == 0
            elif mode == "forbidden":
                passed = len(used_forbidden) == 0
            else:  # preferred
                passed = len(used_preferred) > 0 if preferred_tools else True

            if passed:
                score = Decimal("1.0")
            else:
                # Partial score based on compliance
                total_checks = len(required_tools) + len(forbidden_tools)
                violations = len(missing_required) + len(used_forbidden)
                score = Decimal(str(max(0, 1.0 - violations / max(total_checks, 1))))

            feedback_parts = []
            if missing_required:
                feedback_parts.append(f"Missing required: {list(missing_required)}")
            if used_forbidden:
                feedback_parts.append(f"Used forbidden: {list(used_forbidden)}")
            if passed and not feedback_parts:
                feedback_parts.append("Tool selection compliant")

            return EvaluatorResult(
                score=score,
                passed=passed,
                feedback="; ".join(feedback_parts),
                metadata={
                    "used_tools": list(used_tools),
                    "missing_required": list(missing_required),
                    "used_forbidden": list(used_forbidden),
                    "used_preferred": list(used_preferred)
                }
            )
        except Exception as e:
            return EvaluatorResult(
                score=None,
                passed=None,
                feedback="Evaluation failed",
                error=str(e)
            )


class ErrorRateEvaluator(BaseEvaluator):
    """Evaluates errors and retries during execution"""

    @property
    def category(self) -> EvaluatorCategory:
        return EvaluatorCategory.RUN_METADATA

    def evaluate(self, data: EvaluatorInput) -> EvaluatorResult:
        try:
            if not data.run_metadata:
                return EvaluatorResult(
                    score=None,
                    passed=None,
                    feedback="No run metadata available",
                    error="Missing run_metadata"
                )

            max_errors = self.config.get("max_errors", 2)
            max_retries = self.config.get("max_retries", 3)
            count_warnings = self.config.get("count_warnings", False)

            error_count = data.run_metadata.get("error_count", 0)
            retry_count = data.run_metadata.get("retry_count", 0)
            warning_count = data.run_metadata.get("warning_count", 0) if count_warnings else 0

            total_issues = error_count + (warning_count if count_warnings else 0)

            passed = error_count <= max_errors and retry_count <= max_retries

            if total_issues == 0 and retry_count == 0:
                score = Decimal("1.0")
            else:
                # Score decreases with each error/retry
                error_penalty = min(error_count / max(max_errors, 1), 1) * 0.5
                retry_penalty = min(retry_count / max(max_retries, 1), 1) * 0.3
                warning_penalty = min(warning_count / 5, 1) * 0.2 if count_warnings else 0
                score = Decimal(str(max(0, 1.0 - error_penalty - retry_penalty - warning_penalty)))

            return EvaluatorResult(
                score=score,
                passed=passed,
                feedback=f"Errors: {error_count}/{max_errors}, Retries: {retry_count}/{max_retries}",
                metadata={
                    "error_count": error_count,
                    "retry_count": retry_count,
                    "warning_count": warning_count
                }
            )
        except Exception as e:
            return EvaluatorResult(
                score=None,
                passed=None,
                feedback="Evaluation failed",
                error=str(e)
            )


class SpanCountEvaluator(BaseEvaluator):
    """Evaluates total span count and distribution"""

    @property
    def category(self) -> EvaluatorCategory:
        return EvaluatorCategory.RUN_METADATA

    def evaluate(self, data: EvaluatorInput) -> EvaluatorResult:
        try:
            if not data.run_metadata:
                return EvaluatorResult(
                    score=None,
                    passed=None,
                    feedback="No run metadata available",
                    error="Missing run_metadata"
                )

            max_total = self.config.get("max_total_spans", 50)
            max_llm = self.config.get("max_llm_spans", 10)
            max_tool = self.config.get("max_tool_spans", 20)

            spans = data.run_metadata.get("spans", {})
            total_spans = spans.get("total", 0)
            llm_spans = spans.get("llm", 0)
            tool_spans = spans.get("tool", 0)

            passed = (
                total_spans <= max_total and
                llm_spans <= max_llm and
                tool_spans <= max_tool
            )

            if passed:
                score = Decimal("1.0")
            else:
                # Calculate penalty for each violation
                penalties = []
                if total_spans > max_total:
                    penalties.append((total_spans - max_total) / max_total)
                if llm_spans > max_llm:
                    penalties.append((llm_spans - max_llm) / max_llm)
                if tool_spans > max_tool:
                    penalties.append((tool_spans - max_tool) / max_tool)

                avg_penalty = sum(penalties) / len(penalties) if penalties else 0
                score = Decimal(str(max(0, 1.0 - avg_penalty)))

            return EvaluatorResult(
                score=score,
                passed=passed,
                feedback=f"Spans - Total: {total_spans}/{max_total}, LLM: {llm_spans}/{max_llm}, Tool: {tool_spans}/{max_tool}",
                metadata={
                    "total_spans": total_spans,
                    "llm_spans": llm_spans,
                    "tool_spans": tool_spans
                }
            )
        except Exception as e:
            return EvaluatorResult(
                score=None,
                passed=None,
                feedback="Evaluation failed",
                error=str(e)
            )


class CustomMetadataEvaluator(BaseEvaluator):
    """Evaluates custom metadata fields (placeholder)"""

    @property
    def category(self) -> EvaluatorCategory:
        return EvaluatorCategory.RUN_METADATA

    def evaluate(self, data: EvaluatorInput) -> EvaluatorResult:
        # Note: Custom metadata evaluation requires user-defined logic
        # This is a placeholder
        return EvaluatorResult(
            score=None,
            passed=None,
            feedback="Custom metadata evaluation not yet implemented",
            metadata={"status": "not_implemented"}
        )


# ===== Evaluator Registry =====

EVALUATOR_REGISTRY: dict[str, type[BaseEvaluator]] = {
    # Output evaluators
    EvaluatorType.EXACT_MATCH.value: ExactMatchEvaluator,
    EvaluatorType.CONTAINS.value: ContainsEvaluator,
    EvaluatorType.REGEX_MATCH.value: RegexMatchEvaluator,
    EvaluatorType.JSON_MATCH.value: JsonMatchEvaluator,
    EvaluatorType.SEMANTIC_SIMILARITY.value: SemanticSimilarityEvaluator,
    EvaluatorType.LLM_JUDGE.value: LLMJudgeEvaluator,
    EvaluatorType.CUSTOM_CODE.value: CustomCodeEvaluator,
    # Run metadata evaluators
    EvaluatorType.TOKEN_EFFICIENCY.value: TokenEfficiencyEvaluator,
    EvaluatorType.LATENCY_THRESHOLD.value: LatencyThresholdEvaluator,
    EvaluatorType.COST_THRESHOLD.value: CostThresholdEvaluator,
    EvaluatorType.CHAIN_LENGTH.value: ChainLengthEvaluator,
    EvaluatorType.TOOL_CALL_SUCCESS_RATE.value: ToolCallSuccessRateEvaluator,
    EvaluatorType.TOOL_SELECTION.value: ToolSelectionEvaluator,
    EvaluatorType.ERROR_RATE.value: ErrorRateEvaluator,
    EvaluatorType.SPAN_COUNT.value: SpanCountEvaluator,
    EvaluatorType.CUSTOM_METADATA.value: CustomMetadataEvaluator,
}


def get_evaluator(evaluator_type: str, config: dict) -> BaseEvaluator:
    """Factory function to get an evaluator instance"""
    evaluator_class = EVALUATOR_REGISTRY.get(evaluator_type)
    if not evaluator_class:
        raise ValueError(f"Unknown evaluator type: {evaluator_type}")
    return evaluator_class(config)


def run_evaluator(
    evaluator_type: str,
    config: dict,
    input_data: Any,
    expected_output: Any,
    actual_output: Any,
    run_metadata: Optional[dict] = None,
    context: Optional[Any] = None
) -> EvaluatorResult:
    """Convenience function to run an evaluator"""
    evaluator = get_evaluator(evaluator_type, config)
    data = EvaluatorInput(
        input=input_data,
        expected_output=expected_output,
        actual_output=actual_output,
        run_metadata=run_metadata,
        context=context
    )
    return evaluator.evaluate(data)
