from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple, Union


# DD-01/DD-02: schema contracts only
_ALLOWED_AGENT_STATUSES = {"completed", "failed", "skipped"}
_ALLOWED_RUN_MODES = {"FAST", "DEEP"}


def _require_fields(data: Mapping[str, Any], fields: Iterable[str], context: str) -> None:
    missing = [field for field in fields if field not in data]
    if missing:
        raise ValueError(f"{context} missing required fields: {', '.join(missing)}")


def _ensure_tzaware(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise ValueError(f"{field_name} must be tz-aware UTC datetime")
    return value


def _parse_datetime(value: Any, field_name: str) -> datetime:
    if isinstance(value, datetime):
        return _ensure_tzaware(value, field_name)
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        return _ensure_tzaware(datetime.fromisoformat(normalized), field_name)
    raise ValueError(f"{field_name} must be datetime or ISO string")


def _ensure_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be string")
    return value


def _ensure_float(value: Any, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be float")
    return float(value)


def _ensure_bool(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be bool")
    return value


def _ensure_mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be mapping")
    return value


def _ensure_sequence(value: Any, field_name: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError(f"{field_name} must be sequence")
    return value


def _freeze_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(dict(value))


def _freeze_sequence(value: Sequence[Any]) -> Tuple[Any, ...]:
    return tuple(value)


@dataclass(frozen=True)
class InstrumentIdentity:
    ticker: str
    exchange: str
    currency: str
    country: Optional[str] = None
    isin: Optional[str] = None
    instrument_type: Optional[str] = None
    share_class: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "InstrumentIdentity":
        _require_fields(data, ["ticker", "exchange", "currency"], "InstrumentIdentity")
        return cls(
            ticker=_ensure_str(data["ticker"], "ticker"),
            exchange=_ensure_str(data["exchange"], "exchange"),
            currency=_ensure_str(data["currency"], "currency"),
            country=data.get("country"),
            isin=data.get("isin"),
            instrument_type=data.get("instrument_type"),
            share_class=data.get("share_class"),
        )


@dataclass(frozen=True)
class SourceRef:
    as_of_date: datetime
    retrieval_timestamp: datetime
    origin: Optional[str] = None
    original_timezone: Optional[str] = None
    provider_name: Optional[str] = None
    provider_version: Optional[str] = None
    notes: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SourceRef":
        _require_fields(data, ["as_of_date", "retrieval_timestamp"], "SourceRef")
        return cls(
            as_of_date=_parse_datetime(data["as_of_date"], "as_of_date"),
            retrieval_timestamp=_parse_datetime(
                data["retrieval_timestamp"], "retrieval_timestamp"
            ),
            origin=data.get("origin"),
            original_timezone=data.get("original_timezone"),
            provider_name=data.get("provider_name"),
            provider_version=data.get("provider_version"),
            notes=data.get("notes"),
        )


@dataclass(frozen=True)
class MetricValue:
    value: Optional[Union[float, str, bool]] = None
    unit: Optional[str] = None
    missing_reason: Optional[str] = None
    not_applicable: bool = False
    source_ref: Optional[SourceRef] = None

    def __post_init__(self) -> None:
        if self.value is not None and self.source_ref is None:
            raise ValueError("MetricValue.source_ref required when value is present")
        if (
            self.value is None
            and not self.not_applicable
            and self.missing_reason is None
        ):
            raise ValueError(
                "MetricValue missing_reason required when value is null and not applicable"
            )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MetricValue":
        source_ref = None
        if "source_ref" in data and data["source_ref"] is not None:
            source_ref = SourceRef.from_dict(_ensure_mapping(data["source_ref"], "source_ref"))
        return cls(
            value=data.get("value"),
            unit=data.get("unit"),
            missing_reason=data.get("missing_reason"),
            not_applicable=bool(data.get("not_applicable", False)),
            source_ref=source_ref,
        )


@dataclass(frozen=True)
class PenaltyItem:
    category: str
    reason: str
    amount: float
    source_agent: str

    def __post_init__(self) -> None:
        if self.amount >= 0:
            raise ValueError("PenaltyItem.amount must be negative")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PenaltyItem":
        _require_fields(data, ["category", "reason", "amount", "source_agent"], "PenaltyItem")
        return cls(
            category=_ensure_str(data["category"], "category"),
            reason=_ensure_str(data["reason"], "reason"),
            amount=_ensure_float(data["amount"], "amount"),
            source_agent=_ensure_str(data["source_agent"], "source_agent"),
        )


@dataclass(frozen=True)
class AgentResult:
    agent_name: str
    status: str
    confidence: float
    key_findings: Mapping[str, Any]
    metrics: Tuple[MetricValue, ...]
    suggested_penalties: Tuple[PenaltyItem, ...]
    veto_flags: Tuple[str, ...]
    counter_case: Optional[str] = None
    notes: Optional[str] = None

    def __post_init__(self) -> None:
        if self.status not in _ALLOWED_AGENT_STATUSES:
            raise ValueError("AgentResult.status must be completed, failed, or skipped")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("AgentResult.confidence must be between 0.0 and 1.0")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AgentResult":
        _require_fields(
            data,
            [
                "agent_name",
                "status",
                "confidence",
                "key_findings",
                "metrics",
                "suggested_penalties",
                "veto_flags",
            ],
            "AgentResult",
        )
        metrics = tuple(
            MetricValue.from_dict(_ensure_mapping(item, "MetricValue"))
            for item in _ensure_sequence(data["metrics"], "metrics")
        )
        suggested_penalties = tuple(
            PenaltyItem.from_dict(_ensure_mapping(item, "PenaltyItem"))
            for item in _ensure_sequence(data["suggested_penalties"], "suggested_penalties")
        )
        veto_flags = tuple(
            _ensure_str(item, "veto_flags")
            for item in _ensure_sequence(data["veto_flags"], "veto_flags")
        )
        return cls(
            agent_name=_ensure_str(data["agent_name"], "agent_name"),
            status=_ensure_str(data["status"], "status"),
            confidence=_ensure_float(data["confidence"], "confidence"),
            key_findings=_freeze_mapping(_ensure_mapping(data["key_findings"], "key_findings")),
            metrics=metrics,
            suggested_penalties=suggested_penalties,
            veto_flags=veto_flags,
            counter_case=data.get("counter_case"),
            notes=data.get("notes"),
        )


@dataclass(frozen=True)
class HardStopFieldRegistry:
    identity_fields_all_companies: Tuple[str, ...]
    burn_rate_fields_conditional: Tuple[str, ...]
    portfolio_level_fields: Tuple[str, ...]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "HardStopFieldRegistry":
        _require_fields(
            data,
            ["identity_fields_all_companies", "burn_rate_fields_conditional", "portfolio_level_fields"],
            "HardStopFieldRegistry",
        )
        return cls(
            identity_fields_all_companies=_freeze_sequence(
                _ensure_sequence(data["identity_fields_all_companies"], "identity_fields_all_companies")
            ),
            burn_rate_fields_conditional=_freeze_sequence(
                _ensure_sequence(data["burn_rate_fields_conditional"], "burn_rate_fields_conditional")
            ),
            portfolio_level_fields=_freeze_sequence(
                _ensure_sequence(data["portfolio_level_fields"], "portfolio_level_fields")
            ),
        )


@dataclass(frozen=True)
class PenaltyCriticalFieldRegistry:
    fundamentals: Tuple[str, ...]
    fundamentals_conditional_burn_rate: Tuple[str, ...]
    technicals: Tuple[str, ...]
    liquidity: Tuple[str, ...]
    macro_regime: Tuple[str, ...]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PenaltyCriticalFieldRegistry":
        _require_fields(
            data,
            [
                "fundamentals",
                "fundamentals_conditional_burn_rate",
                "technicals",
                "liquidity",
                "macro_regime",
            ],
            "PenaltyCriticalFieldRegistry",
        )
        return cls(
            fundamentals=_freeze_sequence(_ensure_sequence(data["fundamentals"], "fundamentals")),
            fundamentals_conditional_burn_rate=_freeze_sequence(
                _ensure_sequence(
                    data["fundamentals_conditional_burn_rate"],
                    "fundamentals_conditional_burn_rate",
                )
            ),
            technicals=_freeze_sequence(_ensure_sequence(data["technicals"], "technicals")),
            liquidity=_freeze_sequence(_ensure_sequence(data["liquidity"], "liquidity")),
            macro_regime=_freeze_sequence(_ensure_sequence(data["macro_regime"], "macro_regime")),
        )


@dataclass(frozen=True)
class ConfigSnapshot:
    hard_stop_field_registry: HardStopFieldRegistry
    penalty_critical_field_registry: PenaltyCriticalFieldRegistry
    scoring_rubric_version: str
    agent_prompt_versions: Mapping[str, str]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ConfigSnapshot":
        _require_fields(
            data,
            [
                "hard_stop_field_registry",
                "penalty_critical_field_registry",
                "scoring_rubric_version",
                "agent_prompt_versions",
            ],
            "ConfigSnapshot",
        )
        return cls(
            hard_stop_field_registry=HardStopFieldRegistry.from_dict(
                _ensure_mapping(data["hard_stop_field_registry"], "hard_stop_field_registry")
            ),
            penalty_critical_field_registry=PenaltyCriticalFieldRegistry.from_dict(
                _ensure_mapping(
                    data["penalty_critical_field_registry"], "penalty_critical_field_registry"
                )
            ),
            scoring_rubric_version=_ensure_str(data["scoring_rubric_version"], "scoring_rubric_version"),
            agent_prompt_versions=_freeze_mapping(
                _ensure_mapping(data["agent_prompt_versions"], "agent_prompt_versions")
            ),
        )


@dataclass(frozen=True)
class ConcentrationLimits:
    max_single_name_pct: float
    max_sector_pct: float
    max_theme_pct: Optional[float] = None
    max_fx_exposure_pct: Optional[float] = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ConcentrationLimits":
        _require_fields(data, ["max_single_name_pct", "max_sector_pct"], "ConcentrationLimits")
        return cls(
            max_single_name_pct=_ensure_float(data["max_single_name_pct"], "max_single_name_pct"),
            max_sector_pct=_ensure_float(data["max_sector_pct"], "max_sector_pct"),
            max_theme_pct=data.get("max_theme_pct"),
            max_fx_exposure_pct=data.get("max_fx_exposure_pct"),
        )


@dataclass(frozen=True)
class Holding:
    holding_id: str
    instrument: InstrumentIdentity
    current_weight_pct: float
    current_value_base_currency: Optional[float] = None
    acquisition_date: Optional[datetime] = None
    theme_tags: Optional[Tuple[str, ...]] = None
    compliance_flags: Optional[Tuple[str, ...]] = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Holding":
        _require_fields(
            data,
            ["holding_id", "instrument", "current_weight_pct"],
            "Holding",
        )
        acquisition_date = None
        if data.get("acquisition_date") is not None:
            acquisition_date = _parse_datetime(data["acquisition_date"], "acquisition_date")
        theme_tags = None
        if data.get("theme_tags") is not None:
            theme_tags = _freeze_sequence(_ensure_sequence(data["theme_tags"], "theme_tags"))
        compliance_flags = None
        if data.get("compliance_flags") is not None:
            compliance_flags = _freeze_sequence(
                _ensure_sequence(data["compliance_flags"], "compliance_flags")
            )
        return cls(
            holding_id=_ensure_str(data["holding_id"], "holding_id"),
            instrument=InstrumentIdentity.from_dict(
                _ensure_mapping(data["instrument"], "instrument")
            ),
            current_weight_pct=_ensure_float(data["current_weight_pct"], "current_weight_pct"),
            current_value_base_currency=data.get("current_value_base_currency"),
            acquisition_date=acquisition_date,
            theme_tags=theme_tags,
            compliance_flags=compliance_flags,
        )


@dataclass(frozen=True)
class PortfolioSnapshot:
    snapshot_date: datetime
    holdings: Tuple[Holding, ...]
    cash_pct: float
    total_value_base_currency: Optional[float] = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PortfolioSnapshot":
        _require_fields(data, ["snapshot_date", "holdings", "cash_pct"], "PortfolioSnapshot")
        holdings = tuple(
            Holding.from_dict(_ensure_mapping(item, "Holding"))
            for item in _ensure_sequence(data["holdings"], "holdings")
        )
        return cls(
            snapshot_date=_parse_datetime(data["snapshot_date"], "snapshot_date"),
            holdings=holdings,
            cash_pct=_ensure_float(data["cash_pct"], "cash_pct"),
            total_value_base_currency=data.get("total_value_base_currency"),
        )


@dataclass(frozen=True)
class PortfolioConfig:
    base_currency: str
    risk_tolerance: str
    concentration_limits: ConcentrationLimits
    theme_tags: Optional[Mapping[str, Tuple[str, ...]]] = None
    compliance_flags: Optional[Mapping[str, Tuple[str, ...]]] = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PortfolioConfig":
        _require_fields(
            data,
            ["base_currency", "risk_tolerance", "concentration_limits"],
            "PortfolioConfig",
        )
        theme_tags = None
        if data.get("theme_tags") is not None:
            theme_tags = _freeze_mapping(
                {
                    key: _freeze_sequence(_ensure_sequence(value, "theme_tags"))
                    for key, value in _ensure_mapping(data["theme_tags"], "theme_tags").items()
                }
            )
        compliance_flags = None
        if data.get("compliance_flags") is not None:
            compliance_flags = _freeze_mapping(
                {
                    key: _freeze_sequence(_ensure_sequence(value, "compliance_flags"))
                    for key, value in _ensure_mapping(
                        data["compliance_flags"], "compliance_flags"
                    ).items()
                }
            )
        return cls(
            base_currency=_ensure_str(data["base_currency"], "base_currency"),
            risk_tolerance=_ensure_str(data["risk_tolerance"], "risk_tolerance"),
            concentration_limits=ConcentrationLimits.from_dict(
                _ensure_mapping(data["concentration_limits"], "concentration_limits")
            ),
            theme_tags=theme_tags,
            compliance_flags=compliance_flags,
        )


@dataclass(frozen=True)
class BurnRateClassification:
    is_burn_rate_company: Optional[bool] = None
    not_applicable: Optional[bool] = None
    company_stage: Optional[str] = None
    notes: Optional[str] = None

    def __post_init__(self) -> None:
        if self.is_burn_rate_company and self.not_applicable:
            raise ValueError(
                "BurnRateClassification cannot set is_burn_rate_company and not_applicable"
            )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "BurnRateClassification":
        return cls(
            is_burn_rate_company=data.get("is_burn_rate_company"),
            not_applicable=data.get("not_applicable"),
            company_stage=data.get("company_stage"),
            notes=data.get("notes"),
        )


@dataclass(frozen=True)
class StalenessThresholds:
    financials_penalty_max_age_days: int
    financials_hard_stop_max_age_days: int
    price_volume_penalty_max_age_days: int
    price_volume_hard_stop_max_age_days: int
    company_updates_penalty_max_age_days: int
    macro_regime_penalty_max_age_days: int
    macro_regime_hard_stop_max_age_days: int
    fx_rate_hard_stop_max_age_days: int

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "StalenessThresholds":
        _require_fields(
            data,
            [
                "financials_penalty_max_age_days",
                "financials_hard_stop_max_age_days",
                "price_volume_penalty_max_age_days",
                "price_volume_hard_stop_max_age_days",
                "company_updates_penalty_max_age_days",
                "macro_regime_penalty_max_age_days",
                "macro_regime_hard_stop_max_age_days",
                "fx_rate_hard_stop_max_age_days",
            ],
            "StalenessThresholds",
        )
        return cls(
            financials_penalty_max_age_days=int(data["financials_penalty_max_age_days"]),
            financials_hard_stop_max_age_days=int(data["financials_hard_stop_max_age_days"]),
            price_volume_penalty_max_age_days=int(data["price_volume_penalty_max_age_days"]),
            price_volume_hard_stop_max_age_days=int(data["price_volume_hard_stop_max_age_days"]),
            company_updates_penalty_max_age_days=int(data["company_updates_penalty_max_age_days"]),
            macro_regime_penalty_max_age_days=int(data["macro_regime_penalty_max_age_days"]),
            macro_regime_hard_stop_max_age_days=int(data["macro_regime_hard_stop_max_age_days"]),
            fx_rate_hard_stop_max_age_days=int(data["fx_rate_hard_stop_max_age_days"]),
        )


@dataclass(frozen=True)
class PenaltyCaps:
    total_penalty_cap: float
    category_A_cap: float
    category_B_cap: float
    category_C_cap: float
    category_D_cap: float
    category_E_cap: float
    category_F_cap: float

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PenaltyCaps":
        _require_fields(
            data,
            [
                "total_penalty_cap",
                "category_A_cap",
                "category_B_cap",
                "category_C_cap",
                "category_D_cap",
                "category_E_cap",
                "category_F_cap",
            ],
            "PenaltyCaps",
        )
        return cls(
            total_penalty_cap=_ensure_float(data["total_penalty_cap"], "total_penalty_cap"),
            category_A_cap=_ensure_float(data["category_A_cap"], "category_A_cap"),
            category_B_cap=_ensure_float(data["category_B_cap"], "category_B_cap"),
            category_C_cap=_ensure_float(data["category_C_cap"], "category_C_cap"),
            category_D_cap=_ensure_float(data["category_D_cap"], "category_D_cap"),
            category_E_cap=_ensure_float(data["category_E_cap"], "category_E_cap"),
            category_F_cap=_ensure_float(data["category_F_cap"], "category_F_cap"),
        )


@dataclass(frozen=True)
class RunConfig:
    run_mode: str
    burn_rate_classification: Mapping[str, BurnRateClassification]
    staleness_thresholds: StalenessThresholds
    penalty_caps: PenaltyCaps
    custom_overrides: Optional[Mapping[str, Any]] = None

    def __post_init__(self) -> None:
        if self.run_mode not in _ALLOWED_RUN_MODES:
            raise ValueError("RunConfig.run_mode must be FAST or DEEP")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "RunConfig":
        _require_fields(
            data,
            [
                "run_mode",
                "burn_rate_classification",
                "staleness_thresholds",
                "penalty_caps",
            ],
            "RunConfig",
        )
        burn_rate_classification = {
            holding_id: BurnRateClassification.from_dict(
                _ensure_mapping(value, "BurnRateClassification")
            )
            for holding_id, value in _ensure_mapping(
                data["burn_rate_classification"], "burn_rate_classification"
            ).items()
        }
        custom_overrides = None
        if data.get("custom_overrides") is not None:
            custom_overrides = _freeze_mapping(
                _ensure_mapping(data["custom_overrides"], "custom_overrides")
            )
        return cls(
            run_mode=_ensure_str(data["run_mode"], "run_mode"),
            burn_rate_classification=_freeze_mapping(burn_rate_classification),
            staleness_thresholds=StalenessThresholds.from_dict(
                _ensure_mapping(data["staleness_thresholds"], "staleness_thresholds")
            ),
            penalty_caps=PenaltyCaps.from_dict(
                _ensure_mapping(data["penalty_caps"], "penalty_caps")
            ),
            custom_overrides=custom_overrides,
        )
