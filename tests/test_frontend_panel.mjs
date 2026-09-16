import assert from "node:assert/strict";
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

const Panel = registry.get("speicher-ladelogik-panel-1-0-0-rc-8");

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
  assert.match(panel._batteryCard("A", true), /Heute geladen/);
  assert.match(panel._batteryCard("A", true), /Heute entladen/);
});

test("energy flow uses stable curved direction paths without restarted motion", () => {
  const { panel } = createPanel();
  const flow = panel._flowCard();

  assert.match(flow, /Erzeugung &amp; Netz/);
  assert.match(flow, /flow-route active/);
  assert.match(flow, /C 650 74 560 82 500 207/);
  assert.doesNotMatch(flow, /animateMotion/);
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
