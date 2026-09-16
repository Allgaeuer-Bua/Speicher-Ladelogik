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
    "charge": "Kalibrierladung mit 500 W",
    "rest": "Ruheprüfung",
    "paused": "Pausiert",
    "restore": "Grenzwerte wiederherstellen",
    "done": "Erfolgreich beendet",
    "incomplete": "Wiederholung vorgemerkt",
    "cancelled": "Abgebrochen",
    "error": "Fehler",
}


def _comparison_state(data: dict[str, Any]) -> str:
    if data.get("schattenplanung_fehler"):
        return "Fehler"
    comparison = data.get("shadow_comparison", {})
    if not comparison.get("available"):
        return "Referenz fehlt"
    if comparison.get("matches"):
        return "Übereinstimmend"
    if comparison.get("funktional_passend"):
        return "Nur gewollte Abweichungen"
    return f"{len(comparison.get('differences', []))} Abweichungen"


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
    SpeicherSensorDescription(
        key="planung",
        name="Planung",
        icon="mdi:timeline-clock-outline",
        value_fn=lambda data: data.get("shadow_plan", {}).get("status", "Fehler"),
    ),
    SpeicherSensorDescription(
        key="kalibrierung",
        name="Kalibrierung",
        icon="mdi:battery-sync-outline",
        value_fn=lambda data: PHASE_LABELS.get(
            data.get("shadow_calibration", {}).get("phase"),
            data.get("shadow_calibration", {}).get("phase", "Fehler"),
        ),
    ),
    SpeicherSensorDescription(
        key="planvergleich",
        name="Planvergleich",
        icon="mdi:compare-horizontal",
        value_fn=_comparison_state,
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
        data = self.coordinator.data
        if self.entity_description.key == "status":
            return {
                "version": data["version"],
                "betriebsart": data["betriebsart"],
                "schreibzugriffe_aktiv": data["schreibzugriffe_aktiv"],
                "schattenplanung_aktiv": data["schattenplanung_aktiv"],
                "schattenplanung_fehler": data["schattenplanung_fehler"],
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
                "letzter_schreibzugriff_ts": data.get("letzter_schreibzugriff_ts"),
                "letzter_schreibfehler": data.get("letzter_schreibfehler"),
                "letzte_schreibergebnisse": data.get("letzte_schreibergebnisse", []),
                "kalibrierung_faellig_a": data.get("kalibrierung_faellig_a"),
                "kalibrierung_faellig_e": data.get("kalibrierung_faellig_e"),
            }
        if self.entity_description.key == "planung":
            plan = data.get("shadow_plan", {})
            keys = (
                "version",
                "betriebsart",
                "regelung_aktiv",
                "daten_gueltig",
                "daten_gueltig_gemeinsam",
                "daten_gueltig_venus_a",
                "daten_gueltig_venus_e",
                "normaler_fahrplan_status",
                "normaler_fahrplan_grund",
                "pv_planungswert_w",
                "pv_planungswert_quelle",
                "ueberschuss_quelle",
                "netto_ueberschuss_w",
                "effizienzmodus",
                "sollwertstrategie",
                "prognose_heute_erwartet_kwh",
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
                "restbedarf_venus_a_kwh",
                "restbedarf_venus_e_kwh",
                "untere_geraetegrenze_venus_a_prozent",
                "obere_geraetegrenze_venus_a_prozent",
                "untere_geraetegrenze_venus_e_prozent",
                "obere_geraetegrenze_venus_e_prozent",
                "soll_laden",
                "soll_ladeleistung_gesamt_w",
                "soll_ladegrenze_venus_a_w",
                "soll_ladegrenze_venus_e_w",
                "fahrplan_ladegrenze_roh_venus_a_w",
                "fahrplan_ladegrenze_stabil_venus_a_w",
                "sollwert_venus_a_gehalten",
                "sollwert_venus_a_grund",
                "ziel_venus_a_erreicht",
                "ziel_venus_a_latch_soc",
                "ziel_venus_a_latch_grund",
                "ziel_venus_a_latch_aktiv",
                "ac_leistung_venus_a_frisch",
                "ac_leistung_venus_a_status",
                "ac_leistung_venus_a_alter_min",
                "fahrplan_ladegrenze_roh_venus_e_w",
                "fahrplan_ladegrenze_stabil_venus_e_w",
                "sollwert_venus_e_gehalten",
                "sollwert_venus_e_grund",
                "ziel_venus_e_erreicht",
                "ziel_venus_e_latch_soc",
                "ziel_venus_e_latch_grund",
                "ziel_venus_e_latch_aktiv",
                "ac_leistung_venus_e_frisch",
                "ac_leistung_venus_e_status",
                "ac_leistung_venus_e_alter_min",
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
                "fahrplan_slot_aktiv_venus_a",
                "fahrplan_slot_grund_venus_a",
                "fahrplan_slot_aktiv_venus_e",
                "fahrplan_slot_grund_venus_e",
                "entscheidungsgrund",
                "warnungen",
                "datenfehler_aktuell",
            )
            attributes = {key: plan.get(key) for key in keys}
            attributes["vorgeschlagene_befehle"] = data.get(
                "shadow_proposed_commands", []
            )
            attributes["schreibzugriffe_aktiv"] = data["schreibzugriffe_aktiv"]
            return attributes
        if self.entity_description.key == "kalibrierung":
            calibration = data.get("shadow_calibration", {})
            keys = (
                "phase",
                "batterie",
                "grund",
                "grund_code",
                "energie_ac_kwh",
                "start_ts",
                "ende_ts",
                "kalibrieren_a_sicher",
                "kalibrieren_e_sicher",
                "a_pruefhinweise",
                "e_pruefhinweise",
                "heute_a",
                "heute_e",
                "morgen_a",
                "morgen_e",
                "drift_a_p1_mv",
                "drift_a_p2_mv",
                "drift_e_mv",
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
            for key in (
                "kalibrierung_letzter_erfolg_a_ts",
                "kalibrierung_letzter_erfolg_e_ts",
                "kalibrierung_naechste_faelligkeit_a_ts",
                "kalibrierung_naechste_faelligkeit_e_ts",
                "kalibrierung_faellig_a",
                "kalibrierung_faellig_e",
            ):
                attributes[key] = data.get(key)
            return attributes
        if self.entity_description.key == "planvergleich":
            return dict(data.get("shadow_comparison", {}))
        if self.entity_description.key in {
            "wirkungsgrad_venus_a", "verlustleistung_venus_a"
        }:
            return dict(data["wirkungsgrad_venus_a"])
        if self.entity_description.key in {
            "wirkungsgrad_venus_e", "verlustleistung_venus_e"
        }:
            return dict(data["wirkungsgrad_venus_e"])
        return None
