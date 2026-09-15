"""Operating mode selector for Speicher-Ladelogik."""

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import SpeicherLadelogikCoordinator
from .entity import SpeicherLadelogikEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    coordinator: SpeicherLadelogikCoordinator = entry.runtime_data
    async_add_entities([SpeicherModeSelect(coordinator)])


class SpeicherModeSelect(SpeicherLadelogikEntity, SelectEntity):
    _attr_name = "Betriebsart"
    _attr_icon = "mdi:tune-variant"
    _attr_options = ["Aus", "Beobachten", "Automatik"]

    def __init__(self, coordinator: SpeicherLadelogikCoordinator) -> None:
        super().__init__(coordinator, "betriebsart")

    @property
    def current_option(self) -> str:
        return str(self.coordinator.control["mode"])

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_set_mode(option)
