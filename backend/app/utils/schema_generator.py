"""
Schema Generator - Auto-generate input schemas from Python function code.

This module parses Python function definitions and generates JSON schemas
compatible with LangChain tools.
"""
import ast
import re
from typing import Any, Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


# Python type hints to JSON schema type mapping
TYPE_MAPPING = {
    "str": "string",
    "string": "string",
    "int": "integer",
    "integer": "integer",
    "float": "number",
    "number": "number",
    "bool": "boolean",
    "boolean": "boolean",
    "list": "array",
    "List": "array",
    "dict": "object",
    "Dict": "object",
    "Any": "string",  # Default to string for Any type
}


def parse_function_signature(code: str) -> Optional[Dict[str, Any]]:
    """
    Parse a Python function definition and extract parameter information.

    Args:
        code: Python code containing a function definition

    Returns:
        Dictionary with function name and parameters, or None if parsing fails
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        logger.warning(f"Failed to parse code: {e}")
        return None

    # Find the function definition
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            func_name = node.name
            params = []

            for arg in node.args.args:
                param_name = arg.arg
                param_type = None

                # Extract type annotation if present
                if arg.annotation:
                    param_type = _get_annotation_string(arg.annotation)

                params.append({
                    "name": param_name,
                    "type": param_type,
                    "required": True,  # Positional args are required
                })

            # Handle default values - mark params with defaults as optional
            defaults = node.args.defaults
            num_defaults = len(defaults)
            if num_defaults > 0:
                # Defaults apply to the last N parameters
                for i, param in enumerate(params[-(num_defaults):]):
                    param["required"] = False
                    # Try to extract default value
                    default_node = defaults[i]
                    param["default"] = _get_default_value(default_node)

            return {
                "function_name": func_name,
                "parameters": params,
                "docstring": ast.get_docstring(node),
            }

    return None


def _get_annotation_string(annotation: ast.expr) -> str:
    """Extract type annotation as a string."""
    if isinstance(annotation, ast.Name):
        return annotation.id
    elif isinstance(annotation, ast.Constant):
        return str(annotation.value)
    elif isinstance(annotation, ast.Subscript):
        # Handle generic types like List[str], Dict[str, int]
        if isinstance(annotation.value, ast.Name):
            return annotation.value.id
    elif isinstance(annotation, ast.Attribute):
        # Handle types like typing.List
        return annotation.attr
    return "string"  # Default to string


def _get_default_value(node: ast.expr) -> Any:
    """Extract default value from AST node."""
    if isinstance(node, ast.Constant):
        return node.value
    elif isinstance(node, ast.Name):
        if node.id == "None":
            return None
        return node.id
    elif isinstance(node, ast.List):
        return []
    elif isinstance(node, ast.Dict):
        return {}
    return None


def generate_input_schema(code: str) -> Optional[Dict[str, Any]]:
    """
    Generate a JSON schema from Python function code.

    Args:
        code: Python code containing a function definition

    Returns:
        JSON schema dictionary, or None if generation fails

    Example:
        code = '''
        def search(query: str, max_results: int = 10):
            \"\"\"Search for items matching the query.\"\"\"
            pass
        '''

        schema = generate_input_schema(code)
        # Returns:
        # {
        #     "type": "object",
        #     "properties": {
        #         "query": {"type": "string", "description": "query parameter"},
        #         "max_results": {"type": "integer", "description": "max_results parameter", "default": 10}
        #     },
        #     "required": ["query"]
        # }
    """
    parsed = parse_function_signature(code)
    if not parsed:
        return None

    properties = {}
    required = []

    for param in parsed["parameters"]:
        param_name = param["name"]
        param_type = param.get("type", "string")

        # Map Python type to JSON schema type
        json_type = TYPE_MAPPING.get(param_type, "string")

        prop = {
            "type": json_type,
            "description": f"{param_name} parameter",
        }

        # Add default value if present
        if "default" in param and param["default"] is not None:
            prop["default"] = param["default"]

        properties[param_name] = prop

        # Add to required list if required
        if param.get("required", True):
            required.append(param_name)

    schema = {
        "type": "object",
        "properties": properties,
    }

    if required:
        schema["required"] = required

    return schema


def extract_function_name(code: str) -> Optional[str]:
    """
    Extract the function name from Python code.

    Args:
        code: Python code containing a function definition

    Returns:
        Function name, or None if not found
    """
    parsed = parse_function_signature(code)
    if parsed:
        return parsed["function_name"]
    return None


def validate_function_code(code: str) -> Tuple[bool, Optional[str]]:
    """
    Validate that the code contains a valid Python function.

    Args:
        code: Python code to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not code or not code.strip():
        return False, "Code is empty"

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"Syntax error: {str(e)}"

    # Check if there's at least one function definition
    has_function = False
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            has_function = True
            break

    if not has_function:
        return False, "No function definition found"

    return True, None


def parse_docstring_params(docstring: str) -> Dict[str, str]:
    """
    Parse parameter descriptions from a docstring.

    Supports common docstring formats:
    - :param name: description
    - Args:
        name: description

    Args:
        docstring: Function docstring

    Returns:
        Dictionary mapping parameter names to descriptions
    """
    if not docstring:
        return {}

    params = {}

    # Match :param name: description
    sphinx_pattern = r':param\s+(\w+):\s*(.+?)(?=:param|:return|:raises|$)'
    for match in re.finditer(sphinx_pattern, docstring, re.DOTALL):
        params[match.group(1)] = match.group(2).strip()

    # Match Google-style Args:
    args_section = re.search(r'Args:\s*\n((?:\s+.+\n?)+)', docstring)
    if args_section:
        args_text = args_section.group(1)
        arg_pattern = r'(\w+)(?:\s*\([^)]+\))?:\s*(.+?)(?=\n\s+\w+(?:\s*\([^)]+\))?:|$)'
        for match in re.finditer(arg_pattern, args_text, re.DOTALL):
            params[match.group(1)] = match.group(2).strip()

    return params


def generate_input_schema_with_descriptions(code: str) -> Optional[Dict[str, Any]]:
    """
    Generate a JSON schema with descriptions from docstrings.

    This is an enhanced version that extracts parameter descriptions
    from the function's docstring.

    Args:
        code: Python code containing a function definition

    Returns:
        JSON schema dictionary with descriptions, or None if generation fails
    """
    parsed = parse_function_signature(code)
    if not parsed:
        return None

    # Parse descriptions from docstring
    param_descriptions = {}
    if parsed.get("docstring"):
        param_descriptions = parse_docstring_params(parsed["docstring"])

    properties = {}
    required = []

    for param in parsed["parameters"]:
        param_name = param["name"]
        param_type = param.get("type", "string")

        # Map Python type to JSON schema type
        json_type = TYPE_MAPPING.get(param_type, "string")

        # Get description from docstring or use default
        description = param_descriptions.get(
            param_name,
            f"{param_name} parameter"
        )

        prop = {
            "type": json_type,
            "description": description,
        }

        # Add default value if present
        if "default" in param and param["default"] is not None:
            prop["default"] = param["default"]

        properties[param_name] = prop

        # Add to required list if required
        if param.get("required", True):
            required.append(param_name)

    schema = {
        "type": "object",
        "properties": properties,
    }

    if required:
        schema["required"] = required

    return schema
