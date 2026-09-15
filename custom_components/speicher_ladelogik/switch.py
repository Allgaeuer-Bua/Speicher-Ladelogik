"""Switch platform for guarded Speicher-Ladelogik control."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import SpeicherLadelogikCoordinator
from .entity import SpeicherLadelogikEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the guarded register-control switch."""
    coordinator: SpeicherLadelogikCoordinator = entry.runtime_data
    async_add_entities([SpeicherRegisterControlSwitch(coordinator)])


class SpeicherRegisterControlSwitch(SpeicherLadelogikEntity, SwitchEntity):
    """Explicitly arm register writes until the next integration restart."""

    _attr_name = "Registersteuerung"
    _attr_icon = "mdi:shield-lock-outline"

    def __init__(self, coordinator: SpeicherLadelogikCoordinator) -> None:
        super().__init__(coordinator, "registersteuerung")

    @property
    def is_on(self) -> bool:
        return self.coordinator.write_enabled

    async def async_turn_on(self, **kwargs) -> None:
        """Enable guarded writes after validating all prerequisites."""
        await self.coordinator.async_set_write_enabled(True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Stop issuing new register writes."""
        await self.coordinator.async_set_write_enabled(False)
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}
        return {
            "sicherheitsmodus": "Nach jedem HA-/Integrationsneustart aus",
            "letzter_schreibzugriff_ts": data.get("letzter_schreibzugriff_ts"),
            "letzter_schreibfehler": data.get("letzter_schreibfehler"),
            "letzte_schreibergebnisse": data.get("letzte_schreibergebnisse", []),
        }
