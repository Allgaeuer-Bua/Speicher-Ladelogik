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
const Panel = registry.get("speicher-ladelogik-ae-panel-2-0-0");

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

test("overview has separate SoC values and no daily energy card", () => {
  const p = panel();
  const html = p._overview();
  assert.match(html, /SoC je Speicher/);
  assert.match(html, /Venus A/);
  assert.match(html, /Venus E/);
  assert.doesNotMatch(html, /Energie heute/i);
});

test("storage chart follows pack details and duplicate power chart is gone", () => {
  const p = panel();
  const html = p._batteryCard("A", true);
  assert.ok(html.indexOf("Pack-SoC") < html.indexOf("SoC und Leistungsverlauf"));
  assert.doesNotMatch(html, /AC-Leistung · Laden \/ Entladen/);
});
