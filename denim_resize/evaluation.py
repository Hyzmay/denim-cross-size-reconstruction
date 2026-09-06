from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal


PhysicalGeometryStatus = Literal["passed", "failed", "not_evaluated"]


@dataclass(frozen=True, slots=True)
class EvaluationStatus:
    """Separate image-proxy acceptance from physical geometry evaluation."""

    proxy_checks: dict[str, bool]
    geometry_evaluated: bool
    physical_geometry_status: PhysicalGeometryStatus
    reason: str

    def __post_init__(self) -> None:
        if not self.proxy_checks:
            raise ValueError("At least one proxy check is required")
        if self.geometry_evaluated and self.physical_geometry_status == "not_evaluated":
            raise ValueError(
                "geometry_evaluated cannot be true with a not_evaluated status"
            )
        if not self.geometry_evaluated and self.physical_geometry_status != "not_evaluated":
            raise ValueError(
                "physical geometry must be not_evaluated without geometry ground truth"
            )

    @property
    def proxy_checks_passed(self) -> bool:
        return all(self.proxy_checks.values())

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["proxy_checks_passed"] = self.proxy_checks_passed
        return payload
