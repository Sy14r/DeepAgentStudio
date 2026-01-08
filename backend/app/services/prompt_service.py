"""
Prompt Service for resolving and rendering prompt templates.

This service handles:
- Loading prompts by ID with version resolution
- Variable substitution in templates
- Usage tracking for analytics
"""
import re
from typing import Dict, Optional, List
from sqlalchemy.orm import Session as DBSession
import logging

from ..models.prompt import Prompt, PromptVersion

logger = logging.getLogger(__name__)


class PromptNotFoundError(Exception):
    """Raised when a prompt or version is not found"""
    pass


class PromptVariableError(Exception):
    """Raised when required template variables are missing"""
    pass


class PromptResolutionResult:
    """Result of prompt resolution containing rendered text and metadata."""
    def __init__(self, rendered: str, version_id: int, prompt_id: int):
        self.rendered = rendered
        self.version_id = version_id
        self.prompt_id = prompt_id


class PromptService:
    """
    Service for resolving prompts and substituting template variables.

    Usage:
        service = PromptService(db)
        result = service.resolve_prompt(
            prompt_id=1,
            variables={"topic": "machine learning", "style": "casual"}
        )
        rendered_text = result.rendered
        version_id = result.version_id  # For session tracking
    """

    def __init__(self, db: DBSession):
        """
        Initialize prompt service.

        Args:
            db: Database session
        """
        self.db = db

    def resolve_prompt(
        self,
        prompt_id: int,
        variables: Optional[Dict[str, str]] = None,
        version_id: Optional[int] = None,
        user_id: Optional[int] = None,
        increment_usage: bool = True
    ) -> PromptResolutionResult:
        """
        Resolve a prompt by ID, substitute variables, and return rendered template.

        Args:
            prompt_id: ID of the prompt to resolve
            variables: Dictionary of variable values to substitute
            version_id: Optional specific version ID (uses current_version if not provided)
            user_id: Optional user ID for access validation
            increment_usage: Whether to increment the usage count

        Returns:
            PromptResolutionResult with rendered text and version_id for tracking

        Raises:
            PromptNotFoundError: If prompt or version not found
            PromptVariableError: If required variables are missing
        """
        # Load prompt
        prompt = self._load_prompt(prompt_id, user_id)

        # Get version
        version = self._get_version(prompt, version_id)

        # Substitute variables
        rendered = self.substitute_variables(version.template, variables or {})

        # Increment usage count
        if increment_usage:
            self.increment_usage_count(version.id)

        return PromptResolutionResult(
            rendered=rendered,
            version_id=version.id,
            prompt_id=prompt.id
        )

    def _load_prompt(self, prompt_id: int, user_id: Optional[int] = None) -> Prompt:
        """
        Load prompt from database with optional user access validation.

        Args:
            prompt_id: ID of the prompt
            user_id: Optional user ID for access check

        Returns:
            Prompt model instance

        Raises:
            PromptNotFoundError: If prompt not found or not accessible
        """
        query = self.db.query(Prompt).filter(
            Prompt.id == prompt_id,
            Prompt.is_active == True
        )

        if user_id is not None:
            query = query.filter(Prompt.user_id == user_id)

        prompt = query.first()

        if not prompt:
            raise PromptNotFoundError(f"Prompt {prompt_id} not found or not accessible")

        return prompt

    def _get_version(
        self,
        prompt: Prompt,
        version_id: Optional[int] = None
    ) -> PromptVersion:
        """
        Get the appropriate prompt version.

        Args:
            prompt: The parent prompt
            version_id: Optional specific version ID

        Returns:
            PromptVersion model instance

        Raises:
            PromptNotFoundError: If version not found
        """
        if version_id:
            # Load specific version
            version = self.db.query(PromptVersion).filter(
                PromptVersion.id == version_id,
                PromptVersion.prompt_id == prompt.id
            ).first()

            if not version:
                raise PromptNotFoundError(
                    f"Version {version_id} not found for prompt {prompt.id}"
                )
            return version

        # Use current version
        if prompt.current_version:
            return prompt.current_version

        # Fallback to latest active version
        version = self.db.query(PromptVersion).filter(
            PromptVersion.prompt_id == prompt.id,
            PromptVersion.is_active == True
        ).order_by(PromptVersion.version_number.desc()).first()

        if not version:
            raise PromptNotFoundError(
                f"No active versions found for prompt {prompt.id}"
            )

        return version

    def substitute_variables(
        self,
        template: str,
        variables: Dict[str, str],
        strict: bool = False
    ) -> str:
        """
        Replace {variable_name} placeholders with provided values.

        Args:
            template: The prompt template string
            variables: Dictionary mapping variable names to values
            strict: If True, raise error for missing variables

        Returns:
            Template with variables substituted

        Raises:
            PromptVariableError: If strict=True and required variables are missing
        """
        # Find all variable placeholders in template
        pattern = r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}'
        required_vars = set(re.findall(pattern, template))

        # Check for missing variables if strict mode
        if strict:
            provided_vars = set(variables.keys())
            missing = required_vars - provided_vars
            if missing:
                raise PromptVariableError(
                    f"Missing required variables: {', '.join(sorted(missing))}"
                )

        # Substitute variables
        result = template
        for var_name, var_value in variables.items():
            placeholder = "{" + var_name + "}"
            result = result.replace(placeholder, str(var_value))

        return result

    def extract_variables(self, template: str) -> List[str]:
        """
        Extract variable names from a template.

        Args:
            template: The prompt template string

        Returns:
            List of unique variable names found in template
        """
        pattern = r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}'
        matches = re.findall(pattern, template)
        return list(dict.fromkeys(matches))  # Preserve order, remove duplicates

    def increment_usage_count(self, version_id: int) -> None:
        """
        Increment the usage count for a prompt version.

        Args:
            version_id: ID of the prompt version
        """
        try:
            self.db.query(PromptVersion).filter(
                PromptVersion.id == version_id
            ).update({PromptVersion.usage_count: PromptVersion.usage_count + 1})
            self.db.commit()
        except Exception as e:
            logger.warning(f"Failed to increment usage count for version {version_id}: {e}")
            self.db.rollback()

    def get_prompt_info(
        self,
        prompt_id: int,
        user_id: Optional[int] = None
    ) -> Dict:
        """
        Get information about a prompt including its variables.

        Args:
            prompt_id: ID of the prompt
            user_id: Optional user ID for access check

        Returns:
            Dictionary with prompt info including name, description, variables
        """
        prompt = self._load_prompt(prompt_id, user_id)
        version = self._get_version(prompt)

        return {
            "id": prompt.id,
            "name": prompt.name,
            "description": prompt.description,
            "use_case": prompt.use_case.value,
            "message_type": version.message_type.value,
            "template": version.template,
            "variables": version.variables or self.extract_variables(version.template),
            "version_id": version.id,
            "version_number": version.version_number,
        }
