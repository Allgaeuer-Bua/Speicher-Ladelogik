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
  assert.match(flow, /flow-dots active/);
  assert.match(flow, /M 500 145 C 525 190 660 214 780 234/);
  assert.match(flow, /M 780 250 C 610 250 400 250 205 250/);
  assert.match(flow, /M 500 355 C 525 310 650 284 780 266/);
  assert.doesNotMatch(flow, /805 (?:231|269)/);
  assert.match(flow, /viewBox="0 0 1000 500"/);
  assert.match(flow, /flow-node home/);
  assert.match(flow, /battery-soc/);
  assert.match(flow, /Speicher ·/);
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

test("grid flow direction stays stable around zero", () => {
  const { panel } = createPanel();

  assert.equal(panel._gridDirection(-50), "export");
  assert.equal(panel._gridDirection(-5), "export");
  assert.equal(panel._gridDirection(5), "export");
  assert.equal(panel._gridDirection(30), "import");
  assert.equal(panel._gridDirection(-5), "import");
  assert.equal(panel._gridDirection(-30), "export");
});

test("frontend element name matches the integration release version", () => {
  assert.equal(panelElementName, "speicher-ladelogik-panel-1-0-0-rc-12");
  assert.equal(registry.get(panelElementName), Panel);
  assert.equal(registry.has("speicher-ladelogik-panel-1-0-0-rc-11"), false);
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
