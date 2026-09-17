"""Native numeric controls for Speicher-Ladelogik."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import NumberEntity, NumberEntityDescription, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import SpeicherLadelogikCoordinator
from .entity import SpeicherLadelogikEntity


@dataclass(frozen=True, kw_only=True)
class SpeicherNumberDescription(NumberEntityDescription):
    control_key: str
    minimum: float
    maximum: float
    step: float


NUMBERS = (
    SpeicherNumberDescription(key="bevorzugte_ladeleistung_venus_a", name="Bevorzugte Ladeleistung Venus A", control_key="bevorzugte_ladeleistung_a_w", minimum=0, maximum=1500, step=50, native_unit_of_measurement=UnitOfPower.WATT),
    SpeicherNumberDescription(key="bevorzugte_ladeleistung_venus_d", name="Bevorzugte Ladeleistung Venus D", control_key="bevorzugte_ladeleistung_d_w", minimum=0, maximum=2500, step=50, native_unit_of_measurement=UnitOfPower.WATT),
    SpeicherNumberDescription(key="bevorzugte_ladeleistung_venus_e", name="Bevorzugte Ladeleistung Venus E", control_key="bevorzugte_ladeleistung_e_w", minimum=0, maximum=2500, step=50, native_unit_of_measurement=UnitOfPower.WATT),
    SpeicherNumberDescription(key="nennkapazitaet_venus_a", name="Nennkapazität Venus A", control_key="nennkapazitaet_a_kwh", minimum=0.1, maximum=30, step=0.01, native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR),
    SpeicherNumberDescription(key="nennkapazitaet_venus_d", name="Nennkapazität Venus D", control_key="nennkapazitaet_d_kwh", minimum=0.1, maximum=30, step=0.01, native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR),
    SpeicherNumberDescription(key="nennkapazitaet_venus_e", name="Nennkapazität Venus E", control_key="nennkapazitaet_e_kwh", minimum=0.1, maximum=30, step=0.01, native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR),
    SpeicherNumberDescription(key="manuell_laden_venus_a", name="Handbetrieb Laden Venus A", control_key="manuell_laden_a_w", minimum=0, maximum=1500, step=50, native_unit_of_measurement=UnitOfPower.WATT),
    SpeicherNumberDescription(key="manuell_entladen_venus_a", name="Handbetrieb Entladen Venus A", control_key="manuell_entladen_a_w", minimum=0, maximum=1500, step=50, native_unit_of_measurement=UnitOfPower.WATT),
    SpeicherNumberDescription(key="manuell_laden_venus_d", name="Handbetrieb Laden Venus D", control_key="manuell_laden_d_w", minimum=0, maximum=2500, step=50, native_unit_of_measurement=UnitOfPower.WATT),
    SpeicherNumberDescription(key="manuell_entladen_venus_d", name="Handbetrieb Entladen Venus D", control_key="manuell_entladen_d_w", minimum=0, maximum=2500, step=50, native_unit_of_measurement=UnitOfPower.WATT),
    SpeicherNumberDescription(key="manuell_laden_venus_e", name="Handbetrieb Laden Venus E", control_key="manuell_laden_e_w", minimum=0, maximum=2500, step=50, native_unit_of_measurement=UnitOfPower.WATT),
    SpeicherNumberDescription(key="manuell_entladen_venus_e", name="Handbetrieb Entladen Venus E", control_key="manuell_entladen_e_w", minimum=0, maximum=2500, step=50, native_unit_of_measurement=UnitOfPower.WATT),
    SpeicherNumberDescription(key="mindestreserve", name="Mindestreserve", control_key="mindestreserve", minimum=0, maximum=20, step=0.1, native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR),
    SpeicherNumberDescription(key="prognose_sicherheit", name="Prognosesicherheit", control_key="prognose_sicherheit", minimum=50, maximum=100, step=1, native_unit_of_measurement=PERCENTAGE),
    SpeicherNumberDescription(key="unplanbare_reserve", name="Unplanbare Reserve", control_key="unplanbare_reserve", minimum=0, maximum=20, step=0.1, native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR),
    SpeicherNumberDescription(key="ladewirkungsgrad", name="Planungswirkungsgrad", control_key="ladewirkungsgrad", minimum=50, maximum=100, step=1, native_unit_of_measurement=PERCENTAGE),
    SpeicherNumberDescription(key="planung_hysterese", name="Planungshysterese", control_key="hysterese", minimum=0.05, maximum=1, step=0.05, native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR),
    SpeicherNumberDescription(key="schwacher_tag", name="Schwacher PV-Tag", control_key="schwacher_tag", minimum=0, maximum=200, step=1, native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR),
    SpeicherNumberDescription(key="mittlerer_tag", name="Mittlerer PV-Tag", control_key="mittlerer_tag", minimum=0, maximum=200, step=1, native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR),
    SpeicherNumberDescription(key="starker_tag", name="Starker PV-Tag", control_key="starker_tag", minimum=0, maximum=200, step=1, native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR),
    SpeicherNumberDescription(key="knappheitsreserve", name="Knappheitsreserve", control_key="knappheitsreserve", minimum=100, maximum=200, step=1, native_unit_of_measurement=PERCENTAGE),
    SpeicherNumberDescription(key="min_effiziente_leistung", name="Minimale effiziente Ladeleistung", control_key="min_effiziente_leistung", minimum=0, maximum=5000, step=50, native_unit_of_measurement=UnitOfPower.WATT),
    SpeicherNumberDescription(key="venus_a_packs", name="Anzahl Packs Venus A", control_key="venus_a_packs", minimum=1, maximum=8, step=1),
    SpeicherNumberDescription(key="venus_d_packs", name="Anzahl Packs Venus D", control_key="venus_d_packs", minimum=1, maximum=8, step=1),
)


def _enabled(description: SpeicherNumberDescription, models: tuple[str, ...]) -> bool:
    """Hide controls belonging to storage models that are not configured."""
    for model in ("A", "D", "E"):
        if f"venus_{model.lower()}" in description.key:
            return model in models
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    coordinator: SpeicherLadelogikCoordinator = entry.runtime_data
    async_add_entities(
        SpeicherControlNumber(coordinator, description)
        for description in NUMBERS
        if _enabled(description, coordinator.enabled_models)
    )


class SpeicherControlNumber(SpeicherLadelogikEntity, NumberEntity):
    _attr_mode = NumberMode.BOX
    entity_description: SpeicherNumberDescription

    def __init__(self, coordinator: SpeicherLadelogikCoordinator, description: SpeicherNumberDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description
        self._attr_native_min_value = description.minimum
        self._attr_native_max_value = description.maximum
        self._attr_native_step = description.step

    @property
    def native_value(self) -> float:
        return float(self.coordinator.control[self.entity_description.control_key])

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_control(self.entity_description.control_key, value)
