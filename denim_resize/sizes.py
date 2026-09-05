from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class GarmentMeasurements:
    size: str
    waist_cm: float
    hip_cm: float
    knee_cm: float
    outseam_cm: float
    front_rise_cm: float
    back_rise_cm: float

    def to_dict(self) -> dict[str, float | str]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class MerchantSizeProfile:
    profile_id: str
    merchant: str
    item_id: str
    source_url: str
    retrieved_on: str
    units: str
    measurements: dict[str, GarmentMeasurements]

    def pair(
        self, source_size: str, target_size: str
    ) -> tuple[GarmentMeasurements, GarmentMeasurements]:
        try:
            source = self.measurements[source_size]
            target = self.measurements[target_size]
        except KeyError as error:
            available = ", ".join(sorted(self.measurements))
            raise ValueError(
                f"Size {error.args[0]!r} is unavailable in {self.profile_id}; "
                f"available sizes: {available}"
            ) from error
        return source, target


# Merchant-published garment measurements. This is an item-specific chart, not
# a universal Taobao sizing standard.
TAOBAO_612962220220 = MerchantSizeProfile(
    profile_id="taobao_612962220220",
    merchant="胖子de衣柜",
    item_id="612962220220",
    source_url="https://item.taobao.com/item.htm?id=612962220220",
    retrieved_on="2026-09-06",
    units="cm",
    measurements={
        "32": GarmentMeasurements("32", 81.0, 105.0, 44.0, 105.0, 28.0, 40.0),
        "33": GarmentMeasurements("33", 83.5, 107.5, 45.0, 105.0, 28.5, 40.5),
        "34": GarmentMeasurements("34", 86.0, 110.0, 46.0, 106.0, 29.0, 41.0),
        "36": GarmentMeasurements("36", 91.0, 120.0, 48.0, 107.0, 31.0, 43.0),
        "38": GarmentMeasurements("38", 96.0, 125.0, 49.5, 108.0, 32.0, 44.0),
    },
)


SIZE_PROFILES = {TAOBAO_612962220220.profile_id: TAOBAO_612962220220}


def get_size_profile(profile_id: str) -> MerchantSizeProfile:
    try:
        return SIZE_PROFILES[profile_id]
    except KeyError as error:
        available = ", ".join(sorted(SIZE_PROFILES))
        raise ValueError(
            f"Unknown size profile {profile_id!r}; available profiles: {available}"
        ) from error
