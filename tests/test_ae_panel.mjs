import assert from "node:assert/strict";
import test from "node:test";

const registry = new Map();
globalThis.HTMLElement = class {
  attachShadow() { this.shadowRoot = { querySelector: () => null }; return this.shadowRoot; }
};
globalThis.customElements = {
  get: (name) => registry.get(name),
  define: (name, klass) => registry.set(name, klass),
};
await import("../custom_components/speicher_ladelogik_ae/frontend/speicher-ladelogik-ae-panel.js");
const Panel = registry.get("speicher-ladelogik-ae-panel-2-1-2");

function panel() {
  const instance = new Panel();
  instance._panel = { config: {
    models: ["A", "E"],
    sources: {
      pv: "sensor.pv", grid: "sensor.grid", house: "sensor.house",
      power_a: "sensor.power_a", power_e: "sensor.power_e",
      soc_a: "sensor.soc_a", soc_e: "sensor.soc_e",
    },
  } };
  instance._hass = { states: Object.fromEntries([
    ["pv", 6500], ["grid", -3900], ["house", 1000],
    ["power_a", -1100], ["power_e", 500], ["soc_a", 99], ["soc_e", 77],
  ].map(([id, value]) => [`sensor.${id}`, { state: String(value), attributes: {} }])) };
  return instance;
}

test("independent battery flows retain their own power, direction, SoC and source", () => {
  const p = panel();
  const data = p._flowData();
  assert.deepEqual(data.batteries.map((battery) => battery.model), ["A", "E"]);
  assert.deepEqual(data.batteries.map((battery) => battery.power), [-1100, 500]);
  const html = p._flowCard();
  assert.match(html, /data-live-flow="soc-a">99 %/);
  assert.match(html, /data-live-flow="soc-e">77 %/);
  assert.match(html, /data-flow-route="battery-a"/);
  assert.match(html, /data-flow-route="battery-e"/);
  assert.doesNotMatch(html, /data-live-flow="battery-soc"/);
});

test("solar and house nodes have a longer vertical connection", () => {
  const p = panel();
  const data = p._flowData();
  assert.equal(data.pvPath, "M 500 80 C 500 150 500 230 500 300");
  assert.match(p._styles(), /\.flow-card \.flow-canvas\{min-height:520px\}/);
});

test("overview keeps live battery SoC in the flow without a separate history card", () => {
  const p = panel();
  const html = p._overview();
  assert.doesNotMatch(html, /SoC je Speicher|history-chart|chart-ranges/);
  assert.match(html, /Venus A/);
  assert.match(html, /Venus E/);
  assert.doesNotMatch(html, /Energie heute/i);
});

test("storage retains live details and energy totals without history charts", () => {
  const p = panel();
  const html = p._batteryCard("A", true);
  assert.match(html, /Pack-SoC/);
  assert.match(html, /Heute geladen/);
  assert.doesNotMatch(html, /SoC und Leistungsverlauf|Zelldrift je Pack|history-chart|chart-ranges/);
  assert.doesNotMatch(html, /AC-Leistung · Laden \/ Entladen/);
});

test("calibration displays the measured lower rest as a preference", () => {
  const p = panel();
  p._panel.config.entities = { kalibrierung: "sensor.calibration" };
  p._hass.states["sensor.calibration"] = {
    state: "Lädt", attributes: {
      letzte_ruhe_vor_laden_s_e: 600,
      auftraege: [{ batterie: "E", phase: "empty_rest", ruhe_ende_ts: Date.now() / 1000 + 600 }],
    },
  };
  const html = p._calibrationCard();
  assert.match(html, /Letzte Ruhe vor Ladebeginn: 10 min/);
  assert.match(html, /Angestrebte Ruhe bis/);
});

test("daily release is shown per battery and effective peak state wins over its switch", () => {
  const p = panel();
  p._panel.config.entities = { planung: "sensor.plan", mittagsspitzen: "switch.peak" };
  p._hass.states["switch.peak"] = { state: "on", attributes: {} };
  p._hass.states["sensor.plan"] = { state: "Ladefreigabe aktiv", attributes: {
    mittagsspitzen_aktiv: false, mittagsspitzen_planbar: false,
    fahrplan_slot_aktiv_venus_a: true, fahrplan_slot_aktiv_venus_e: false,
    ladefreigabe_venus_a_seit_ts: Date.now() / 1000 - 300,
    ladebeginn_venus_e_ts: Date.now() / 1000 + 3600,
  } };
  assert.match(p._storageSlot("A", "a"), /freigegeben seit/);
  assert.match(p._storageSlot("E", "e"), /Beginn geplant/);
  assert.match(p._peakDetails(), />Aus</);
  assert.doesNotMatch(p._planningCard(), /Entscheidung fixiert|Pausenslot|15-Minuten/);
});

test("diagnostics retain the first release reason alongside the current hold", () => {
  const p = panel();
  p._panel.config.entities = { planung: "sensor.plan" };
  p._hass.states["sensor.plan"] = { state: "Ladefreigabe aktiv", attributes: {
    leistungsentscheidung_venus_a: { zeit_ts: 1791095172, grund: "Ladefreigabe bleibt bestehen" },
    ladefreigabe_venus_a_ursprung: { zeit_ts: 1791093603, grund: "Eigenes vorzeitiges SoC-Ziel absichern" },
  } };
  const html = p._diagnostics();
  assert.match(html, /Erste Freigabe/);
  assert.match(html, /Eigenes vorzeitiges SoC-Ziel absichern/);
  assert.match(html, /Ladefreigabe bleibt bestehen/);
});

test("only today's power history is requested for energy totals", () => {
  const p = panel();
  p._tab = "overview";
  assert.deepEqual(p._historySourceIds(), []);
  p._tab = "batteries";
  assert.deepEqual(p._historySourceIds(), ["sensor.power_a", "sensor.power_e"]);
});

test("charge decisions separate limits, reasons and errors per battery", () => {
  const p = panel();
  p._panel.config.entities = { planung: "sensor.plan", bevorzugte_ladeleistung_venus_a: "number.preferred_a" };
  p._hass.states["number.preferred_a"] = { state: "1100", attributes: {} };
  p._hass.states["sensor.plan"] = { state: "Warten", attributes: {
    daten_gueltig_venus_a: false, soll_ladegrenze_venus_a_w: 0,
    leistungsentscheidung_venus_a: { zeit_ts: 1791274300, bevorzugt_w: 0, roh_w: 0, stabil_w: 0,
      grund: "Sicherheitsstopp", sollwert_grund: "Sicherheitsstopp", restbedarf_kwh: 1.91,
      datenfehler: ["A: Gerätegrenzen ungültig", "E: anderer Fehler"], fehlmenge_bevorzugt_kwh: 0 },
  } };
  const html = p._chargeDecision("A");
  assert.match(html, /decision-blocked/);
  assert.match(html, /Bevorzugt/);
  assert.match(html, /1,1 kW/);
  assert.match(html, /Neu berechnet/);
  assert.match(html, /Sollgrenze/);
  assert.match(html, /Gerätegrenzen ungültig/);
  assert.doesNotMatch(html, /anderer Fehler/);
  assert.match(html, /<details[^>]*data-decision-details="A"/);
  assert.equal((html.match(/<p class="decision-reason">Sicherheitsstopp<\/p>/g) || []).length, 1);
});
