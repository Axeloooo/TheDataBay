"""Pydantic schema for dataset preview responses."""

from typing import List

from pydantic import BaseModel, Field


class DatasetPreviewResponse(BaseModel):
    """First rows of a dataset returned before purchase."""

    column_names: List[str] = Field(..., description="Dataset column headers")
    rows: List[List[str]] = Field(..., description="Up to 10 preview rows")
