from __future__ import annotations

from typing import List, Optional

from pydantic import Field

from src.core.models.schemas import StrictBaseModel


class MissingField(StrictBaseModel):
    field_name: str
    not_applicable: bool = False


class StalenessFlag(StrictBaseModel):
    staleness_type: str
    age_days: float
    hard_stop_triggered: bool = False


class ContradictionRecord(StrictBaseModel):
    unresolved: bool = False


class CorporateActionRisk(StrictBaseModel):
    split_days_ago: Optional[int] = None
    dividend_days_ago: Optional[int] = None
    spinoff_or_merger_days_ago: Optional[int] = None


class DIOOutput(StrictBaseModel):
    staleness_flags: List[StalenessFlag] = Field(default_factory=list)
    missing_hard_stop_fields: List[str] = Field(default_factory=list)
    missing_penalty_critical_fields: List[MissingField] = Field(default_factory=list)
    contradictions: List[ContradictionRecord] = Field(default_factory=list)
    unsourced_numbers_detected: bool = False
    corporate_action_risk: Optional[CorporateActionRisk] = None
    low_source_reliability: bool = False
    integrity_veto_triggered: bool = False


class FXExposureReport(StrictBaseModel):
    holding_currency: Optional[str] = None
    fx_rate_missing: bool = False
    fx_rate_stale: bool = False
    fx_exposure_pct: Optional[float] = None
    hedge_data_missing: bool = False
    fx_hard_stop_triggered: bool = False
