"""
Prompt management API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import re

from ...database import get_db
from ...models.user import User
from ...models.prompt import Prompt, PromptVersion
from ...schemas.prompt import (
    PromptCreate,
    PromptUpdate,
    PromptResponse,
    PromptDetailResponse,
    PromptListResponse,
    PromptVersionResponse,
    PromptVersionCreate,
    PromptVersionUpdate,
    PromptRollbackRequest,
    PromptPreviewRequest,
    PromptPreviewResponse,
    PromptUseCase,
)
from ..deps import get_current_user

router = APIRouter()


def extract_variables(template: str) -> List[str]:
    """
    Extract variable names from a template string.

    Looks for {variable_name} patterns and returns unique variable names.
    """
    # Find all {variable} patterns
    pattern = r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}'
    variables = re.findall(pattern, template)
    # Return unique variables while preserving order
    seen = set()
    unique_vars = []
    for var in variables:
        if var not in seen:
            seen.add(var)
            unique_vars.append(var)
    return unique_vars


def _build_prompt_detail_response(prompt: Prompt, db: Session) -> PromptDetailResponse:
    """Helper function to build PromptDetailResponse with current version"""
    current_version = None
    if prompt.current_version_id:
        version = db.query(PromptVersion).filter(
            PromptVersion.id == prompt.current_version_id
        ).first()
        if version:
            current_version = PromptVersionResponse.model_validate(version)

    return PromptDetailResponse(
        id=prompt.id,
        user_id=prompt.user_id,
        name=prompt.name,
        description=prompt.description,
        use_case=prompt.use_case,
        tags=prompt.tags,
        is_active=prompt.is_active,
        current_version_id=prompt.current_version_id,
        created_at=prompt.created_at,
        updated_at=prompt.updated_at,
        current_version=current_version
    )


@router.post("", response_model=PromptDetailResponse, status_code=status.HTTP_201_CREATED)
def create_prompt(
    prompt_data: PromptCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new prompt with initial version.

    Creates both a Prompt record and its first PromptVersion.
    """
    # Create prompt
    prompt = Prompt(
        user_id=current_user.id,
        name=prompt_data.name,
        description=prompt_data.description,
        use_case=prompt_data.use_case,
        tags=prompt_data.tags
    )
    db.add(prompt)
    db.flush()  # Flush to get prompt.id

    # Extract variables from template
    variables = extract_variables(prompt_data.version.template)

    # Create first version
    version = PromptVersion(
        prompt_id=prompt.id,
        version_number=1,
        template=prompt_data.version.template,
        variables=variables,
        message_type=prompt_data.version.message_type,
        is_active=prompt_data.version.is_active,
        created_by=current_user.id
    )
    db.add(version)
    db.flush()

    # Set current version
    prompt.current_version_id = version.id
    db.commit()
    db.refresh(prompt)
    db.refresh(version)

    # Build response
    return _build_prompt_detail_response(prompt, db)


@router.get("", response_model=PromptListResponse)
def list_prompts(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records to return"),
    use_case: Optional[PromptUseCase] = Query(None, description="Filter by use case"),
    active_only: bool = Query(True, description="Only return active prompts"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all prompts for the current user with pagination and filters.
    """
    query = db.query(Prompt).filter(Prompt.user_id == current_user.id)

    if active_only:
        query = query.filter(Prompt.is_active == True)

    if use_case:
        query = query.filter(Prompt.use_case == use_case)

    total = query.count()
    prompts = query.order_by(Prompt.updated_at.desc()).offset(skip).limit(limit).all()

    return PromptListResponse(
        prompts=[PromptResponse.model_validate(prompt) for prompt in prompts],
        total=total,
        page=skip // limit + 1,
        page_size=limit
    )


@router.get("/{prompt_id}", response_model=PromptDetailResponse)
def get_prompt(
    prompt_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get prompt details including current version.
    """
    prompt = db.query(Prompt).filter(
        Prompt.id == prompt_id,
        Prompt.user_id == current_user.id
    ).first()

    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found"
        )

    return _build_prompt_detail_response(prompt, db)


@router.put("/{prompt_id}", response_model=PromptDetailResponse)
def update_prompt(
    prompt_id: int,
    prompt_data: PromptUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update prompt metadata (not the template).

    To update the template, create a new version instead.
    """
    prompt = db.query(Prompt).filter(
        Prompt.id == prompt_id,
        Prompt.user_id == current_user.id
    ).first()

    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found"
        )

    # Update metadata fields
    update_data = prompt_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(prompt, field, value)

    db.commit()
    db.refresh(prompt)

    return _build_prompt_detail_response(prompt, db)


@router.delete("/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_prompt(
    prompt_id: int,
    hard_delete: bool = Query(False, description="Permanently delete prompt"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a prompt (soft delete by default).

    Set hard_delete=true to permanently delete.
    """
    prompt = db.query(Prompt).filter(
        Prompt.id == prompt_id,
        Prompt.user_id == current_user.id
    ).first()

    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found"
        )

    if hard_delete:
        db.delete(prompt)
    else:
        prompt.is_active = False

    db.commit()
    return None


# Version Management Endpoints

@router.get("/{prompt_id}/versions", response_model=List[PromptVersionResponse])
def list_prompt_versions(
    prompt_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get version history for a prompt.
    """
    # Verify prompt ownership
    prompt = db.query(Prompt).filter(
        Prompt.id == prompt_id,
        Prompt.user_id == current_user.id
    ).first()

    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found"
        )

    versions = db.query(PromptVersion).filter(
        PromptVersion.prompt_id == prompt_id
    ).order_by(PromptVersion.version_number.desc()).all()

    return [PromptVersionResponse.model_validate(version) for version in versions]


@router.post("/{prompt_id}/versions", response_model=PromptDetailResponse, status_code=status.HTTP_201_CREATED)
def create_prompt_version(
    prompt_id: int,
    version_data: PromptVersionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new version of a prompt.

    Automatically sets it as the current version.
    """
    prompt = db.query(Prompt).filter(
        Prompt.id == prompt_id,
        Prompt.user_id == current_user.id
    ).first()

    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found"
        )

    # Get current max version number
    max_version = db.query(PromptVersion.version_number).filter(
        PromptVersion.prompt_id == prompt_id
    ).order_by(PromptVersion.version_number.desc()).first()

    next_version_number = (max_version[0] + 1) if max_version else 1

    # Extract variables from template
    variables = extract_variables(version_data.template)

    # Create new version
    new_version = PromptVersion(
        prompt_id=prompt.id,
        version_number=next_version_number,
        template=version_data.template,
        variables=variables,
        message_type=version_data.message_type,
        is_active=version_data.is_active,
        created_by=current_user.id
    )
    db.add(new_version)
    db.flush()

    # Update current version
    prompt.current_version_id = new_version.id
    db.commit()
    db.refresh(prompt)

    return _build_prompt_detail_response(prompt, db)


@router.patch("/{prompt_id}/versions/{version_id}", response_model=PromptVersionResponse)
def update_prompt_version(
    prompt_id: int,
    version_id: int,
    version_data: PromptVersionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a prompt version (currently only is_active flag for A/B testing).
    """
    # Verify prompt ownership
    prompt = db.query(Prompt).filter(
        Prompt.id == prompt_id,
        Prompt.user_id == current_user.id
    ).first()

    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found"
        )

    # Get version
    version = db.query(PromptVersion).filter(
        PromptVersion.id == version_id,
        PromptVersion.prompt_id == prompt_id
    ).first()

    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found"
        )

    # Update fields
    if version_data.is_active is not None:
        version.is_active = version_data.is_active

    db.commit()
    db.refresh(version)

    return PromptVersionResponse.model_validate(version)


@router.post("/{prompt_id}/rollback", response_model=PromptDetailResponse)
def rollback_prompt(
    prompt_id: int,
    rollback_data: PromptRollbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Rollback prompt to a previous version.

    Updates the current_version_id to point to the specified version.
    """
    prompt = db.query(Prompt).filter(
        Prompt.id == prompt_id,
        Prompt.user_id == current_user.id
    ).first()

    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found"
        )

    # Verify version exists and belongs to this prompt
    version = db.query(PromptVersion).filter(
        PromptVersion.id == rollback_data.version_id,
        PromptVersion.prompt_id == prompt_id
    ).first()

    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found for this prompt"
        )

    # Update current version
    prompt.current_version_id = version.id
    db.commit()
    db.refresh(prompt)

    return _build_prompt_detail_response(prompt, db)


@router.post("/preview", response_model=PromptPreviewResponse)
def preview_prompt(
    preview_data: PromptPreviewRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Preview a prompt template with sample variable values.

    Useful for testing templates before creating/updating.
    """
    # Extract variables from template
    variables_found = extract_variables(preview_data.template)

    # Find missing variables
    provided_vars = set(preview_data.variables.keys())
    required_vars = set(variables_found)
    variables_missing = list(required_vars - provided_vars)

    # Render template
    rendered = preview_data.template
    for var, value in preview_data.variables.items():
        rendered = rendered.replace(f"{{{var}}}", str(value))

    return PromptPreviewResponse(
        rendered=rendered,
        variables_found=variables_found,
        variables_missing=variables_missing
    )


# Analytics Endpoints

@router.get("/{prompt_id}/analytics")
def get_prompt_analytics(
    prompt_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get usage analytics for a prompt.

    Returns:
    - Total usage count across all versions
    - Usage by version
    - Version history with usage counts
    """
    # Verify prompt ownership
    prompt = db.query(Prompt).filter(
        Prompt.id == prompt_id,
        Prompt.user_id == current_user.id
    ).first()

    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found"
        )

    # Get all versions with usage counts
    versions = db.query(PromptVersion).filter(
        PromptVersion.prompt_id == prompt_id
    ).order_by(PromptVersion.version_number.desc()).all()

    # Calculate totals
    total_usage = sum(v.usage_count for v in versions)

    # Build version usage breakdown
    version_usage = [
        {
            "version_id": v.id,
            "version_number": v.version_number,
            "usage_count": v.usage_count,
            "is_active": v.is_active,
            "is_current": v.id == prompt.current_version_id,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        }
        for v in versions
    ]

    return {
        "prompt_id": prompt_id,
        "prompt_name": prompt.name,
        "total_usage_count": total_usage,
        "total_versions": len(versions),
        "current_version_id": prompt.current_version_id,
        "version_usage": version_usage,
    }
