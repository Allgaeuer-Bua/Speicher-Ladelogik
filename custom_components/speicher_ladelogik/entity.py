"""Base entity for Speicher-Ladelogik."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NAME, VERSION
from .coordinator import SpeicherLadelogikCoordinator


class SpeicherLadelogikEntity(CoordinatorEntity[SpeicherLadelogikCoordinator]):
    """Base coordinator entity."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SpeicherLadelogikCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            name=coordinator.entry.title,
            manufacturer="Allgaeuer-Bua",
            model=NAME,
            sw_version=VERSION,
            configuration_url="https://github.com/Allgaeuer-Bua/Speicher-Ladelogik",
        )
