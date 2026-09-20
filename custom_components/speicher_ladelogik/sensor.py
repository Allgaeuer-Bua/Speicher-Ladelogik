"""Sensor platform for Speicher-Ladelogik."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import SpeicherLadelogikCoordinator
from .entity import SpeicherLadelogikEntity

PHASE_LABELS = {
    "idle": "Bereit",
    "requested": "Auftrag vorgemerkt",
    "drain": "Entladen auf 13 %",
    "wait": "Wartet auf PV-Fenster",
    "charge": "Kalibrierladung",
    "rest": "Ruheprüfung",
    "paused": "Pausiert",
    "restore": "Grenzwerte wiederherstellen",
    "done": "Erfolgreich beendet",
    "incomplete": "Wiederholung vorgemerkt",
    "cancelled": "Abgebrochen",
    "error": "Fehler",
}


def _calibration_state(data: dict[str, Any]) -> str:
    """Return the translated calibration phase including its configured power."""
    calibration = data.get("calibration", {})
    phase = calibration.get("phase", "error")
    if phase == "charge":
        power = round(float(calibration.get("leistung_w", 500)))
        return f"Kalibrierladung mit {power} W"
    return PHASE_LABELS.get(phase, phase)


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
        key="daten_venus_d",
        name="Daten Venus D",
        icon="mdi:battery-check-outline",
        value_fn=lambda data: "bereit" if data["daten_gueltig_venus_d"] else "unvollständig",
    ),
    SpeicherSensorDescription(
        key="daten_venus_e",
        name="Daten Venus E",
        icon="mdi:battery-check-outline",
        value_fn=lambda data: "bereit" if data["daten_gueltig_venus_e"] else "unvollständig",
    ),
    SpeicherSensorDescription(
        key="planung",
        name="Planung",
        icon="mdi:timeline-clock-outline",
        value_fn=lambda data: data.get("plan", {}).get("status", "Fehler"),
    ),
    SpeicherSensorDescription(
        key="kalibrierung",
        name="Kalibrierung",
        icon="mdi:battery-sync-outline",
        value_fn=_calibration_state,
    ),
    SpeicherSensorDescription(
        key="wirkungsgrad_venus_a",
        name="Wirkungsgrad Venus A",
        icon="mdi:percent-outline",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data["wirkungsgrad_venus_a"]["wirkungsgrad"],
    ),
    SpeicherSensorDescription(
        key="verlustleistung_venus_a",
        name="Verlustleistung Venus A",
        icon="mdi:lightning-bolt-outline",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data["wirkungsgrad_venus_a"]["verlust_w"],
    ),
    SpeicherSensorDescription(
        key="wirkungsgrad_venus_e",
        name="Wirkungsgrad Venus E",
        icon="mdi:percent-outline",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data["wirkungsgrad_venus_e"]["wirkungsgrad"],
    ),
    SpeicherSensorDescription(
        key="wirkungsgrad_venus_d",
        name="Wirkungsgrad Venus D",
        icon="mdi:percent-outline",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data["wirkungsgrad_venus_d"]["wirkungsgrad"],
    ),
    SpeicherSensorDescription(
        key="verlustleistung_venus_d",
        name="Verlustleistung Venus D",
        icon="mdi:lightning-bolt-outline",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data["wirkungsgrad_venus_d"]["verlust_w"],
    ),
    SpeicherSensorDescription(
        key="verlustleistung_venus_e",
        name="Verlustleistung Venus E",
        icon="mdi:lightning-bolt-outline",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data["wirkungsgrad_venus_e"]["verlust_w"],
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
        SpeicherLadelogikSensor(coordinator, description)
        for description in SENSORS
        if not any(
            f"venus_{model.lower()}" in description.key
            and model not in coordinator.enabled_models
            for model in ("A", "D", "E")
        )
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
        for slot in coordinator.enabled_models:
            if f"venus_{slot.lower()}" in description.key:
                self._attr_name = description.name.replace(
                    f"Venus {slot}", coordinator.storage_name(slot)
                )
                break

    @property
    def native_value(self):
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        data = self.coordinator.data
        if self.entity_description.key == "status":
            attributes = {
                "version": data["version"],
                "betriebsart": data["betriebsart"],
                "schreibzugriffe_aktiv": data["schreibzugriffe_aktiv"],
                "planung_aktiv": data["planung_aktiv"],
                "planungsfehler": data["planungsfehler"],
                "daten_gueltig_gemeinsam": data["daten_gueltig_gemeinsam"],
                "pv_planungswert_w": data["pv_planungswert_w"],
                "pv_planungswert_quelle": data["pv_planungswert_quelle"],
                "pv_ac_w": data["pv_ac_w"],
                "pv_mppt_summe_dc_w": data["pv_mppt_summe_dc_w"],
                "quellen_gesamt": data["quellen_gesamt"],
                "quellen_verfuegbar": data["quellen_verfuegbar"],
                "fehlende_entitaeten": data["fehlende_entitaeten"],
                "warnungen": data["warnungen"],
                "letzter_schreibzugriff_ts": data.get("letzter_schreibzugriff_ts"),
                "letzter_schreibfehler": data.get("letzter_schreibfehler"),
                "letzte_schreibergebnisse": data.get("letzte_schreibergebnisse", []),
            }
            for model in self.coordinator.enabled_models:
                name = model.lower()
                for prefix in (
                    "daten_gueltig_venus_",
                    "soc_venus_",
                    "ac_leistung_venus_",
                ):
                    suffix = "_w" if prefix == "ac_leistung_venus_" else ""
                    key = f"{prefix}{name}{suffix}"
                    attributes[key] = data.get(key)
                attributes[f"kalibrierung_faellig_{name}"] = data.get(
                    f"kalibrierung_faellig_{name}"
                )
            return attributes
        if self.entity_description.key == "planung":
            plan = data.get("plan", {})
            keys = (
                "version",
                "betriebsart",
                "regelung_aktiv",
                "daten_gueltig",
                "daten_gueltig_gemeinsam",
                "normaler_fahrplan_status",
                "normaler_fahrplan_grund",
                "pv_planungswert_w",
                "pv_planungswert_quelle",
                "ueberschuss_quelle",
                "netto_ueberschuss_w",
                "effizienzmodus",
                "sollwertstrategie",
                "prognose_heute_erwartet_kwh",
                "prognose_rest_erwartet_kwh",
                "prognose_morgen_kwh",
                "tagesklasse",
                "ladefenster_start_ts",
                "ladefenster_ende_ts",
                "fenster_fortschritt_prozent",
                "sicher_speicherbar_rest_kwh",
                "sicher_speicherbar_fenster_rest_kwh",
                "deckungsfaktor",
                "knapp",
                "restbedarf_kwh",
                "soll_laden",
                "soll_ladeleistung_gesamt_w",
                "verteilungsmodus",
                "mittagsspitzen_aktiv",
                "mittagsspitzen_planbar",
                "einspeiseziel_w",
                "spitzenfenster_start_ts",
                "spitzenfenster_ende_ts",
                "spitzenplan_voll_ts",
                "vorziehen_noetig",
                "fruehestens_voll_ts",
                "ziel_fehlmenge_simulation_kwh",
                "fahrplan_slot_start_ts",
                "fahrplan_slot_ende_ts",
                "fahrplan_entscheidung_fixiert_bis_ts",
                "fahrplan_slot_verriegelt",
                "fahrplan_slot_aktiv",
                "fahrplan_slot_status",
                "entscheidungsgrund",
                "warnungen",
                "datenfehler_aktuell",
            )
            attributes = {key: plan.get(key) for key in keys}
            model_fields = (
                "daten_gueltig_venus_{name}",
                "restbedarf_venus_{name}_kwh",
                "untere_geraetegrenze_venus_{name}_prozent",
                "obere_geraetegrenze_venus_{name}_prozent",
                "soll_ladegrenze_venus_{name}_w",
                "fahrplan_ladegrenze_roh_venus_{name}_w",
                "fahrplan_ladegrenze_stabil_venus_{name}_w",
                "sollwert_venus_{name}_gehalten",
                "sollwert_venus_{name}_grund",
                "ziel_venus_{name}_erreicht",
                "ziel_venus_{name}_latch_soc",
                "ziel_venus_{name}_latch_grund",
                "ziel_venus_{name}_latch_aktiv",
                "ac_leistung_venus_{name}_frisch",
                "ac_leistung_venus_{name}_status",
                "ac_leistung_venus_{name}_alter_min",
                "fahrplan_slot_aktiv_venus_{name}",
                "fahrplan_slot_grund_venus_{name}",
            )
            for model in self.coordinator.enabled_models:
                name = model.lower()
                for template in model_fields:
                    key = template.format(name=name)
                    attributes[key] = plan.get(key)
            attributes["vorgeschlagene_befehle"] = data.get(
                "proposed_commands", []
            )
            attributes["schreibzugriffe_aktiv"] = data["schreibzugriffe_aktiv"]
            return attributes
        if self.entity_description.key == "kalibrierung":
            calibration = data.get("calibration", {})
            keys = (
                "phase",
                "batterie",
                "grund",
                "grund_code",
                "leistung_w",
                "energie_ac_kwh",
                "start_ts",
                "ende_ts",
                "peer_entladesperre_freigegeben",
                "peer_dauerfreigabe_14_prozent",
                "peer_netzbezug_freigegeben",
                "peer_netzbezug_seit_ts",
                "peer_netzfrei_seit_ts",
                "peer_freigabe_grund",
                "netzleistung_w",
                "peer_freigabe_schwelle_prozent",
            )
            attributes = {key: calibration.get(key) for key in keys}
            for model in self.coordinator.enabled_models:
                name = model.lower()
                for key in (
                    f"kalibrieren_{name}_sicher",
                    f"{name}_pruefhinweise",
                    f"heute_{name}",
                    f"morgen_{name}",
                    f"kalibrierung_letzter_erfolg_{name}_ts",
                    f"kalibrierung_naechste_faelligkeit_{name}_ts",
                    f"kalibrierung_faellig_{name}",
                ):
                    source = data if key.startswith("kalibrierung_") else calibration
                    attributes[key] = source.get(key)
                drift_fields = (
                    (f"drift_{name}_p1_mv", f"drift_{name}_p2_mv")
                    if self.coordinator.storage_has_packs(model)
                    else (f"drift_{name}_mv",)
                )
                for key in drift_fields:
                    attributes[key] = calibration.get(key)
            return attributes
        for model in self.coordinator.enabled_models:
            name = model.lower()
            if self.entity_description.key in {
                f"wirkungsgrad_venus_{name}",
                f"verlustleistung_venus_{name}",
            }:
                return dict(data[f"wirkungsgrad_venus_{name}"])
        return None
