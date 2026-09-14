"""Sensor platform for Speicher-Ladelogik."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import SpeicherLadelogikCoordinator
from .entity import SpeicherLadelogikEntity


@dataclass(frozen=True, kw_only=True)
class SpeicherSensorDescription(SensorEntityDescription):
    """Describe a Speicher-Ladelogik sensor."""

    value_fn: Callable[[dict[str, Any]], Any]


SENSORS = (
    SpeicherSensorDescription(
        key="status",
        name="Status",
        icon="mdi:battery-clock-outline",
        value_fn=lambda data: "Bereit" if data["daten_gueltig"] else "Unvollständig",
    ),
    SpeicherSensorDescription(
        key="pv_planungswert",
        name="PV-Planungswert",
        icon="mdi:solar-power-variant-outline",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data["pv_planungswert_w"],
    ),
    SpeicherSensorDescription(
        key="daten_gemeinsam",
        name="Gemeinsame Daten",
        icon="mdi:database-check-outline",
        value_fn=lambda data: "bereit" if data["daten_gueltig_gemeinsam"] else "unvollständig",
    ),
    SpeicherSensorDescription(
        key="daten_venus_a",
        name="Daten Venus A",
        icon="mdi:battery-check-outline",
        value_fn=lambda data: "bereit" if data["daten_gueltig_venus_a"] else "unvollständig",
    ),
    SpeicherSensorDescription(
        key="daten_venus_e",
        name="Daten Venus E",
        icon="mdi:battery-check-outline",
        value_fn=lambda data: "bereit" if data["daten_gueltig_venus_e"] else "unvollständig",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Speicher-Ladelogik sensors."""
    coordinator: SpeicherLadelogikCoordinator = entry.runtime_data
    async_add_entities(
        SpeicherLadelogikSensor(coordinator, description) for description in SENSORS
    )


class SpeicherLadelogikSensor(SpeicherLadelogikEntity, SensorEntity):
    """A sensor backed by the integration coordinator."""

    entity_description: SpeicherSensorDescription

    def __init__(
        self,
        coordinator: SpeicherLadelogikCoordinator,
        description: SpeicherSensorDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self):
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.key != "status":
            return None
        data = self.coordinator.data
        return {
            "version": data["version"],
            "betriebsart": data["betriebsart"],
            "schreibzugriffe_aktiv": data["schreibzugriffe_aktiv"],
            "daten_gueltig_gemeinsam": data["daten_gueltig_gemeinsam"],
            "daten_gueltig_venus_a": data["daten_gueltig_venus_a"],
            "daten_gueltig_venus_e": data["daten_gueltig_venus_e"],
            "pv_planungswert_w": data["pv_planungswert_w"],
            "pv_planungswert_quelle": data["pv_planungswert_quelle"],
            "pv_ac_w": data["pv_ac_w"],
            "pv_mppt_summe_dc_w": data["pv_mppt_summe_dc_w"],
            "soc_venus_a": data["soc_venus_a"],
            "soc_venus_e": data["soc_venus_e"],
            "ac_leistung_venus_a_w": data["ac_leistung_venus_a_w"],
            "ac_leistung_venus_e_w": data["ac_leistung_venus_e_w"],
            "quellen_gesamt": data["quellen_gesamt"],
            "quellen_verfuegbar": data["quellen_verfuegbar"],
            "fehlende_entitaeten": data["fehlende_entitaeten"],
            "warnungen": data["warnungen"],
        }
