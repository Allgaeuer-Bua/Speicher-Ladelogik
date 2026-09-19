import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const registry = new Map();

globalThis.HTMLElement = class {
  constructor() {
    this.isConnected = false;
  }

  attachShadow() {
    this.shadowRoot = { innerHTML: "", querySelectorAll: () => [] };
    return this.shadowRoot;
  }
};

globalThis.customElements = {
  define: (name, klass) => registry.set(name, klass),
  get: (name) => registry.get(name),
};
globalThis.window = { confirm: () => true };

await import(
  "../custom_components/speicher_ladelogik/frontend/speicher-ladelogik-panel.js"
);

const manifest = JSON.parse(readFileSync(
  new URL("../custom_components/speicher_ladelogik/manifest.json", import.meta.url),
  "utf8",
));
const panelElementName = `speicher-ladelogik-panel-${manifest.version.replaceAll(".", "-")}`;
const Panel = registry.get(panelElementName);

function createPanel() {
  const calls = [];
  const panel = new Panel();
  panel._panel = {
    config: {
      entities: {
        betriebsart: "select.speicher_ladelogik_betriebsart",
        mittagsspitzen: "switch.speicher_ladelogik_mittagsspitzen",
        mindestreserve: "number.speicher_ladelogik_mindestreserve",
        kalibrierleistung: "number.speicher_ladelogik_kalibrierleistung",
        kalibrierung: "sensor.speicher_ladelogik_kalibrierung",
        fehler_quittieren: "button.speicher_ladelogik_fehler_quittieren",
      },
      sources: {
        pv: "sensor.pv_power",
        grid: "sensor.grid_power",
        house: "sensor.house_power",
        power_a: "sensor.venus_a_power",
        power_e: "sensor.venus_e_power",
        soc_a: "sensor.venus_a_soc",
        soc_e: "sensor.venus_e_soc",
        drift_e: "sensor.venus_e_cell_delta",
      },
    },
  };
  panel._hass = {
    states: {
      "switch.speicher_ladelogik_mittagsspitzen": { state: "on", attributes: {} },
      "number.speicher_ladelogik_mindestreserve": { state: "2", attributes: {} },
      "number.speicher_ladelogik_kalibrierleistung": {
        state: "750",
        attributes: { min: 400, max: 1500, step: 50, unit_of_measurement: "W" },
      },
      "sensor.speicher_ladelogik_kalibrierung": {
        state: "Bereit",
        attributes: {
          heute_a: { ok: true, start: 1_800_000_000, end: 1_800_007_200, longest_h: 4.5, required_h: 2 },
          morgen_a: { ok: false, longest_h: 1, required_h: 2 },
          batterie: "—",
          grund: "Kein Auftrag aktiv",
        },
      },
      "sensor.pv_power": { state: "4200", attributes: {} },
      "sensor.grid_power": { state: "-250", attributes: {} },
      "sensor.house_power": { state: "1200", attributes: {} },
      "sensor.venus_a_power": { state: "300", attributes: {} },
      "sensor.venus_e_power": { state: "0", attributes: {} },
      "sensor.venus_a_soc": { state: "65", attributes: {} },
      "sensor.venus_e_soc": { state: "98", attributes: {} },
      "sensor.venus_e_cell_delta": {
        state: "0.008000135",
        attributes: { unit_of_measurement: "V" },
      },
    },
    callService: async (...args) => calls.push(args),
  };
  return { panel, calls };
}

test("panel resolves native and configured source entities", () => {
  const { panel } = createPanel();
  assert.equal(panel._eid("betriebsart"), "select.speicher_ladelogik_betriebsart");
  assert.equal(panel._source("pv").state, "4200");
  assert.equal(panel._isOn("mittagsspitzen"), true);
});

test("panel controls call the matching Home Assistant services", async () => {
  const { panel, calls } = createPanel();

  await panel._setMode("Automatik");
  await panel._toggle("mittagsspitzen");
  await panel._setNumber("mindestreserve", "3.5");
  await panel._setNumber("kalibrierleistung", "800");
  await panel._press("fehler_quittieren");

  assert.deepEqual(calls, [
    ["select", "select_option", {
      entity_id: "select.speicher_ladelogik_betriebsart",
      option: "Automatik",
    }],
    ["switch", "turn_off", {
      entity_id: "switch.speicher_ladelogik_mittagsspitzen",
    }],
    ["number", "set_value", {
      entity_id: "number.speicher_ladelogik_mindestreserve",
      value: 3.5,
    }],
    ["number", "set_value", {
      entity_id: "number.speicher_ladelogik_kalibrierleistung",
      value: 800,
    }],
    ["button", "press", {
      entity_id: "button.speicher_ladelogik_fehler_quittieren",
    }],
  ]);
});

test("panel uses the Venus AC sign convention and translates calibration phases", () => {
  const { panel } = createPanel();

  assert.deepEqual(panel._batteryMode(-945), { label: "Lädt", tone: "charge" });
  assert.deepEqual(panel._batteryMode(945), { label: "Entlädt", tone: "discharge" });
  assert.deepEqual(panel._batteryMode(0), { label: "Bereit", tone: "idle" });
  assert.equal(panel._statusLabel("Kalibrierung A: drain"), "Kalibrierung A: Entladen auf 13 %");
});

test("panel formats single-value drift sensors and register results", () => {
  const { panel } = createPanel();
  const [drift] = panel._sourceStates("drift_e");

  assert.equal(panel._drift(drift), "8 mV");
  assert.equal(panel._driftTone(panel._driftValue(drift)), "good");
  assert.equal(panel._driftTone(35), "warn");
  assert.equal(panel._driftTone(50), "bad");
  assert.equal(
    panel._formatWriteResult({
      entity: "number.marstek_venus_e_entladeleistung",
      value: 0,
      battery: "E",
      restore: false,
      ok: true,
      written: true,
    }),
    "Venus E: Entladeleistung auf 0 W gesetzt und bestätigt",
  );
});

test("overview replaces duplicate battery cards with daily history cards", () => {
  const { panel } = createPanel();
  const overview = panel._overview();

  assert.match(overview, /Energie heute/);
  assert.match(overview, /SoC · heute/);
  assert.match(overview, /Mittagsspitzenkappung/);
  assert.doesNotMatch(overview, /battery-pair span-full/);
  assert.match(panel._header(), />Speicher</);
});

test("planning uses the remaining forecast and labels the battery fill need", () => {
  const { panel } = createPanel();
  panel._panel.config.entities.planung = "sensor.planung";
  panel._hass.states["sensor.planung"] = {
    state: "Bereit",
    attributes: { prognose_rest_erwartet_kwh: 12.5, prognose_heute_erwartet_kwh: 42.5, restbedarf_kwh: 3.2 },
  };
  const card = panel._planningCard();
  assert.match(card, /Restprognose heute/);
  assert.match(card, /12,5 kWh/);
  assert.doesNotMatch(card, /42,5 kWh/);
  assert.match(card, /Restbedarf Speicherfüllung/);
  assert.match(card, /Geplante Einspeisung zur PV-Spitze/);
});

test("number fields show whole steps as integers and retain fractional reserves", () => {
  const { panel } = createPanel();
  panel._hass.states["number.speicher_ladelogik_kalibrierleistung"].state = "750.0";
  panel._hass.states["number.speicher_ladelogik_mindestreserve"].attributes = {
    step: 0.1, unit_of_measurement: "kWh",
  };
  assert.match(panel._numberRow(["kalibrierleistung", "Ladeleistung", ""]), /value="750"/);
  assert.match(panel._numberRow(["mindestreserve", "Mindestreserve", ""]), /value="2"/);
  panel._hass.states["number.speicher_ladelogik_mindestreserve"].state = "2.5";
  assert.match(panel._numberRow(["mindestreserve", "Mindestreserve", ""]), /value="2\.5"/);
});

test("charts do not draw a slope across a long change without readings", () => {
  const { panel } = createPanel();
  const now = Date.now();
  assert.deepEqual(panel._chartSegments([
    { t: now - 4_000_000, v: 0.1 },
    { t: now - 3_000_000, v: -0.5 },
    { t: now - 2_999_000, v: -0.4 },
  ]).map((segment) => segment.length), [1, 2]);
  assert.equal(panel._chartSegments([
    { t: now - 4_000_000, v: 0.1 },
    { t: now - 3_000_000, v: 0.1 },
  ]).length, 1);
});

test("calibration shows the last success per storage", () => {
  const { panel } = createPanel();
  const last = Date.now() / 1000 - 2 * 86400;
  panel._hass.states["sensor.speicher_ladelogik_kalibrierung"].attributes.kalibrierung_letzter_erfolg_a_ts = last;
  const card = panel._calibrationCard();
  assert.match(card, /Letzte Kalibrierung: vor 2 Tagen/);
  assert.match(card, /Noch keine erfolgreiche Kalibrierung bekannt/);
});

test("daily battery energy separates charging and discharging signs", () => {
  const { panel } = createPanel();
  const now = Date.now();
  panel._history = {
    "sensor.venus_a_power": [
      { s: "-1000", lu: (now - 7_200_000) / 1000 },
      { s: "500", lu: (now - 3_600_000) / 1000 },
      { s: "500", lu: now / 1000 },
    ],
  };

  const energy = panel._batteryEnergy("a");
  assert.ok(energy.charged > 0.99 && energy.charged < 1.01);
  assert.ok(energy.discharged > 0.49 && energy.discharged < 0.51);
  const card = panel._batteryCard("A", true);
  assert.match(card, /Heute geladen/);
  assert.match(card, /Heute entladen/);
  assert.match(card, /Restbedarf/);
  assert.match(card, />Verlust</);
  assert.match(card, /Register/);
  assert.doesNotMatch(card, /Fahrplanlimit/);
  assert.ok(card.indexOf("Verlust") < card.indexOf("Restbedarf"));
});

test("energy flow uses a four-node aggregate power-flow layout", () => {
  const { panel } = createPanel();
  const flow = panel._flowCard();

  assert.match(flow, /flow-route active/);
  assert.equal((flow.match(/flow-dots active/g) || []).length, 3);
  assert.match(flow, /M 500 125 C 525 190 660 214 880 250/);
  assert.match(flow, /M 880 250 C 610 250 400 250 120 250/);
  assert.match(flow, /M 500 405 C 525 310 650 284 880 250/);
  assert.match(flow, /viewBox="0 0 1000 500"/);
  assert.match(flow, /flow-node home/);
  assert.match(flow, /battery-soc/);
  assert.match(flow, /<span>Netz<\/span>/);
  assert.match(flow, /<span>Speicher<\/span>/);
  assert.doesNotMatch(flow, /Netz ·|Speicher ·/);
  assert.doesNotMatch(flow, /Venus A ·/);
  assert.doesNotMatch(flow, /marker-end|flow-arrow-/);
  assert.doesNotMatch(flow, /neutral/);
  assert.doesNotMatch(flow, /animateMotion/);
  const styles = panel._styles();
  assert.match(styles, /@keyframes flow-dots/);
  assert.match(styles, /flow-node\.pv\{left:50%;top:19%;[^}]*flex-direction:column-reverse/);
  assert.match(styles, /flow-node\.battery\{left:50%;top:81%/);
  assert.match(styles, /flow-node\.battery\{top:79%/);
});

test("grid flow direction follows the sign without hysteresis", () => {
  const { panel } = createPanel();

  assert.equal(panel._gridDirection(-1), "export");
  assert.equal(panel._gridDirection(0), "import");
  assert.equal(panel._gridDirection(1), "import");
});

test("zero power keeps routes illuminated but stops moving dots", () => {
  const { panel } = createPanel();
  panel._hass.states["sensor.pv_power"].state = "0";
  panel._hass.states["sensor.grid_power"].state = "0";
  panel._hass.states["sensor.venus_a_power"].state = "0";
  panel._hass.states["sensor.venus_e_power"].state = "0";

  const flow = panel._flowCard();
  assert.equal((flow.match(/flow-route active/g) || []).length, 3);
  assert.equal((flow.match(/flow-dots active/g) || []).length, 0);
  assert.equal((flow.match(/flow-dots idle/g) || []).length, 3);
});

test("calibration status explains empty and active states", () => {
  const { panel } = createPanel();
  panel._hass.states["sensor.speicher_ladelogik_kalibrierung"].attributes.batterie = "";
  panel._hass.states["sensor.speicher_ladelogik_kalibrierung"].attributes.grund = "";
  let card = panel._calibrationCard();

  assert.match(card, /<span>Speicher<\/span><strong>Keiner<\/strong>/);
  assert.match(card, /Kein Kalibrierauftrag aktiv/);
  assert.match(card, /Aktuelle Phase: Bereit/);
  assert.match(card, /Bisher in diesem Kalibrierlauf geladene AC-Energie/);
  assert.match(card, /4,5 h verfügbar · 2 h benötigt/);
  assert.match(card, /kein ausreichendes Fenster/);

  panel._hass.states["sensor.speicher_ladelogik_kalibrierung"].state = "Kalibrierung A: charge";
  panel._hass.states["sensor.speicher_ladelogik_kalibrierung"].attributes.batterie = "A";
  panel._hass.states["sensor.speicher_ladelogik_kalibrierung"].attributes.grund = "Ladung mit 500 W";
  card = panel._calibrationCard();
  assert.match(card, /Venus A/);
  assert.match(card, /Ladung mit 500 W/);
  assert.match(card, /Aktuelle Phase: Kalibrierung A: Kalibrierladung/);
});

test("control settings explain the effect of planning thresholds", () => {
  const { panel } = createPanel();
  const reserves = panel._numberCard("Planungsreserven", "mdi:shield-sun-outline", "planung");
  const classes = panel._numberCard("Tagesklassen", "mdi:weather-partly-cloudy", "tagesklassen");
  const power = panel._numberCard("Ladeleistungen", "mdi:battery-charging", "leistung");
  assert.match(reserves, /Was bedeuten diese Werte\?/);
  assert.match(reserves, /Knappheits-Hysterese/);
  assert.match(reserves, /1,25-mal der Restbedarf/);
  assert.match(classes, /bevorzugten Ladebeginn/);
  assert.match(power, /tatsächliche Verbrauch/);
});

test("frontend element name matches the integration release version", () => {
  assert.equal(panelElementName, "speicher-ladelogik-panel-1-0-3");
  assert.equal(registry.get(panelElementName), Panel);
  assert.equal(registry.has("speicher-ladelogik-panel-1-0-1"), false);
});

test("charts render a combined hover tooltip and clickable sensor legends", () => {
  const { panel } = createPanel();
  const now = Date.now();
  const chart = panel._chart([
    { name: "Solar", color: "#ffcf4a", entityId: "sensor.pv", points: [{ t: now - 1000, v: 1.2 }] },
    { name: "Haus", color: "#8bd8e9", entityId: "sensor.house", points: [{ t: now - 1000, v: 0.8 }] },
  ], { unit: " kW", hours: 1 });

  assert.match(chart, /chart-tooltip/);
  assert.match(chart, /chart-hover-plane/);
  assert.match(chart, /data-entity="sensor\.pv"/);
  assert.doesNotMatch(chart, /chart-hit/);
  assert.equal(panel._chartModels.size, 1);
});

test("source-only updates avoid a full dashboard render", () => {
  const { panel } = createPanel();
  panel._rendered = true;
  panel._syncStateRefs();
  let renders = 0;
  let liveUpdates = 0;
  panel._render = () => { renders += 1; };
  panel._scheduleLiveRefresh = () => { liveUpdates += 1; };

  panel.hass = {
    ...panel._hass,
    states: {
      ...panel._hass.states,
      "sensor.pv_power": { state: "4300", attributes: {} },
    },
  };

  assert.equal(renders, 0);
  assert.equal(liveUpdates, 1);
});

test("every chart keeps its own selected history range", () => {
  const { panel } = createPanel();

  panel._historyHours.overviewPower = 1;
  panel._historyHours.overviewSoc = 6;
  panel._historyHours.batteryA = 12;
  panel._historyHours.batteryE = 24;

  assert.match(panel._historyButtons("overviewPower"), /data-history-hours="1" class="active"/);
  assert.match(panel._historyButtons("overviewSoc"), /data-history-hours="6" class="active"/);
  assert.match(panel._historyButtons("batteryA"), /data-history-hours="12" class="active"/);
  assert.match(panel._historyButtons("batteryE"), /data-history-hours="24" class="active"/);
});

test("configured storage models drive cards, slots, controls, and diagnostics", () => {
  const { panel } = createPanel();
  panel._panel.config.models = ["D"];
  panel._panel.config.sources.soc_d = "sensor.venus_d_soc";
  panel._panel.config.sources.power_d = "sensor.venus_d_power";
  panel._hass.states["sensor.venus_d_soc"] = { state: "70", attributes: {} };
  panel._hass.states["sensor.venus_d_power"] = { state: "0", attributes: {} };

  assert.deepEqual(panel._models(), ["D"]);
  assert.match(panel._batteries(), /Venus D/);
  assert.doesNotMatch(panel._batteries(), /Venus A/);
  assert.doesNotMatch(panel._batteries(), /Venus E/);
  assert.match(panel._planningCard(), /Venus D/);
  assert.match(panel._control(), /Handbetrieb Venus D/);
  assert.match(panel._diagnostics(), /Venus D/);
});

test("A and D show only their configured MPPT sensors", () => {
  const { panel } = createPanel();
  panel._panel.config.sources.mppt_d = ["sensor.venus_d_mppt_1"];
  panel._hass.states["sensor.venus_d_mppt_1"] = {
    state: "812.345",
    attributes: { unit_of_measurement: "W" },
    entity_id: "sensor.venus_d_mppt_1",
  };

  assert.match(panel._mpptDetails("d"), /MPPT 1/);
  assert.match(panel._mpptDetails("d"), /812,35 W/);
  assert.equal(panel._mpptDetails("a"), "");
});
