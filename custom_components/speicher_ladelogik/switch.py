"""Native switches for Speicher-Ladelogik."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import SpeicherLadelogikCoordinator
from .entity import SpeicherLadelogikEntity


@dataclass(frozen=True, kw_only=True)
class SpeicherSwitchDescription(SwitchEntityDescription):
    control_key: str


SWITCHES = (
    SpeicherSwitchDescription(key="kalibrierung_parallel", name="Zwei Kalibrierungen gleichzeitig", icon="mdi:battery-sync", control_key="kalibrierung_parallel"),
    SpeicherSwitchDescription(key="mittagsspitzen", name="Mittagsspitzen reduzieren", icon="mdi:chart-bell-curve", control_key="mittagsspitzen"),
    SpeicherSwitchDescription(key="handbetrieb_venus_a", name="Handbetrieb Venus A", icon="mdi:hand-back-right-outline", control_key="manuell_a_aktiv"),
    SpeicherSwitchDescription(key="handbetrieb_venus_d", name="Handbetrieb Venus D", icon="mdi:hand-back-right-outline", control_key="manuell_d_aktiv"),
    SpeicherSwitchDescription(key="handbetrieb_venus_e", name="Handbetrieb Venus E", icon="mdi:hand-back-right-outline", control_key="manuell_e_aktiv"),
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    coordinator: SpeicherLadelogikCoordinator = entry.runtime_data
    async_add_entities(
        SpeicherControlSwitch(coordinator, description)
        for description in SWITCHES
        if not description.key.startswith("handbetrieb_venus_")
        or description.key.rsplit("_", 1)[-1].upper() in coordinator.enabled_models
    )


class SpeicherControlSwitch(SpeicherLadelogikEntity, SwitchEntity):
    entity_description: SpeicherSwitchDescription

    def __init__(self, coordinator: SpeicherLadelogikCoordinator, description: SpeicherSwitchDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description
        slot = description.key.rsplit("_", 1)[-1].upper()
        if slot in coordinator.enabled_models:
            self._attr_name = description.name.replace(
                f"Venus {slot}", coordinator.storage_name(slot)
            )

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.control[self.entity_description.control_key])

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_set_control(self.entity_description.control_key, True)

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_set_control(self.entity_description.control_key, False)
