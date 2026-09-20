"""Native actions for calibration and error acknowledgement."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import SpeicherLadelogikCoordinator
from .entity import SpeicherLadelogikEntity


@dataclass(frozen=True, kw_only=True)
class SpeicherButtonDescription(ButtonEntityDescription):
    request: str


BUTTONS = (
    SpeicherButtonDescription(key="kalibrierung_venus_a_anfordern", name="Kalibrierung Venus A anfordern", icon="mdi:battery-sync", request="cal_a"),
    SpeicherButtonDescription(key="kalibrierung_venus_d_anfordern", name="Kalibrierung Venus D anfordern", icon="mdi:battery-sync", request="cal_d"),
    SpeicherButtonDescription(key="kalibrierung_venus_e_anfordern", name="Kalibrierung Venus E anfordern", icon="mdi:battery-sync", request="cal_e"),
    SpeicherButtonDescription(key="kalibrierung_venus_a_morgen", name="Kalibrierung Venus A morgen", icon="mdi:calendar-arrow-right", request="cal_a_tomorrow"),
    SpeicherButtonDescription(key="kalibrierung_venus_d_morgen", name="Kalibrierung Venus D morgen", icon="mdi:calendar-arrow-right", request="cal_d_tomorrow"),
    SpeicherButtonDescription(key="kalibrierung_venus_e_morgen", name="Kalibrierung Venus E morgen", icon="mdi:calendar-arrow-right", request="cal_e_tomorrow"),
    SpeicherButtonDescription(key="kalibrierung_venus_a_entfernen", name="Kalibrierauftrag Venus A entfernen", icon="mdi:playlist-remove", request="cancel_a"),
    SpeicherButtonDescription(key="kalibrierung_venus_d_entfernen", name="Kalibrierauftrag Venus D entfernen", icon="mdi:playlist-remove", request="cancel_d"),
    SpeicherButtonDescription(key="kalibrierung_venus_e_entfernen", name="Kalibrierauftrag Venus E entfernen", icon="mdi:playlist-remove", request="cancel_e"),
    SpeicherButtonDescription(key="kalibrierung_abbrechen", name="Laufende Kalibrierung abbrechen", icon="mdi:cancel", request="cancel"),
    SpeicherButtonDescription(key="fehler_quittieren", name="Schreibfehler quittieren", icon="mdi:check-decagram-outline", request="ack"),
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    coordinator: SpeicherLadelogikCoordinator = entry.runtime_data
    async_add_entities(
        SpeicherActionButton(coordinator, description)
        for description in BUTTONS
        if not description.key.startswith("kalibrierung_venus_")
        or description.key.split("_")[2].upper() in coordinator.enabled_models
    )


class SpeicherActionButton(SpeicherLadelogikEntity, ButtonEntity):
    entity_description: SpeicherButtonDescription

    def __init__(self, coordinator: SpeicherLadelogikCoordinator, description: SpeicherButtonDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description
        parts = description.key.split("_")
        if len(parts) > 2 and parts[2].upper() in coordinator.enabled_models:
            slot = parts[2].upper()
            self._attr_name = description.name.replace(
                f"Venus {slot}", coordinator.storage_name(slot)
            )

    async def async_press(self) -> None:
        await self.coordinator.async_request_action(self.entity_description.request)
