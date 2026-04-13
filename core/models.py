from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Literal, Optional

RareItemOrigin = Literal["system", "user_seeded"]

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TestStyle(str, Enum):
    SERIOUS = "严肃"
    HUMOROUS = "幽默"
    CUSTOM = "自定义"


class TestMode(str, Enum):
    MULTI_AXIS = "多向轴"
    MULTI_DIM = "多维度"


class NamingMode(str, Enum):
    ABSTRACT = "抽象形容"
    REFERENCE = "角色对标"
    BOTH = "两者兼用"


class RareResultType(str, Enum):
    APPEND = "附加"
    OVERRIDE = "覆盖"


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

class TestConfig(BaseModel):
    theme: str = ""
    mode: TestMode = TestMode.MULTI_AXIS
    style: TestStyle = TestStyle.HUMOROUS
    custom_style: str = ""
    # multi-axis settings
    axis_count: int = 8
    questions_per_axis: int = 4
    normal_result_count: int = 16
    # multi-dimension settings
    dimension_count: int = 6
    questions_per_dimension: int = 4
    archetype_count: int = 12
    naming_mode: NamingMode = NamingMode.ABSTRACT
    # shared limits
    max_rare_results: int = 3
    max_special_questions: int = 4
    max_total_questions: int = 40


# ---------------------------------------------------------------------------
# Multi-Axis models (existing, preserved)
# ---------------------------------------------------------------------------

class Axis(BaseModel):
    id: str
    left_name: str
    right_name: str
    description: str


class NormalResult(BaseModel):
    id: str
    name: str
    description: str
    reference_name: Optional[str] = None
    reference_source: Optional[str] = None
    image_path: Optional[str] = None
    dimension_combo: dict[str, int] = Field(
        default_factory=dict,
        description="axis_id -> direction (+1 or -1)",
    )


class ThresholdCondition(BaseModel):
    axis_id: str
    direction: int
    threshold: float = 0.6


class RareResult(BaseModel):
    id: str
    name: str
    description: str
    reference_name: Optional[str] = None
    reference_source: Optional[str] = None
    image_path: Optional[str] = None
    type: RareResultType = RareResultType.APPEND
    threshold_conditions: list[ThresholdCondition] = Field(default_factory=list)
    special_question_ids: list[str] = Field(default_factory=list)
    min_special_hits: int = 2
    origin: RareItemOrigin = "system"
    user_seed_character: Optional[str] = None
    user_seed_traits: Optional[str] = None


class QuestionOption(BaseModel):
    text: str
    value: int  # -2, -1, 0, 1, 2


class WeakAxisEffect(BaseModel):
    axis_id: str
    coefficient: float = 0.5


class Question(BaseModel):
    id: str
    text: str
    options: list[QuestionOption] = Field(min_length=5, max_length=5)
    primary_axis_id: str
    weak_axes: list[WeakAxisEffect] = Field(default_factory=list)
    is_special: bool = False
    linked_rare_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Multi-Dimension models (new)
# ---------------------------------------------------------------------------

class Dimension(BaseModel):
    id: str
    display_name: str
    low_label: str
    high_label: str
    description: str


class MultiDimOption(BaseModel):
    text: str
    effects: dict[str, int] = Field(
        default_factory=dict,
        description="dimension_id -> effect value (-2 to 2)",
    )


class MultiDimQuestion(BaseModel):
    id: str
    stem: str
    primary_dimension: str
    secondary_dimensions: list[str] = Field(
        default_factory=list, description="0-2 secondary dimensions",
    )
    options: list[MultiDimOption] = Field(min_length=3, max_length=3)
    is_special: bool = False
    special_cluster: Optional[str] = None


class ResultArchetype(BaseModel):
    id: str
    name: str
    description: str
    reference_name: Optional[str] = None
    reference_source: Optional[str] = None
    vector: dict[str, float] = Field(
        default_factory=dict,
        description="dimension_id -> expected normalised score [-1, 1]",
    )
    image_path: Optional[str] = None


class RareTagRule(BaseModel):
    type: str  # "dimension_min" | "dimension_max" | "special_cluster_min_hits"
    dimension: Optional[str] = None
    cluster: Optional[str] = None
    value: float = 0.0


class RareTag(BaseModel):
    id: str
    name: str
    description: str
    reference_name: Optional[str] = None
    reference_source: Optional[str] = None
    image_path: Optional[str] = None
    rules: dict[str, list[RareTagRule]] = Field(
        default_factory=dict,
        description="'all' or 'any' -> list of rules",
    )
    origin: RareItemOrigin = "system"
    user_seed_character: Optional[str] = None
    user_seed_traits: Optional[str] = None


# ---------------------------------------------------------------------------
# Aggregate root
# ---------------------------------------------------------------------------

class TestProject(BaseModel):
    config: TestConfig = Field(default_factory=TestConfig)

    # multi-axis data
    axes: list[Axis] = Field(default_factory=list)
    normal_results: list[NormalResult] = Field(default_factory=list)
    rare_results: list[RareResult] = Field(default_factory=list)
    questions: list[Question] = Field(default_factory=list)

    # multi-dimension data
    dimensions: list[Dimension] = Field(default_factory=list)
    archetypes: list[ResultArchetype] = Field(default_factory=list)
    rare_tags: list[RareTag] = Field(default_factory=list)
    dim_questions: list[MultiDimQuestion] = Field(default_factory=list)

    # metadata
    current_step: int = 1

    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.model_dump_json(indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> TestProject:
        p = Path(path)
        data = json.loads(p.read_text(encoding="utf-8"))
        return cls.model_validate(data)
