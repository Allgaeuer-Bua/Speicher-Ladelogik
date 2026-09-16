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

const Panel = registry.get("speicher-ladelogik-panel");

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
      sources: { pv: "sensor.pv_power" },
    },
  };
  panel._hass = {
    states: {
      "switch.speicher_ladelogik_mittagsspitzen": { state: "on", attributes: {} },
      "number.speicher_ladelogik_mindestreserve": { state: "2", attributes: {} },
      "sensor.pv_power": { state: "4200", attributes: {} },
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
