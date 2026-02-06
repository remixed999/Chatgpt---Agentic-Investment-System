from __future__ import annotations

from typing import Dict, List

from pydantic import ValidationError

from src.core.validation.errors import ValidationResult
from src.schemas.models import ConfigSnapshot, HoldingInput, PortfolioConfig, PortfolioSnapshot, RunConfig


def validate_or_raise(
    *,
    portfolio_snapshot_data: Dict[str, object],
    portfolio_config_data: Dict[str, object],
    run_config_data: Dict[str, object],
    config_snapshot_data: Dict[str, object],
) -> ValidationResult:
    portfolio_errors: List[str] = []
    holding_errors: Dict[str, List[str]] = {}
    valid_holdings: List[HoldingInput] = []
    portfolio_failed = False

    holdings_data = portfolio_snapshot_data.get("holdings")
    if not isinstance(holdings_data, list):
        portfolio_errors.append("holdings_not_list")
        holdings_data = []
        portfolio_failed = True

    for index, holding_data in enumerate(holdings_data):
        if not isinstance(holding_data, dict):
            holding_errors[f"holding_index_{index}"] = ["holding_not_object"]
            continue
        identity_data = holding_data.get("identity")
        identity_id = None
        if isinstance(identity_data, dict):
            identity_id = identity_data.get("holding_id")
        holding_id = str(identity_id or f"holding_index_{index}")
        try:
            holding = HoldingInput.model_validate(holding_data)
        except ValidationError as exc:
            holding_errors[holding_id] = [err.get("msg", "invalid_holding") for err in exc.errors()]
            continue
        valid_holdings.append(holding)

    try:
        portfolio_snapshot = PortfolioSnapshot.model_validate(
            {
                "portfolio_id": portfolio_snapshot_data.get("portfolio_id"),
                "as_of_date": portfolio_snapshot_data.get("as_of_date"),
                "holdings": valid_holdings,
                "cash_pct": portfolio_snapshot_data.get("cash_pct"),
                "retrieval_timestamp": portfolio_snapshot_data.get("retrieval_timestamp"),
            }
        )
    except ValidationError as exc:
        portfolio_errors.extend(err.get("msg", "invalid_snapshot") for err in exc.errors())
        portfolio_snapshot = None
        portfolio_failed = True

    try:
        portfolio_config = PortfolioConfig.model_validate(portfolio_config_data)
    except ValidationError as exc:
        portfolio_errors.extend(err.get("msg", "invalid_portfolio_config") for err in exc.errors())
        portfolio_config = None
        portfolio_failed = True

    try:
        run_config = RunConfig.model_validate(run_config_data)
    except ValidationError as exc:
        portfolio_errors.extend(err.get("msg", "invalid_run_config") for err in exc.errors())
        run_config = None
        portfolio_failed = True

    try:
        config_snapshot = ConfigSnapshot.model_validate(config_snapshot_data)
    except ValidationError as exc:
        portfolio_errors.extend(err.get("msg", "invalid_config_snapshot") for err in exc.errors())
        config_snapshot = None
        portfolio_failed = True

    portfolio_vetoed = False
    if portfolio_config and not portfolio_config.base_currency:
        portfolio_errors.append("base_currency_missing")
        portfolio_vetoed = True

    for index, holding in enumerate(valid_holdings):
        holding_identity = holding.identity
        holding_id = (
            str(holding_identity.holding_id)
            if holding_identity and holding_identity.holding_id
            else f"holding_index_{index}"
        )
        if (
            holding_identity is None
            or not holding_identity.holding_id
            or not holding_identity.ticker
        ):
            holding_errors.setdefault(holding_id, []).append("holding_identity_missing")

    return ValidationResult(
        portfolio_errors=portfolio_errors,
        holding_errors=holding_errors,
        portfolio_failed=portfolio_failed,
        portfolio_vetoed=portfolio_vetoed,
        portfolio_snapshot=portfolio_snapshot,
        portfolio_config=portfolio_config,
        run_config=run_config,
        config_snapshot=config_snapshot,
        valid_holdings=valid_holdings,
        portfolio_id=portfolio_snapshot.portfolio_id if portfolio_snapshot else None,
    )
