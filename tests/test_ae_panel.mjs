import assert from "node:assert/strict";
import test from "node:test";

const registry = new Map();
globalThis.HTMLElement = class {
  constructor() { this.attributes = {}; this.properties = {}; this.style = { setProperty: (key, value) => { this.properties[key] = value; } }; }
  setAttribute(key, value) { this.attributes[key] = value; }
  attachShadow() { this.shadowRoot = { querySelector: () => null, querySelectorAll: () => [] }; return this.shadowRoot; }
};
globalThis.customElements = {
  get: (name) => registry.get(name),
  define: (name, klass) => registry.set(name, klass),
};
await import("../custom_components/speicher_ladelogik_ae/frontend/speicher-ladelogik-ae-panel.js");
const Panel = registry.get("speicher-ladelogik-ae-panel-2-2-0");

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
  assert.match(p._storageSlot("A", "a"), /Freigegeben seit/);
  p._hass.states["sensor.power_e"].state = "0";
  assert.match(p._storageSlot("E", "e"), /Wartet bis/);
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

test("calibration moves to its own navigation and keeps all actions", () => {
  const p = panel();
  p._panel.config.entities = { kalibrierung_ruhe_unten: "number.rest" };
  p._hass.states["number.rest"] = { state: "45", attributes: { min: 0, max: 240, step: 1, unit_of_measurement: "min" } };
  assert.match(p._header(), /data-tab="calibration"/);
  assert.doesNotMatch(p._control(), /calibration-card|data-press="kalibrierung/);
  const html = p._calibration();
  assert.match(html, /calibration-card/);
  assert.match(html, /Ruhezeit vor dem Laden/);
  assert.match(html, /data-press="kalibrierung_abbrechen"/);
  assert.match(html, /data-press="kalibrierung_venus_e_morgen"/);
});

test("diagnostics place beginning over end and preserve technical details", () => {
  const p = panel();
  p._panel.config.entities = { planung: "sensor.plan" };
  p._hass.states["sensor.plan"] = { state: "Warten", attributes: {
    leistungsentscheidung_venus_a: { fenster_start_ts: 1791283020, simulation_ende_ts: 1791302400, restbedarf_kwh: 1.9 },
  } };
  const html = p._chargeDecision("A");
  assert.ok(html.indexOf("Geplanter Beginn") < html.indexOf("Restbedarf"));
  assert.ok(html.indexOf("Restbedarf") < html.indexOf("Planung bis"));
  assert.match(p._batteryCard("A", true), /<details[^>]*data-remember-details="battery-a"/);
  assert.match(p._batteryCard("A", true), /Pack-SoC/);
});

test("appearance survives recreation, validates values and never invokes HA services", () => {
  const saved = new Map();
  globalThis.localStorage = { getItem: (key) => saved.get(key) || null, setItem: (key, value) => saved.set(key, value) };
  try {
    const p = panel();
    p._hass.callService = () => { throw new Error("Presentation must not write controls"); };
    p._setAppearance("accent", "violet");
    p._setAppearance("theme", "light");
    p._setAppearance("density", "compact");
    p._setAppearance("batteryE", "blue");
    p._setAppearance("motion", "off");
    const restored = panel();
    assert.deepEqual(restored._appearance, p._appearance);
    restored._applyAppearance();
    assert.equal(restored.attributes["data-theme"], "light");
    assert.equal(restored.attributes["data-density"], "compact");
    assert.equal(restored.properties["--battery-e"], "#1964b5");
    assert.equal(restored.properties["--accent"], "#7542ba");
    restored._setAppearance("accent", 'red;display:none');
    assert.equal(restored._appearance.accent, "violet");
    saved.set("speicher_ladelogik_ae.appearance.v1", '{"accent":"invalid","theme":"broken","batteryA":"orange"}');
    const sanitized = panel();
    assert.equal(sanitized._appearance.accent, "green");
    assert.equal(sanitized._appearance.theme, "auto");
    assert.equal(sanitized._appearance.batteryA, "orange");
  } finally { delete globalThis.localStorage; }
});

test("automatic theme follows HA and storage failures do not break rendering", () => {
  globalThis.localStorage = { getItem: () => { throw new Error("blocked"); }, setItem: () => { throw new Error("blocked"); } };
  try {
    const p = panel();
    p._hass.themes = { darkMode: false };
    assert.equal(p._effectiveTheme(), "light");
    p._hass.themes.darkMode = true;
    assert.equal(p._effectiveTheme(), "dark");
    p._setAppearance("theme", "light");
    assert.equal(p._effectiveTheme(), "light");
    assert.match(p._appearanceNotice(), /dauerhafte Speichern/);
    p._appearanceOpen = true;
    assert.match(p._appearancePanel(), /Darstellung schließen/);
    assert.match(p._styles(), /prefers-reduced-motion/);
  } finally { delete globalThis.localStorage; }
});

test("storage status distinguishes permission, real flow, target and safety", () => {
  const p = panel();
  p._panel.config.entities = { planung: "sensor.plan" };
  const plan = { fahrplan_slot_aktiv_venus_a: true, daten_gueltig_venus_a: true };
  p._hass.states["sensor.plan"] = { attributes: plan };
  p._hass.states["sensor.power_a"].state = "0";
  assert.equal(p._storageStatus("A").label, "Freigegeben");
  p._hass.states["sensor.power_a"].state = "-700";
  assert.equal(p._storageStatus("A").label, "Lädt");
  p._hass.states["sensor.power_a"].state = "250";
  assert.equal(p._storageStatus("A").label, "Entlädt");
  p._hass.states["sensor.power_a"].state = "0";
  plan.ziel_venus_a_erreicht = true;
  assert.equal(p._storageStatus("A").label, "Voll");
  plan.obere_geraetegrenze_venus_a_prozent = 80;
  assert.equal(p._storageStatus("A").label, "Ziel erreicht");
  plan.daten_gueltig_venus_a = false;
  assert.equal(p._storageStatus("A").label, "Gesperrt");
});
