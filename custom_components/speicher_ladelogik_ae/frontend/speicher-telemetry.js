/* Venus Speicher-Cockpit 1.0.4 · Standalone Home Assistant card · MIT */
(() => {
  'use strict';
  // Internal read-only analytics module, derived from Venus-Cockpit 1.0.4 (MIT).
  const TAG = 'speicher-ladelogik-telemetry', VERSION = '2.4.0';
  const CSS = "\n    #venus-speicher{color-scheme:inherit;--vs-bg:light-dark(#eef2f6,#10151e);--vs-panel:light-dark(#fff,#1b2330);--vs-raised:light-dark(#f4f6f9,#25303f);--vs-text:light-dark(#172435,#ecf1f8);--vs-sub:light-dark(#526276,#a9b8ca);--vs-line:light-dark(#dfe5ec,#344051);--vs-a:light-dark(#14814f,#80d6a6);--vs-e:light-dark(#007e8c,#70ced8);--vs-net:light-dark(#7a637f,#bcabc6);--vs-good:light-dark(#237347,#8bd5a6);--vs-good-bg:light-dark(#e8f4ed,#22372f);--vs-selected:light-dark(#223449,#e4ebf4);--vs-selected-text:light-dark(#fff,#182333);font:14px/1.45 Arial,Helvetica,sans-serif;color:var(--vs-text);font-variant-numeric:tabular-nums;max-width:1200px;margin:0 auto;container-type:inline-size}\n    #venus-speicher *{box-sizing:border-box}\n    #venus-speicher h2{font-size:26px;line-height:1.2;letter-spacing:-.6px;font-weight:500;margin:0 0 7px}\n    #venus-speicher h3{font-size:15px;font-weight:500;margin:0}\n    #venus-speicher h4{font-size:13px;font-weight:500;margin:0}\n    #venus-speicher p{margin:0}\n    #venus-speicher button,#venus-speicher input,#venus-speicher select{font:inherit}\n    #venus-speicher button{color:inherit}\n    #venus-speicher i{display:inline-flex;width:18px;height:18px;flex:none}\n    #venus-speicher .vs-app{background:var(--vs-bg);padding:24px;border-radius:18px;overflow:hidden}\n    #venus-speicher .vs-heading{display:flex;align-items:flex-start;justify-content:space-between;gap:15px;margin-bottom:20px}\n    #venus-speicher .vs-sub{color:var(--vs-sub);font-size:12px}\n    #venus-speicher .vs-small{color:var(--vs-sub);font-size:11px}\n    #venus-speicher .vs-demo{text-align:right;font-size:11px;color:var(--vs-sub);white-space:nowrap;padding-top:3px}\n    #venus-speicher .vs-demo span{display:block;margin-top:4px}\n    #venus-speicher .vs-totals{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));padding:12px 0 22px;border-bottom:1px solid var(--vs-line);margin-bottom:18px}\n    #venus-speicher .vs-total{padding:0 24px;border-left:1px solid var(--vs-line);min-width:0}\n    #venus-speicher .vs-total:first-child{padding-left:0;border-left:0}\n    #venus-speicher .vs-total:last-child{padding-right:0}\n    #venus-speicher .vs-total>span{font-size:12px;color:var(--vs-sub)}\n    #venus-speicher .vs-total strong{display:block;font-size:30px;letter-spacing:-.8px;font-weight:500;margin-top:5px;white-space:nowrap}\n    #venus-speicher .vs-total strong small{font-weight:400;font-size:13px;color:var(--vs-sub);letter-spacing:0}\n    #venus-speicher .vs-total p{font-size:11px;color:var(--vs-sub);margin-top:4px}\n    #venus-speicher .vs-devices{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin-bottom:18px;align-items:start}\n    #venus-speicher .vs-panel{background:var(--vs-panel);border-radius:12px;padding:18px;min-width:0}\n    #venus-speicher .vs-head{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}\n    #venus-speicher .vs-device-name{display:flex;align-items:center;gap:8px}\n    #venus-speicher .vs-device-name i{color:var(--vs-color)}\n    #venus-speicher .vs-status{font-size:11px;color:var(--vs-sub);display:flex;align-items:center;gap:5px}\n    #venus-speicher .vs-status i{width:14px;height:14px}\n    #venus-speicher .vs-device-main{display:flex;align-items:end;justify-content:space-between;gap:16px;margin:20px 0 12px}\n    #venus-speicher .vs-soc{font-size:37px;letter-spacing:-1.3px;line-height:1.1;font-weight:500}\n    #venus-speicher .vs-soc small{font-size:15px;letter-spacing:0;color:var(--vs-sub);font-weight:400}\n    #venus-speicher .vs-power{text-align:right}\n    #venus-speicher .vs-power strong{font-size:23px;display:block;font-weight:500;letter-spacing:-.5px}\n    #venus-speicher .vs-power strong small{font-size:12px;font-weight:400;letter-spacing:0;color:var(--vs-sub)}\n    #venus-speicher .vs-power>span{display:flex;justify-content:flex-end;align-items:center;gap:4px;font-size:11px;color:var(--vs-sub);margin-top:3px}\n    #venus-speicher .vs-power i{width:13px;height:13px}\n    #venus-speicher .vs-track{height:8px;border-radius:8px;background:var(--vs-raised);overflow:hidden}\n    #venus-speicher .vs-track>span{display:block;height:100%;border-radius:8px;background:var(--vs-color)}\n    #venus-speicher .vs-capacity{display:flex;justify-content:space-between;gap:12px;margin-top:8px;font-size:11px;color:var(--vs-sub)}\n    #venus-speicher .vs-device-values{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:18px;padding-top:15px;border-top:1px solid var(--vs-line)}\n    #venus-speicher .vs-device-values strong{display:block;font-size:16px;font-weight:500;margin-top:4px}\n    #venus-speicher .vs-device-values strong small{font-size:11px;color:var(--vs-sub);font-weight:400}\n    #venus-speicher .vs-pack-strip{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-top:17px;min-height:44px}\n    #venus-speicher .vs-pack-head{display:flex;justify-content:space-between;gap:8px;color:var(--vs-sub);font-size:11px;margin-bottom:6px}\n    #venus-speicher .vs-pack-strip .vs-track{height:4px}\n    #venus-speicher .vs-temperature-strip{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:17px;min-height:44px}\n    #venus-speicher .vs-temperature-strip>div>span{display:block;font-size:11px;color:var(--vs-sub)}\n    #venus-speicher .vs-temperature-strip strong{display:block;font-size:13px;font-weight:400;margin-top:4px}\n    #venus-speicher details{color:var(--vs-sub);font-size:12px}\n    #venus-speicher summary{padding:9px 0;min-height:36px}\n    #venus-speicher .vs-device-details{border-top:1px solid var(--vs-line);margin-top:12px;padding-top:3px}\n    #venus-speicher .vs-device-details+details{margin-top:0;border-top:0;padding-top:0}\n    #venus-speicher .vs-settings{display:grid;gap:16px;padding:8px 0 12px}\n    #venus-speicher .vs-setting label{display:flex;justify-content:space-between;gap:12px;margin-bottom:8px;align-items:center}\n    #venus-speicher .vs-setting output{color:var(--vs-text)}\n    #venus-speicher select{color:var(--vs-text);background:var(--vs-raised);border:1px solid var(--vs-line);border-radius:7px;padding:7px 10px;font-size:12px;max-width:100%}\n    #venus-speicher .vs-setting select{width:100%}\n    #venus-speicher input[type=\"range\"]{width:100%;accent-color:var(--vs-color);margin:0;display:block}\n    #venus-speicher .vs-details-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:15px 12px;padding:9px 0 14px}\n    #venus-speicher .vs-details-grid span{display:block;color:var(--vs-sub);font-size:11px}\n    #venus-speicher .vs-details-grid strong{display:block;color:var(--vs-text);font-size:13px;font-weight:400;margin-top:4px;overflow-wrap:anywhere}\n    #venus-speicher .vs-fan{display:flex;justify-content:space-between;align-items:center;gap:14px;border-top:1px solid var(--vs-line);padding:12px 0 7px}\n    #venus-speicher .vs-fan label{display:flex;gap:7px;align-items:center}\n    #venus-speicher .vs-fan input{width:18px;height:18px;accent-color:var(--vs-color)}\n    #venus-speicher .vs-action{background:var(--vs-selected);color:var(--vs-selected-text);border:0;border-radius:7px;padding:8px 12px;min-height:34px;font-size:12px}\n    #venus-speicher .vs-save-row{display:flex;align-items:center;justify-content:space-between;gap:12px;min-height:34px}\n    #venus-speicher .vs-save-row span{font-size:11px;color:var(--vs-sub)}\n    #venus-speicher .vs-chart-panel{margin-bottom:18px}\n    #venus-speicher .vs-tabs{display:flex;gap:2px;background:var(--vs-raised);border-radius:7px;padding:3px;flex-wrap:wrap}\n    #venus-speicher .vs-tabs button{font-size:12px;background:transparent;border:0;border-radius:5px;padding:6px 9px;min-height:31px;color:var(--vs-sub)}\n    #venus-speicher .vs-tabs button[aria-pressed=\"true\"]{background:var(--vs-panel);color:var(--vs-text)}\n    #venus-speicher .vs-chart-context{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-top:12px;min-height:31px}\n    #venus-speicher .vs-chart-context>span{color:var(--vs-sub);font-size:12px}\n    #venus-speicher .vs-chart-context select{max-width:45%}\n    #venus-speicher .vs-chart{position:relative;width:100%;margin-top:8px}\n    #venus-speicher .vs-chart svg{display:block;width:100%;overflow:visible}\n    #venus-speicher .vs-chart text{font:11px Arial,Helvetica,sans-serif;fill:var(--vs-sub)}\n    #venus-speicher .vs-legend{display:flex;justify-content:center;gap:19px;flex-wrap:wrap;margin-top:9px}\n    #venus-speicher .vs-legend button{border:0;background:none;padding:4px 0;display:flex;gap:6px;align-items:center;font-size:11px;color:var(--vs-sub)}\n    #venus-speicher .vs-legend button[aria-pressed=\"false\"]{opacity:.45;text-decoration:line-through}\n    #venus-speicher .vs-swatch{display:inline-block;width:17px;height:3px;background:var(--vs-color);border-radius:2px}\n    #venus-speicher .vs-legend button[data-dash=\"true\"] .vs-swatch{background:repeating-linear-gradient(to right,var(--vs-color) 0 5px,transparent 5px 8px)}\n    #venus-speicher .vs-tooltip{position:absolute;z-index:4;pointer-events:none;min-width:155px;max-width:100%;background:var(--vs-raised);border:1px solid var(--vs-line);border-radius:8px;padding:9px 11px;box-shadow:0 4px 18px #0002;font-size:12px}\n    #venus-speicher .vs-tooltip strong{display:block;font-weight:500;margin-bottom:5px}\n    #venus-speicher .vs-tip-row{display:flex;justify-content:space-between;gap:18px;margin-top:3px}\n    #venus-speicher .vs-lower{display:grid;grid-template-columns:1fr 1fr;gap:16px;align-items:start}\n    #venus-speicher .vs-table{width:100%;border-collapse:collapse;font-size:12px;margin-top:15px;text-align:left}\n    #venus-speicher .vs-table th{font-size:11px;font-weight:400;color:var(--vs-sub);padding:0 0 10px}\n    #venus-speicher .vs-table td{padding:11px 0;border-top:1px solid var(--vs-line);font-weight:400;white-space:nowrap}\n    #venus-speicher .vs-table th:not(:first-child),#venus-speicher .vs-table td:not(:first-child){text-align:right;padding-left:7px}\n    #venus-speicher .vs-table .vs-sum td{font-weight:500}\n    #venus-speicher .vs-device-dot{width:7px;height:7px;border-radius:50%;display:inline-block;background:var(--vs-color);margin-right:6px}\n    #venus-speicher .vs-table-note{font-size:11px;color:var(--vs-sub);margin-top:9px}\n    #venus-speicher .vs-cell-details{margin-top:10px;border-top:1px solid var(--vs-line);padding-top:4px}\n    #venus-speicher .vs-cell-tools{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-top:9px}\n    #venus-speicher .vs-cell-chart{margin-top:10px}\n    #venus-speicher .vs-cell-chart svg{width:100%;display:block}\n    #venus-speicher .vs-cell-chart text{font:11px Arial,Helvetica,sans-serif;fill:var(--vs-sub)}\n    #venus-speicher .vs-cell-values{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:13px 10px;margin-top:16px}\n    #venus-speicher .vs-cell-values>div{min-width:0}\n    #venus-speicher .vs-cell-values span{display:block;font-size:11px;color:var(--vs-sub);margin-bottom:4px}\n    #venus-speicher .vs-cell-values strong{display:inline-flex;align-items:baseline;gap:4px;font-weight:400;font-size:13px;color:var(--vs-text);white-space:nowrap}\n    #venus-speicher .vs-cell-values small{font-weight:400;font-size:11px;color:var(--vs-sub)}\n    #venus-speicher .vs-tooltip[data-cells=\"true\"]{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:3px 12px;width:300px;min-width:0}\n    #venus-speicher .vs-tooltip[data-cells=\"true\"] strong{grid-column:1/-1}\n    #venus-speicher .vs-tooltip[data-cells=\"true\"] .vs-tip-row{font-size:11px;gap:5px;white-space:nowrap}\n    @container(max-width:560px){#venus-speicher .vs-total strong small{display:inline;margin-top:0}#venus-speicher .vs-total strong{font-size:24px}#venus-speicher .vs-cell-values{grid-template-columns:repeat(4,minmax(0,1fr))}}\n    @container(max-width:360px){#venus-speicher .vs-total strong{font-size:21px;letter-spacing:-.5px}#venus-speicher .vs-cell-values{grid-template-columns:repeat(3,minmax(0,1fr))}}\n    #venus-speicher .vs-bottom{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-top:17px;font-size:11px;color:var(--vs-sub);flex-wrap:wrap}\n    #venus-speicher [hidden]{display:none!important}\n    #venus-speicher .vs-sr{position:absolute;width:1px;height:1px;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap}\n    @container(max-width:760px){#venus-speicher .vs-app{padding:20px 18px}#venus-speicher .vs-lower{grid-template-columns:1fr}#venus-speicher .vs-total{padding:0 16px}#venus-speicher .vs-total strong{font-size:27px}#venus-speicher .vs-chart-panel>.vs-head{align-items:flex-start}}\n    @container(max-width:560px){#venus-speicher .vs-app{padding:18px 12px}#venus-speicher h2{font-size:24px}#venus-speicher .vs-heading{margin-bottom:17px}#venus-speicher .vs-heading .vs-demo{max-width:100px;white-space:normal}#venus-speicher .vs-devices{grid-template-columns:1fr;gap:13px}#venus-speicher .vs-panel{padding:16px 13px}#venus-speicher .vs-total{padding:0 9px}#venus-speicher .vs-total>span{font-size:11px;display:block;min-height:32px}#venus-speicher .vs-total strong{font-size:24px}#venus-speicher .vs-total strong small{font-size:11px;display:inline;margin-top:0}#venus-speicher .vs-totals{padding:9px 0 17px;margin-bottom:15px}#venus-speicher .vs-total p{font-size:11px}#venus-speicher .vs-heading>.vs-demo{font-size:11px}#venus-speicher .vs-tabs button{padding:6px 8px}#venus-speicher .vs-lower{gap:13px}#venus-speicher .vs-device-main{margin-top:18px}}\n    @container(max-width:360px){#venus-speicher .vs-total strong{font-size:22px}#venus-speicher .vs-total{padding:0 7px}#venus-speicher .vs-total:first-child{padding-left:0}#venus-speicher .vs-total:last-child{padding-right:0}#venus-speicher .vs-details-grid{grid-template-columns:repeat(2,minmax(0,1fr))}#venus-speicher .vs-head{gap:10px}#venus-speicher .vs-table{font-size:11px}}\n    @media(pointer:coarse){#venus-speicher .vs-tabs button,#venus-speicher .vs-legend button,#venus-speicher summary,#venus-speicher .vs-action{min-height:44px}#venus-speicher input,#venus-speicher select{font-size:16px}#venus-speicher input[type=\"range\"]{height:32px}}\n    @media(prefers-reduced-motion:reduce){#venus-speicher *{transition:none!important;animation:none!important}}\n  \n:host{display:block;container-type:inline-size;min-width:0}\nha-card{display:block;background:transparent;border:0;box-shadow:none;overflow:visible}\n#venus-speicher{max-width:none;font-family:var(--paper-font-body1_-_font-family,Arial,Helvetica,sans-serif)}\n#venus-speicher .vs-app{border-radius:var(--ha-card-border-radius,18px)}\n#venus-speicher button,#venus-speicher summary,#venus-speicher select{cursor:pointer}\n#venus-speicher button:disabled,#venus-speicher input:disabled,#venus-speicher select:disabled{cursor:default;opacity:.6}\n#venus-speicher ha-icon{--mdc-icon-size:18px;width:18px;height:18px;color:var(--vs-color);flex:none}\n#venus-speicher .vs-total strong small{display:inline!important;margin:0;white-space:nowrap}\n#venus-speicher .vs-total strong{white-space:nowrap}\n#venus-speicher .vs-total strong>span{white-space:nowrap}\n#venus-speicher .vs-device-values strong,#venus-speicher .vs-capacity>span{overflow-wrap:anywhere}\n#venus-speicher .vs-settings .vs-control-range{display:block;font-size:11px;color:var(--vs-sub);margin-top:6px}\n#venus-speicher .vs-save-row{align-items:flex-start}\n#venus-speicher .vs-save-row>span{overflow-wrap:anywhere;min-width:0}\n#venus-speicher .vs-save-row button{flex:none}\n#venus-speicher [data-error=\"true\"]{color:light-dark(#b33434,#f3a6a6)}\n#venus-speicher .vs-control-message{font-size:11px;overflow-wrap:anywhere;margin-top:5px}\n#venus-speicher .vs-control-message:empty{display:none}\n#venus-speicher .vs-history-note{margin-top:12px;overflow-wrap:anywhere}\n#venus-speicher .vs-history-note:empty{display:none}\n#venus-speicher .vs-data-notes{margin-top:15px;overflow-wrap:anywhere}\n#venus-speicher .vs-data-notes ul{padding-left:20px}\n#venus-speicher .vs-data-notes li{margin:7px 0}\n#venus-speicher .vs-bottom button{border:0;background:transparent;font:inherit;color:inherit;padding:7px 0;text-decoration:underline;text-underline-offset:3px;min-height:36px}\n#venus-speicher .vs-details-grid{min-width:0}\n#venus-speicher .vs-details-grid>div{min-width:0;overflow-wrap:anywhere}\n#venus-speicher{--vs-chart-1:light-dark(#2864c5,#88baff);--vs-chart-2:light-dark(#b65c00,#ffbf73);--vs-chart-3:light-dark(#8954b5,#caa5f2);--vs-chart-4:light-dark(#237a45,#93d7aa);--vs-chart-5:light-dark(#c33f52,#ff9ca8);--vs-chart-6:light-dark(#0b7f9a,#80d4eb);--vs-chart-7:light-dark(#827400,#d8cc6c);--vs-chart-8:light-dark(#ad367c,#efa1d3);--vs-chart-9:light-dark(#8a5b31,#d9b08c);--vs-chart-10:light-dark(#493fa7,#b4aaff);--vs-chart-11:light-dark(#13654f,#77cbb3);--vs-chart-12:light-dark(#b94e31,#ffab8e);--vs-chart-13:light-dark(#5b6473,#c3cad5)}\n#venus-speicher .vs-legend .vs-swatch{width:24px;height:10px;display:block;flex:none;border-radius:0}\n#venus-speicher .vs-legend button .vs-swatch,#venus-speicher .vs-legend button[data-dash=\"true\"] .vs-swatch{background:none}\n#venus-speicher .vs-tip-name{display:inline-flex;align-items:center;gap:4px}\n#venus-speicher .vs-tip-dot{display:inline-block;width:7px;height:7px;border-radius:50%;flex:none}\n@container(max-width:360px){#venus-speicher .vs-total strong{font-size:21px;letter-spacing:-.5px}}\n@media(pointer:coarse){#venus-speicher .vs-bottom button{min-height:44px}}\n/* Theme tokens are supplied by each card's generator. */\n#venus-speicher button.entity-info{appearance:none;border:0;border-radius:3px;background:transparent;color:inherit;font:inherit;line-height:inherit;letter-spacing:inherit;text-align:inherit;padding:3px 0;margin:-3px 0;display:inline;cursor:pointer;max-width:100%;vertical-align:baseline}\n#venus-speicher button.entity-info:hover{text-decoration:underline;text-underline-offset:3px}\n#venus-speicher button.entity-info:focus-visible{outline:2px solid var(--vs-a);outline-offset:3px}\n#venus-speicher dialog.entity-sources{color-scheme:inherit;color:var(--vs-text);background:var(--vs-panel);border:1px solid var(--vs-line);border-radius:14px;box-shadow:0 14px 60px #0004;padding:20px;width:min(480px,calc(100vw - 24px));max-width:calc(100vw - 24px);max-height:85dvh;overflow:auto;overflow-wrap:anywhere;font:inherit}\n#venus-speicher dialog.entity-sources::backdrop{background:#0007}\n#venus-speicher .entity-sources h3{font-size:18px;margin:0 0 8px}\n#venus-speicher .entity-sources p{font-size:13px;color:var(--vs-sub);margin:0 0 16px}\n#venus-speicher .entity-sources button.entity-source{display:block;width:100%;background:var(--vs-raised);color:inherit;border:1px solid var(--vs-line);border-radius:8px;text-align:left;font:inherit;padding:10px 12px;margin:8px 0;cursor:pointer}\n#venus-speicher .entity-source strong,#venus-speicher .entity-source small,#venus-speicher .entity-source span{display:block}\n#venus-speicher .entity-source strong{font-size:13px;font-weight:600}\n#venus-speicher .entity-source small{font-size:11px;color:var(--vs-sub);margin:3px 0;overflow-wrap:anywhere}\n#venus-speicher .entity-source span{font-size:13px}\n#venus-speicher .entity-sources-close{display:block;margin:15px 0 0 auto;background:var(--vs-raised);color:inherit;border:1px solid var(--vs-line);border-radius:7px;padding:9px 15px;min-height:40px;font:inherit;cursor:pointer}\n#venus-speicher .entity-sources button:focus-visible{outline:2px solid var(--vs-a);outline-offset:2px}\n\n#venus-speicher .vs-setting-info{appearance:none;display:flex;align-items:center;gap:10px;width:100%;text-align:left;color:var(--vs-sub);font:inherit;background:none;border:0;border-radius:5px;margin:0 0 6px;padding:4px 0;min-height:32px;cursor:pointer}\n#venus-speicher .vs-setting-info>span{flex:1;min-width:0}\n#venus-speicher .vs-setting-info output{color:var(--vs-text);white-space:nowrap}\n#venus-speicher .vs-setting-info ha-icon{--mdc-icon-size:14px;width:14px;height:14px;opacity:.7}\n#venus-speicher .vs-setting-info:hover>span{text-decoration:underline;text-underline-offset:3px}\n#venus-speicher .vs-setting-info:focus-visible{outline:2px solid var(--vs-color);outline-offset:3px}\n#venus-speicher .vs-device-values>div>button.entity-info{display:block}\n#venus-speicher .vs-chart-context{flex-wrap:wrap;align-items:flex-start}\n#venus-speicher .vs-chart-options{display:flex;align-items:center;justify-content:flex-end;gap:8px;flex-wrap:wrap;max-width:100%;margin-left:auto}\n#venus-speicher .vs-chart-options>select{max-width:100%}\n#venus-speicher .vs-range-control{display:flex;align-items:center;gap:8px;color:var(--vs-sub);font-size:11px;max-width:100%}\n#venus-speicher .vs-range-control select{max-width:100%;min-width:110px}\n#venus-speicher .vs-pack-charts{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin-top:18px;align-items:start}\n#venus-speicher .vs-pack-charts .vs-chart-panel{margin-bottom:0}\n#venus-speicher .vs-pack-caption{margin-top:12px}\n#venus-speicher .vs-pack-charts .vs-legend{gap:6px 14px}\n@container(max-width:760px){#venus-speicher .vs-pack-charts{grid-template-columns:minmax(0,1fr);gap:13px}}\n@container(max-width:480px){#venus-speicher .vs-chart-options{width:100%;justify-content:flex-start;margin-left:0}#venus-speicher .vs-chart-panel .vs-range-control{margin-left:auto}#venus-speicher .vs-chart-context .vs-range-control{margin-left:0}}\n@media(pointer:coarse){#venus-speicher .vs-setting-info{min-height:44px}#venus-speicher .vs-range-control select{min-height:44px}}\n#venus-speicher .vs-date-range{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr) auto;gap:6px 10px;align-items:end;margin:14px 0 8px;min-width:0}\n#venus-speicher .vs-date-range>label{display:block;min-width:0;font-size:11px;color:var(--vs-sub)}\n#venus-speicher .vs-date-range input{display:block;appearance:auto;width:100%;min-width:0;max-width:100%;margin-top:5px;border:1px solid var(--vs-line);border-radius:7px;padding:8px;color:var(--vs-text);background:var(--vs-raised);font:inherit;font-size:12px;min-height:36px}\n#venus-speicher .vs-date-range button{min-height:36px}\n#venus-speicher .vs-date-zone,#venus-speicher .vs-date-feedback{grid-column:1/-1;overflow-wrap:anywhere}\n#venus-speicher .vs-date-feedback:empty{display:none}\n#venus-speicher .vs-date-range input:focus-visible{outline:2px solid var(--vs-a);outline-offset:2px}\n@container(max-width:1100px){#venus-speicher .vs-pack-charts .vs-date-range{grid-template-columns:minmax(0,1fr) minmax(0,1fr)}#venus-speicher .vs-pack-charts .vs-date-range>button{grid-column:2;justify-self:end}}\n@container(max-width:480px){#venus-speicher .vs-date-range{grid-template-columns:minmax(0,1fr)}#venus-speicher .vs-pack-charts .vs-date-range{grid-template-columns:minmax(0,1fr)}#venus-speicher .vs-date-range>button,#venus-speicher .vs-pack-charts .vs-date-range>button{grid-column:1;justify-self:end}#venus-speicher .vs-date-range input{font-size:16px;min-height:44px}#venus-speicher .vs-date-range button{min-height:44px}}\n@media(pointer:coarse){#venus-speicher .vs-date-range input{font-size:16px;min-height:44px}#venus-speicher .vs-date-range button{min-height:44px}}\n";
  const DEFAULTS = {
  "title": "Dein Speicher-Cockpit",
  "theme": "auto",
  "enable_controls": true,
  "history_hours": 24,
  "history_refresh_seconds": 120,
  "history_max_points": 720,
  "power_deadband_w": 10,
  "capacity_kwh": {
    "a": 3.66,
    "e": 4.56
  },
  "power_sign": {
    "a": 1,
    "e": 1
  },
  "grid_power_sign": 1,
  "colors": {
    "a": "#14814f",
    "e": "#007e8c"
  },
  "entities": {
    "a_power": "sensor.marstek_venus_a_ac_leistung_invertiert",
    "a_ac_raw": "sensor.marstek_venus_a_ac_leistung",
    "a_dc": "sensor.marstek_venus_a_batterieleistung",
    "a_voltage": "sensor.marstek_venus_a_batteriespannung",
    "a_current": "sensor.marstek_venus_a_batteriestrom",
    "a_soc": "sensor.marstek_venus_a_soc_batterie",
    "a_temperature": "sensor.marstek_venus_a_innentemperatur",
    "a_mos1": "sensor.marstek_venus_a_interne_mos1_temperatur",
    "a_mos2": "sensor.marstek_venus_a_interne_mos2_temperatur",
    "a_status": "sensor.marstek_venus_a_wechselrichter_status",
    "a_usable": "sensor.venus_a_nutzbare_kapazitat",
    "a_load": "sensor.marstek_venus_a_venus_a_auslastung",
    "a_eta_min": "sensor.venus_a_zeit_bis_soc_min",
    "a_eta_max": "sensor.venus_a_zeit_bis_soc_max",
    "a_mode": "select.marstek_venus_a_benutzer_modus",
    "a_charge_limit": "number.marstek_venus_a_maximale_ladeleistung",
    "a_discharge_limit": "number.marstek_venus_a_maximale_entladeleistung",
    "a_fan": "switch.lufter_venus_a",
    "a_efficiency": "sensor.venus_a_ac_wirkungsgrad",
    "a_charge_today": "sensor.marstek_venus_a_tagliche_ladeenergie",
    "a_discharge_today": "sensor.marstek_venus_a_tagliche_entladeenergie",
    "a_charge_month": "sensor.marstek_venus_a_monatliche_ladeenergie",
    "a_discharge_month": "sensor.marstek_venus_a_monatliche_entladeenergie",
    "a_charge_total": "sensor.marstek_venus_a_venus_a_gesamte_ladeenergie",
    "a_discharge_total": "sensor.marstek_venus_a_venus_a_gesamte_entladeenergie",
    "a_p1_soc": "sensor.marstek_venus_a_soc_batteriepack_1",
    "a_p2_soc": "sensor.marstek_venus_a_soc_batteriepack_2",
    "a_p1_drift": "sensor.venus_a_pack_1_zelldrift",
    "a_p2_drift": "sensor.venus_a_pack_2_zelldrift",
    "e_power": "sensor.marstek_venus_e_venus_e_ac_leistung_invertiert",
    "e_ac_raw": "sensor.marstek_venus_e_ac_leistung",
    "e_dc": "sensor.marstek_venus_e_dc_leistung",
    "e_voltage": "sensor.marstek_venus_e_dc_spannung",
    "e_current": "sensor.marstek_venus_e_dc_strom",
    "e_soc": "sensor.marstek_venus_e_soc",
    "e_temperature": "sensor.marstek_venus_e_interne_temperatur",
    "e_mos1": "sensor.marstek_venus_e_mos1_interne_temperatur",
    "e_mos2": "sensor.marstek_venus_e_mos2_interne_temperatur",
    "e_status": "sensor.marstek_venus_e_wechselrichter_status",
    "e_usable": "sensor.venus_e_nutzbare_kapazitat",
    "e_load": "sensor.marstek_venus_e_venus_e_auslastung",
    "e_eta_min": "sensor.venus_e_zeit_bis_soc_min",
    "e_eta_max": "sensor.venus_e_zeit_bis_soc_max",
    "e_mode": "select.marstek_venus_e_betriebsmodus",
    "e_charge_limit": "number.marstek_venus_e_ladeleistung",
    "e_discharge_limit": "number.marstek_venus_e_entladeleistung",
    "e_fan": "switch.haus_lufter_wr_und_speicher",
    "e_efficiency": "sensor.venus_e_ac_wirkungsgrad",
    "e_charge_today": "sensor.marstek_venus_e_tagliche_ladeenergie",
    "e_discharge_today": "sensor.marstek_venus_e_tagliche_entladeenergie",
    "e_charge_month": "sensor.marstek_venus_e_monatliche_ladeenergie",
    "e_discharge_month": "sensor.marstek_venus_e_monatliche_entladeenergie",
    "e_charge_total": "sensor.marstek_venus_e_gesamte_ladung",
    "e_discharge_total": "sensor.marstek_venus_e_gesamt_entladen",
    "e_drift": "sensor.marstek_venus_e_zellspannungs_differenz",
    "e_cell_min": "sensor.marstek_venus_e_min_zellspannung",
    "e_cell_max": "sensor.marstek_venus_e_max_zellspannung",
    "grid_power": "sensor.stromzahler_leistung",
    "a_reference": "input_number.batterie_gesamt_referenzkapazitaet_a",
    "e_reference": "input_number.batterie_gesamt_referenzkapazitaet_e",
    "reference_ready": "input_boolean.batterie_gesamt_initialisiert",
    "sign_setting": "input_boolean.batterie_gesamt_positive_leistung_ist_entladen",
    "a_p1_cell_1": "sensor.marstek_venus_a_batteriepack_1_zelle_1_spannung",
    "a_p1_cell_2": "sensor.marstek_venus_a_batteriepack_1_zelle_2_spannung",
    "a_p1_cell_3": "sensor.marstek_venus_a_batteriepack_1_zelle_3_spannung",
    "a_p1_cell_4": "sensor.marstek_venus_a_batteriepack_1_zelle_4_spannung",
    "a_p1_cell_5": "sensor.marstek_venus_a_batteriepack_1_zelle_5_spannung",
    "a_p1_cell_6": "sensor.marstek_venus_a_batteriepack_1_zelle_6_spannung",
    "a_p1_cell_7": "sensor.marstek_venus_a_batteriepack_1_zelle_7_spannung",
    "a_p1_cell_8": "sensor.marstek_venus_a_batteriepack_1_zelle_8_spannung",
    "a_p1_cell_9": "sensor.marstek_venus_a_batteriepack_1_zelle_9_spannung",
    "a_p1_cell_10": "sensor.marstek_venus_a_batteriepack_1_zelle_10_spannung",
    "a_p1_cell_11": "sensor.marstek_venus_a_batteriepack_1_zelle_11_spannung",
    "a_p1_cell_12": "sensor.marstek_venus_a_batteriepack_1_zelle_12_spannung",
    "a_p1_cell_13": "sensor.marstek_venus_a_batteriepack_1_zelle_13_spannung",
    "a_p2_cell_1": "sensor.marstek_venus_a_batteriepack_2_zelle_1_spannung",
    "a_p2_cell_2": "sensor.marstek_venus_a_batteriepack_2_zelle_2_spannung",
    "a_p2_cell_3": "sensor.marstek_venus_a_batteriepack_2_zelle_3_spannung",
    "a_p2_cell_4": "sensor.marstek_venus_a_batteriepack_2_zelle_4_spannung",
    "a_p2_cell_5": "sensor.marstek_venus_a_batteriepack_2_zelle_5_spannung",
    "a_p2_cell_6": "sensor.marstek_venus_a_batteriepack_2_zelle_6_spannung",
    "a_p2_cell_7": "sensor.marstek_venus_a_batteriepack_2_zelle_7_spannung",
    "a_p2_cell_8": "sensor.marstek_venus_a_batteriepack_2_zelle_8_spannung",
    "a_p2_cell_9": "sensor.marstek_venus_a_batteriepack_2_zelle_9_spannung",
    "a_p2_cell_10": "sensor.marstek_venus_a_batteriepack_2_zelle_10_spannung",
    "a_p2_cell_11": "sensor.marstek_venus_a_batteriepack_2_zelle_11_spannung",
    "a_p2_cell_12": "sensor.marstek_venus_a_batteriepack_2_zelle_12_spannung",
    "a_p2_cell_13": "sensor.marstek_venus_a_batteriepack_2_zelle_13_spannung"
  }
};
  // Included in each standalone card; no extra resource is required.
  function entityInfoButton(host, keys, label, content) {
    const button = document.createElement('button');
    button.type = 'button'; button.className = 'entity-info';
    button.setAttribute('aria-label', label + ' · Entität oder Quellen öffnen');
    button.title = 'Entität oder Quellen öffnen';
    if (content instanceof Node) button.append(content); else button.textContent = content;
    button.addEventListener('click', () => openEntityInfo(host, typeof keys === 'function' ? keys() : keys, label));
    return button;
  }
  function bindEntityInfo(host, selector, keys, label) {
    const value = host.shadowRoot.querySelector(selector);
    if (!value || value.parentElement?.classList.contains('entity-info')) return;
    const button = entityInfoButton(host, keys, label, '');
    value.replaceWith(button); button.append(value);
  }
  function openEntityInfo(host, keys, label) {
    const ids = [...new Set(keys.map(key => host._config.entities[key]).filter(Boolean))];
    const moreInfo = entityId => host.dispatchEvent(new CustomEvent('hass-more-info', {
      detail: { entityId }, bubbles: true, composed: true
    }));
    host._infoDialog?.close();
    if (ids.length === 1) { moreInfo(ids[0]); return; }
    const dialog = document.createElement('dialog'); dialog.className = 'entity-sources';
    host._infoDialog = dialog;
    const heading = document.createElement('h3'); heading.textContent = label;
    heading.id = 'entity-sources-title'; dialog.setAttribute('aria-labelledby', heading.id);
    const note = document.createElement('p');
    note.textContent = ids.length ? 'Berechneter oder zusammengesetzter Wert. Quelle auswählen, um die Entität zu öffnen.' : 'Keine Entität zugeordnet. Dieser Wert stammt aus der Kartenkonfiguration.';
    dialog.append(heading, note);
    for (const id of ids) {
      const state = host.hass?.states?.[id], button = document.createElement('button');
      button.type = 'button'; button.className = 'entity-source'; button.dataset.entityId = id;
      const name = document.createElement('strong'), identity = document.createElement('small'), value = document.createElement('span');
      name.textContent = state?.attributes?.friendly_name || id;
      identity.textContent = id;
      value.textContent = state ? String(state.state) + (state.attributes?.unit_of_measurement ? ' ' + state.attributes.unit_of_measurement : '') : 'Nicht verfügbar';
      button.append(name, identity, value); button.addEventListener('click', () => { dialog.close(); moreInfo(id); });
      dialog.append(button);
    }
    const close = document.createElement('button'); close.type = 'button'; close.className = 'entity-sources-close'; close.textContent = 'Schließen';
    close.addEventListener('click', () => dialog.close()); dialog.append(close);
    dialog.addEventListener('click', event => { if (event.target === dialog) { const r = dialog.getBoundingClientRect(); if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) dialog.close(); } });
    dialog.addEventListener('close', () => { dialog.remove(); if (host._infoDialog === dialog) host._infoDialog = null; }, { once: true });
    host.shadowRoot.querySelector('ha-card > div').append(dialog); dialog.showModal();
  }

  const DEVICES = [{id:'a',name:'Venus A',color:'var(--vs-a)'},{id:'e',name:'Venus E',color:'var(--vs-e)'}];
  const MODES = {power:'Leistung',soc:'SoC',efficiency:'Wirkungsgrad',temperature:'Temperaturen',drift:'Zelldrift',cells:'Zellspannungen'};
  const NS = 'http://www.w3.org/2000/svg';
  const HISTORY_RANGES = [1,6,12,24,48,168];
  let CARD_COUNT = 0;
  const valid = n => typeof n === 'number' && Number.isFinite(n);
  const num = raw => raw === null || raw === undefined || String(raw).trim() === '' ? null : (Number.isFinite(Number(raw)) ? Number(raw) : null);
  const fmt = (n,d=1) => valid(n) ? n.toLocaleString('de-DE',{minimumFractionDigits:d,maximumFractionDigits:d}) : '–';
  const sum = values => values.every(valid) ? values.reduce((a,b)=>a+b,0) : null;
  const available = state => !!state && !['unknown','unavailable','none',''].includes(String(state.state).trim().toLowerCase());
  function convert(value,kind,unit) {
    if (!valid(value)) return null;
    const u=String(unit||'').toLowerCase().replace(/\s/g,'');
    if (kind==='temperature') return ['°c','c','celsius'].includes(u) ? value : ['°f','f'].includes(u) ? (value-32)*5/9 : u==='k' ? value-273.15 : null;
    const scale=({power:{w:.001,kw:1,mw:1000},energy:{wh:.001,kwh:1,mwh:1000},voltage:{v:1,mv:.001,kv:1000},current:{a:1,ma:.001},drift:{v:1000,mv:1},percent:{'%':1,'':1}}[kind]||{})[u];
    return scale===undefined ? null : value*scale;
  }
  function node(tag,attrs={},text) { const n=document.createElementNS(NS,tag);Object.entries(attrs).forEach(([k,v])=>n.setAttribute(k,String(v)));if(text!==undefined)n.textContent=text;return n; }
  function pathFor(points,x,y) { let pen=false,s='';for(const p of points){if(!valid(p.v)){pen=false;continue;}s+=`${pen?'L':'M'}${x(p.t).toFixed(2)},${y(p.v).toFixed(2)} `;pen=true;}return s; }
  function thin(points,limit) {
    if(points.length<=limit)return points;
    const size=Math.ceil(points.length/Math.max(1,Math.floor(limit/5))),out=[];
    for(let i=0;i<points.length;i+=size){const b=points.slice(i,i+size),good=b.filter(p=>valid(p.v)),marks=[b[0],b[b.length-1]];if(good.length)marks.push(good.reduce((a,c)=>a.v<c.v?a:c),good.reduce((a,c)=>a.v>c.v?a:c));b.forEach((p,j)=>{if(!valid(p.v)&&(j===0||valid(b[j-1].v)))marks.push(p);if(valid(p.v)&&j>0&&!valid(b[j-1].v))marks.push(p);});out.push(...[...new Set(marks)].sort((a,b)=>a.t-b.t));}return out;
  }
  function stateAt(points,t) { if(!points.length||t<points[0].t||t>points[points.length-1].t)return null;let lo=0,hi=points.length-1;while(lo<hi){const m=Math.ceil((lo+hi)/2);if(points[m].t<=t)lo=m;else hi=m-1;}return points[lo].v; }
  const rangeControl=(id,label)=>`<label class="vs-range-control" for="vs-${id}-range"><span>Schnellwahl</span><select id="vs-${id}-range" data-history-range="${id}" aria-label="Zeitraum · ${label}"></select></label>`;
  const dateControl=(id,label)=>`<form class="vs-date-range" data-date-form="${id}" aria-label="Eigener Zeitraum · ${label}"><label for="vs-${id}-from">Von<input id="vs-${id}-from" data-date-input="${id}" type="datetime-local" step="60" required aria-label="Von · ${label}"></label><label for="vs-${id}-to">Bis<input id="vs-${id}-to" data-date-input="${id}" type="datetime-local" step="60" required aria-label="Bis · ${label}"></label><button class="vs-action" type="submit">Anzeigen</button><span class="vs-small vs-date-zone" id="vs-${id}-timezone"></span><p class="vs-small vs-date-feedback" id="vs-${id}-date-feedback" role="status" aria-live="polite"></p></form>`;
  const valueField=(id,label)=>`<div><span>${label}</span><strong id="vs-${id}">–</strong></div>`;
  const template=packs=>`<ha-card><div id="venus-speicher"><div class="vs-app">
    <div class="vs-heading"><div><h2 id="vs-title"></h2><p class="vs-sub">Venus A & E · Energie, Steuerung und Zellen im Blick.</p></div><div class="vs-demo" id="vs-updated"></div></div>
    <div class="vs-totals"><div class="vs-total"><span>Gesamt-Ladezustand</span><strong><span id="vs-total-soc">–</span> <small>%</small></strong><p>Kapazitätsgewichtet</p></div><div class="vs-total"><span>Gespeicherte Energie</span><strong><span id="vs-total-energy">–</span> <small>kWh</small></strong><p id="vs-total-capacity">SoC-Schätzung</p></div><div class="vs-total"><span>Leistung · beide Speicher</span><strong><span id="vs-total-power">–</span> <small>kW</small></strong><p id="vs-total-flow">–</p></div></div>
    <div class="vs-devices">${DEVICES.map(({id,name,color})=>`<section class="vs-panel" style="--vs-color:${color}" aria-label="${name}">
      <div class="vs-head"><h3 class="vs-device-name"><ha-icon icon="mdi:battery-outline" aria-hidden="true"></ha-icon>${name}</h3><span class="vs-status" id="vs-${id}-mode-label">–</span></div>
      <div class="vs-device-main"><div class="vs-soc"><span id="vs-${id}-soc">–</span> <small>%</small></div><div class="vs-power"><strong><span id="vs-${id}-power">–</span> <small>kW</small></strong><span id="vs-${id}-flow">–</span></div></div>
      <div class="vs-track" id="vs-${id}-soc-track" role="progressbar" aria-label="${name} Ladezustand" aria-valuemin="0" aria-valuemax="100"><span></span></div><div class="vs-capacity"><span id="vs-${id}-stored">–</span><span id="vs-${id}-reference">–</span></div>
      <div class="vs-device-values"><div><span class="vs-sub" id="vs-${id}-eta-label">Bis SoC-Grenze</span><strong id="vs-${id}-eta">–</strong></div><div><span class="vs-sub">Interne Temperatur</span><strong><span id="vs-${id}-temperature">–</span> <small>°C</small></strong></div></div>
      ${id==='a'?`<div class="vs-pack-strip">${packs.map(p=>`<div><div class="vs-pack-head"><span>Pack ${p}</span><span id="vs-a-p${p}-soc">–</span></div><div class="vs-track" id="vs-a-p${p}-soc-track" role="progressbar" aria-label="Venus A Pack ${p} Ladezustand" aria-valuemin="0" aria-valuemax="100"><span></span></div></div>`).join('')}</div>`:`<div class="vs-temperature-strip">${[['mos1','MOS 1','°C'],['mos2','MOS 2','°C'],['drift','Zelldrift','mV']].map(([k,l,u])=>`<div><span>${l}</span><strong><span id="vs-e-mini-${k}">–</span> ${u}</strong></div>`).join('')}</div>`}
      <details class="vs-device-details" id="vs-${id}-control"><summary>Steuerung</summary><div class="vs-settings">
        <div class="vs-setting"><label for="vs-${id}-mode">Betriebsmodus</label><select id="vs-${id}-mode" data-control="mode" data-device="${id}" disabled></select></div>
        ${[['charge_limit','Maximale Ladeleistung'],['discharge_limit','Maximale Entladeleistung']].map(([key,label])=>`<div class="vs-setting"><button type="button" class="vs-setting-info" data-limit-info="${id}_${key}" aria-label="${name} · ${label} · Entität öffnen" title="Entität öffnen"><span>${label}</span><output id="vs-${id}-${key}-value" for="vs-${id}-${key}">–</output><ha-icon icon="mdi:open-in-new" aria-hidden="true"></ha-icon></button><input id="vs-${id}-${key}" data-control="${key}" data-device="${id}" type="range" aria-label="${name} · ${label}" disabled><span class="vs-control-range" id="vs-${id}-${key}-range"></span></div>`).join('')}
        <div class="vs-save-row"><span id="vs-${id}-feedback" aria-live="polite"></span><button class="vs-action" type="button" data-apply="${id}" disabled>Übernehmen</button></div>
      </div></details>
      <details class="vs-device-details" id="vs-${id}-electric"><summary>Elektrik & Temperaturen</summary><div class="vs-details-grid">${[['ac','AC-Leistung'],['dc','DC-Leistung'],['loss','Verlustleistung'],['ratio','Wirkungsgrad · aktuell'],['voltage','DC-Spannung'],['current','DC-Strom'],['mos1','MOS 1'],['mos2','MOS 2'],['load','Auslastung'],['status','Wechselrichter'],['usable','Nutzbare Kapazität'],['eta_min','Bis SoC-Minimum'],['eta_max','Bis SoC-Maximum']].map(([key,label])=>valueField(id+'-'+key,label)).join('')}</div><p class="vs-small" id="vs-${id}-ratio-note"></p><div class="vs-fan"><span>${id==='a'?'Lüfter Venus A':'Lüfter WR & Speicher'}</span><label><input type="checkbox" id="vs-${id}-fan" data-fan="${id}" aria-label="${id==='a'?'Lüfter Venus A':'Lüfter WR und Speicher'}" disabled><span id="vs-${id}-fan-label">–</span></label></div><p class="vs-control-message" id="vs-${id}-fan-message" aria-live="polite"></p></details>
    </section>`).join('')}</div>
    <section class="vs-panel vs-chart-panel" aria-label="Gemeinsamer Speicherverlauf"><div class="vs-head"><h3>Gemeinsamer Verlauf</h3><div class="vs-tabs" role="group" aria-label="Verlauf auswählen">${Object.entries(MODES).map(([id,name])=>`<button type="button" data-view="${id}" aria-pressed="${id==='drift'}">${name}</button>`).join('')}</div></div><div class="vs-chart-context"><span id="vs-chart-caption"></span><div class="vs-chart-options">${rangeControl('main','Gemeinsamer Verlauf')}<select id="vs-chart-device" aria-label="Speicher für Temperaturverlauf" hidden><option value="a">Venus A</option><option value="e">Venus E</option></select><select id="vs-history-pack" aria-label="Venus A Pack für Zellspannungsverlauf" hidden>${packs.map(p=>`<option value="${p}">A · Pack ${p}</option>`).join('')}</select></div></div>${dateControl('main','Gemeinsamer Verlauf')}<div class="vs-chart" id="vs-main-chart"></div><div class="vs-legend" id="vs-main-legend" role="group" aria-label="Kurven ein- oder ausblenden"></div><p class="vs-history-note vs-small" id="vs-history-note" aria-live="polite"></p></section>
    <div class="vs-lower"><section class="vs-panel" aria-label="Energiebilanz"><div class="vs-head"><h3>Energiebilanz</h3><div class="vs-tabs" role="group" aria-label="Zeitraum der Energiebilanz">${[['today','Heute'],['month','Monat'],['total','Gesamt']].map(([id,label])=>`<button type="button" data-period="${id}" aria-pressed="${id==='today'}">${label}</button>`).join('')}</div></div><table class="vs-table"><thead><tr><th>Speicher</th><th>Laden<br>kWh</th><th>Entladen<br>kWh</th><th>Verhältnis<br>%</th></tr></thead><tbody id="vs-energy-rows"></tbody></table><p class="vs-table-note">Verhältnis: entladene / geladene Energie</p></section>
    <section class="vs-panel" aria-label="Zellspannungen beider Speicher"><div class="vs-head"><h3>Zellen · aktuell</h3><span class="vs-small">Min. / Max. & Drift</span></div><table class="vs-table"><thead><tr><th>Speicher</th><th>Min.<br>V</th><th>Max.<br>V</th><th>Drift<br>mV</th></tr></thead><tbody id="vs-cell-summary"></tbody></table><details class="vs-cell-details" id="vs-cell-details" open><summary>Venus A · ${packs.length*13} Einzelzellen</summary><div class="vs-cell-tools"><span class="vs-small" id="vs-cell-count">13 Zellen je Pack</span><select id="vs-cell-pack" aria-label="Batteriepack für aktuelle Zellspannungen">${packs.map(p=>`<option value="${p}">Pack ${p}</option>`).join('')}</select></div><div class="vs-cell-values" id="vs-cell-values"></div></details></section></div>
    <div class="vs-pack-charts">${packs.map(pack=>`<section class="vs-panel vs-chart-panel" aria-label="Venus A · Pack ${pack} · Zellspannungsverlauf"><div class="vs-head"><h3>Venus A · Pack ${pack} · Zellspannungen</h3>${rangeControl('pack'+pack,'Venus A · Pack '+pack)}</div>${dateControl('pack'+pack,'Venus A · Pack '+pack)}<p class="vs-small vs-pack-caption" id="vs-pack${pack}-caption"></p><div class="vs-chart" id="vs-pack${pack}-chart"></div><div class="vs-legend" id="vs-pack${pack}-legend" role="group" aria-label="Pack ${pack} · Zellkurven ein- oder ausblenden"></div><p class="vs-history-note vs-small" id="vs-pack${pack}-note" aria-live="polite"></p></section>`).join('')}</div>
    <details class="vs-data-notes" id="vs-data-notes" hidden><summary id="vs-data-notes-title"></summary><ul id="vs-data-notes-list"></ul></details>
    <div class="vs-bottom"><span>Speicher-Ladelogik A/E ${VERSION}</span><button id="vs-refresh" type="button">Verläufe aktualisieren</button></div><div class="vs-sr" id="vs-live" aria-live="polite"></div>
  </div></div></ha-card>`;

  class VenusSpeicherCockpitCard extends HTMLElement {
    constructor(){super();this.attachShadow({mode:'open'});this._chartId='vs-'+(++CARD_COUNT);this._mode='drift';this._period='today';this._cache={};this._epoch=0;this._configEpoch=0;this._draft={a:{},e:{}};this._messages={};this._busy={};this._fanBusy={};this._hidden=new Map();this._visibility=()=>{if(!document.hidden){this._queueUpdate();this._refreshHistory();}};}
    setConfig(config={}){
      const c={...DEFAULTS,...config,entities:{...DEFAULTS.entities,...config.entities},capacity_kwh:{...DEFAULTS.capacity_kwh,...config.capacity_kwh},power_sign:{...DEFAULTS.power_sign,...config.power_sign},colors:{...DEFAULTS.colors,...config.colors}};
      if(!['auto','light','dark'].includes(c.theme))throw new Error('theme muss auto, light oder dark sein.');
      for(const id of ['a','e']){if(!(num(c.capacity_kwh[id])>0))throw new Error('capacity_kwh.'+id+' muss größer als 0 sein.');c.capacity_kwh[id]=num(c.capacity_kwh[id]);if(![1,-1].includes(num(c.power_sign[id])))throw new Error('power_sign.'+id+' muss 1 oder -1 sein.');c.power_sign[id]=num(c.power_sign[id]);if(typeof c.colors[id]!=='string'||!/^#[0-9a-fA-F]{6}$/.test(c.colors[id]))throw new Error('colors.'+id+': sechsstelligen Hex-Farbwert verwenden.');}
      c.history_hours=Math.max(1,Math.min(168,num(c.history_hours)??24));c.history_refresh_seconds=Math.max(30,num(c.history_refresh_seconds)??120);c.history_max_points=Math.max(120,Math.min(3000,num(c.history_max_points)??720));c.power_deadband_w=Math.max(0,num(c.power_deadband_w)??10);c.enable_controls=c.enable_controls!==false;
      c.grid_power_sign=num(c.grid_power_sign);if(![1,-1].includes(c.grid_power_sign))throw new Error('grid_power_sign muss 1 oder -1 sein.');
      for(const [key,id]of Object.entries(c.entities)){if(typeof id!=='string'||(id&&!/^[a-z_]+\.[a-z0-9_]+$/.test(id)))throw new Error('entities.'+key+': ungültige Entitäts-ID.');if(id&&/^[ae]_(mode|charge_limit|discharge_limit|fan)$/.test(key)){const domain=key.endsWith('_mode')?'select.':key.endsWith('_fan')?'switch.':'number.';if(!id.startsWith(domain))throw new Error('entities.'+key+' muss eine '+domain+'-Entität sein.');}}
      c.pack_indices=[...new Set(config.pack_indices ?? [1,2])].filter(p=>Number.isInteger(p)&&p>=1&&p<=6).sort((a,b)=>a-b);
      const structural=JSON.stringify(this._config?.pack_indices)!==JSON.stringify(c.pack_indices);
      const selections=['cell-pack','history-pack'].map(id=>[id,this.$('#vs-'+id)?.value]);
      this._infoDialog?.close();this._config=c;this._ranges={...Object.fromEntries(['main',...c.pack_indices.map(p=>'pack'+p)].map(id=>[id,c.history_hours])),...this._ranges};this._fixedRanges||={};this._dateDirty||={};
      if(structural){this.shadowRoot.replaceChildren();this._cellsSignature=this._cellValuesSignature=this._energySignature=null;}
      this._configEpoch++;this._epoch++;this._cache={};this._draft={a:{},e:{}};this._messages={};this._controlErrors={};this._busy={};this._fanBusy={};this._build();for(const [id,value]of selections){const el=this.$('#vs-'+id);if([...el.options].some(o=>o.value===value))el.value=value;}this._syncRanges();this._update();if(this.isConnected)this._refreshHistory();
    }
    set hass(value){const old=this._hass;this._hass=value;if(!this._config||!value)return;const zoneChanged=old&&old.config?.time_zone!==value.config?.time_zone;if(zoneChanged){this._epoch++;this._cache={};this._dateDirty={};}if(!old||zoneChanged||old.themes!==value.themes||Object.values(this._config.entities).some(id=>id&&old.states?.[id]!==value.states?.[id]))this._queueUpdate();if(this.isConnected&&(!old||zoneChanged))this._refreshHistory();}
    get hass(){return this._hass;}
    connectedCallback(){if(!this._config)this.setConfig({});this._observer||=new ResizeObserver(entries=>{const w=entries[0]?.contentRect.width;if(w!==this._width){this._width=w;this._queueCharts();}});this._observer.observe(this);document.addEventListener('visibilitychange',this._visibility);clearInterval(this._timer);this._timer=setInterval(()=>{if(!document.hidden){this._queueUpdate();this._refreshHistory();}},30000);this._update();this._refreshHistory();}
    disconnectedCallback(){this._infoDialog?.close();this._observer?.disconnect();clearInterval(this._timer);document.removeEventListener('visibilitychange',this._visibility);cancelAnimationFrame(this._frame);cancelAnimationFrame(this._chartFrame);this._frame=this._chartFrame=0;}
    getGridOptions(){return {columns:'full',min_columns:6};}
    getCardSize(){return Math.max(12,Math.ceil((this.offsetHeight||1600)/50));}
    static getStubConfig(){return {type:'custom:'+TAG,title:DEFAULTS.title};}
    _packs(){return this._config?.pack_indices || [];}
    $(s){return this.shadowRoot.querySelector(s);}$$(s){return [...this.shadowRoot.querySelectorAll(s)];}
    _set(id,value){const el=this.$('#vs-'+id);if(el&&el.textContent!==String(value))el.textContent=value;}
    _queueUpdate(){if(!this._frame)this._frame=requestAnimationFrame(()=>{this._frame=0;this._update();});}
    _queueCharts(){if(!this._chartFrame)this._chartFrame=requestAnimationFrame(()=>{this._chartFrame=0;this._drawChart();});}
    _build(){if(this.$('#venus-speicher'))return;this.shadowRoot.innerHTML=`<style>${CSS}
      #venus-speicher .vs-heading,#venus-speicher .vs-totals,#venus-speicher .vs-devices{display:none}
      #venus-speicher .vs-app{padding:0;background:transparent;border-radius:0}
      #venus-speicher .vs-panel{border:0}
      #venus-speicher .vs-tooltip{pointer-events:auto}
      #venus-speicher .vs-tooltip .entity-info{pointer-events:auto;font:inherit}
      @container(max-width:600px){
        #venus-speicher .vs-tooltip{position:static;inset:auto!important;width:100%;min-width:0;max-width:none;margin-top:12px;box-shadow:none;box-sizing:border-box}
        #venus-speicher .vs-tooltip[data-cells="true"]{width:100%;max-width:none}
      }
    </style>${template(this._packs())}`;
      this.$('[data-view="cells"]').hidden=!this._packs().length;
      if(!this._packs().length&&this._mode==='cells')this._mode='drift';
      const app=this.$('.vs-app'),lower=this.$('.vs-lower');
      app.insertBefore(this.$('.vs-pack-charts'),lower);
      lower.prepend(lower.lastElementChild);
      this.$$('[data-view]').forEach(b=>b.addEventListener('click',()=>{this._mode=b.dataset.view;this._update();this._refreshHistory();this._set('live',MODES[this._mode]+' ausgewählt');}));
      this.$$('[data-period]').forEach(b=>b.addEventListener('click',()=>{this._period=b.dataset.period;this._update();}));
      for(const selector of ['#vs-chart-device','#vs-history-pack'])this.$(selector).addEventListener('change',()=>{this._queueCharts();this._refreshHistory();});
      this.$('#vs-cell-pack').addEventListener('change',()=>this._update());
      this.$('#vs-refresh').addEventListener('click',()=>this._refreshHistory(true));
      this.$$('[data-control]').forEach(input=>input.addEventListener(input.tagName==='SELECT'?'change':'input',()=>{const id=input.dataset.device,key=input.dataset.control,value=key==='mode'?input.value:num(input.value);this._draft[id][key]={value};delete this._messages[id];this._controlErrors[id]=false;this._syncControls(id);}));
      this.$$('[data-apply]').forEach(b=>b.addEventListener('click',()=>this._apply(b.dataset.apply)));
      this.$$('[data-fan]').forEach(input=>input.addEventListener('change',()=>this._setFan(input.dataset.fan,input.checked)));
      this.$$('[data-limit-info]').forEach(button=>button.addEventListener('click',()=>openEntityInfo(this,[button.dataset.limitInfo],button.getAttribute('aria-label'))));
      this.$$('[data-history-range]').forEach(select=>select.addEventListener('change',()=>{const chart=select.dataset.historyRange;if(select.value==='custom'){this._markDateDraft(chart);this.$('#vs-'+chart+'-from').focus();return;}this._ranges[chart]=Number(select.value);delete this._fixedRanges[chart];delete this._dateDirty[chart];this._dateFeedback(chart,'');this._syncDateInputs();this._queueCharts();this._refreshHistory();}));
      this.$$('[data-date-input]').forEach(input=>input.addEventListener('input',()=>this._markDateDraft(input.dataset.dateInput)));
      this.$$('[data-date-form]').forEach(form=>form.addEventListener('submit',event=>{event.preventDefault();this._applyDateRange(form.dataset.dateForm);}));
      this._bindInfo();
    }
    _bindInfo(){
      const bind=(id,keys,label)=>bindEntityInfo(this,'#vs-'+id,keys,label);
      const weighted=['a_soc','e_soc','a_reference','e_reference','reference_ready'];
      bind('total-soc',weighted,'Gesamt-Ladezustand');bind('total-energy',weighted,'Gespeicherte Energie · SoC-Schätzung');
      bind('total-power',['a_power','e_power','sign_setting'],'Leistung · beide Speicher');
      for(const {id,name} of DEVICES){
        for(const [key,label]of [['soc','Ladezustand'],['power','Leistung'],['temperature','Interne Temperatur'],['voltage','DC-Spannung'],['current','DC-Strom'],['mos1','MOS 1'],['mos2','MOS 2'],['load','Auslastung'],['status','Wechselrichter'],['usable','Nutzbare Kapazität'],['eta_min','Bis SoC-Minimum'],['eta_max','Bis SoC-Maximum']])bind(id+'-'+key,[id+'_'+key],name+' · '+label);
        bind(id+'-ac',[id+'_ac_raw'],name+' · AC-Leistung');bind(id+'-dc',[id+'_dc'],name+' · DC-Leistung');
        for(const key of ['loss','ratio'])bind(id+'-'+key,[id+'_ac_raw',id+'_dc',id+'_power','sign_setting'],name+' · '+(key==='loss'?'Leistungsdifferenz AC/DC':'Wirkungsgrad · aktuell'));
        bind(id+'-mode-label',[id+'_mode'],name+' · Betriebsmodus');
        bind(id+'-stored',[id+'_soc',id+'_reference','reference_ready'],name+' · Gespeicherte Energie · SoC-Schätzung');
        bind(id+'-reference',()=>{const ref=this._read(id+'_reference','energy','kWh'),ready=this._state('reference_ready');return ref>0&&(!ready||ready.state==='on')?[id+'_reference']:[];},name+' · Referenzkapazität');
        bind(id+'-eta',()=>{const p=this._power(id);return p>0?[id+'_eta_min']:p<0?[id+'_eta_max']:[id+'_eta_min',id+'_eta_max'];},name+' · Restzeit');
      }
      for(const p of this._packs())bind('a-p'+p+'-soc',['a_p'+p+'_soc'],'Venus A · Pack '+p+' · Ladezustand');
      for(const key of['mos1','mos2','drift'])bind('e-mini-'+key,['e_'+key],'Venus E · '+(key==='drift'?'Zelldrift':key.toUpperCase()));
    }
    _electrical(id,power){
      const dc=this._read(id+'_dc','power','W'),ac=this._read(id+'_ac_raw','power','W');
      if(!valid(ac)||!valid(dc))return {ac,dc,ratio:null,loss:null,note:'AC- oder DC-Messwert fehlt oder die Einheit wird nicht unterstützt. Werte antippen, um die Quellen zu prüfen.'};
      if(ac===0&&dc===0)return {ac,dc,ratio:null,loss:0,note:'AC und DC sind 0 W. Ohne Eingangsleistung lässt sich kein Wirkungsgrad berechnen.'};
      if(!valid(power)||power===0)return {ac,dc,ratio:null,loss:null,note:'Keine eindeutige Lade-/Entladerichtung. Die normierte AC-Leistung und ihre Vorzeicheneinstellung prüfen.'};
      const charging=power<0,input=Math.abs(charging?ac:dc),output=Math.abs(charging?dc:ac),loss=(input-output)*1000,ratio=input>0?output/input*100:null;
      const notes=[charging?'Laden: DC / AC.':'Entladen: AC / DC.','Näherung aus Momentanwerten.'];
      if(input===0)notes.push('Eingangsleistung ist 0 W: kein Wirkungsgrad berechenbar.');
      else if(input<=.05)notes.push('Bei höchstens 50 W Eingangsleistung ist das Verhältnis ungenau.');
      if(loss<0)notes.push('Ausgang höher als Eingang: rechnerisches Verhältnis und negative Leistungsdifferenz. Aktualisierungszeiten und Vorzeichen prüfen.');
      return {ac,dc,ratio,loss,note:notes.join(' ')};
    }
    _state(key){return this._hass?.states?.[this._config.entities[key]];}
    _read(key,kind,unit,required=false){const s=this._state(key),n=num(s?.state);if(!valid(n)){if(required&&this._config.entities[key])this._issues.add(this._config.entities[key]+': kein gültiger Messwert');return null;}const value=kind?convert(n,kind,s.attributes?.unit_of_measurement||unit):n;if(value===null&&kind)this._issues.add(this._config.entities[key]+': Einheit „'+(s.attributes?.unit_of_measurement||unit)+'“ wird nicht unterstützt');return value;}
    _text(key){const s=this._state(key);return available(s)?String(s.state):'–';}
    _percent(key,required=false){const v=this._read(key,'percent','%',required);return valid(v)&&v>=0&&v<=100?v:null;}
    _capacity(id){const initialized=this._state('reference_ready');const reference=this._read(id+'_reference','energy','kWh');return reference>0&&(!initialized||initialized.state==='on')?reference:this._config.capacity_kwh[id];}
    _sign(id){const setting=this._state('sign_setting'),ready=this._state('reference_ready');return ['on','off'].includes(setting?.state)&&(!ready||ready.state==='on')?(setting.state==='on'?1:-1)*this._config.power_sign[id]:this._config.power_sign[id];}
    _power(id,required=false){const p=this._read(id+'_power','power','W',required);return valid(p)?p*this._sign(id):null;}
    _flow(p){if(!valid(p))return 'Leistung nicht verfügbar';if(Math.abs(p)*1000<=this._config.power_deadband_w)return 'Bereit';return p>0?'Entlädt':'Lädt';}
    _socTrack(key,value){const el=this.$('#vs-'+key+'-soc-track');if(!el)return;el.firstElementChild.style.width=(valid(value)?value:0)+'%';if(valid(value)){el.setAttribute('aria-valuenow',String(value));el.setAttribute('aria-valuetext',fmt(value,0)+' %');}else{el.removeAttribute('aria-valuenow');el.setAttribute('aria-valuetext','Ladezustand nicht verfügbar');}}
    _duration(key){const s=this._state(key);if(!available(s))return '–';const raw=String(s.state),n=num(raw),u=String(s.attributes?.unit_of_measurement||'').toLowerCase();if(s.attributes?.device_class==='timestamp'){const t=Date.parse(raw);return Number.isFinite(t)?this._minutes(Math.max(0,(t-Date.now())/60000)):'–';}if(n!==null){const m=['s','sec','seconds'].includes(u)?n/60:['min','minutes'].includes(u)?n:['h','hours'].includes(u)?n*60:null;return m===null?'–':this._minutes(m);}const match=/^(\d+):(\d{2})(?::(\d{2}))?$/.exec(raw);return match?this._minutes(+match[1]*60 + +match[2] + +(match[3]||0)/60):raw;}
    _minutes(m){if(!valid(m)||m<0)return '–';const n=Math.round(m);return n>=60?Math.floor(n/60)+' h '+n%60+' min':n+' min';}
    _cellKeys(pack){return Array.from({length:13},(_,i)=>'a_p'+pack+'_cell_'+(i+1));}
    _cellStats(pack){const keys=this._cellKeys(pack),values=keys.map(key=>this._read(key,'voltage','V')).filter(v=>valid(v)&&v>0);return {count:values.length,min:values.length===13?Math.min(...values):null,max:values.length===13?Math.max(...values):null};}
    _update(){if(!this._config||!this.$('#venus-speicher'))return;this._issues=new Set();const root=this.$('#venus-speicher'),dark=this._config.theme==='dark'||(this._config.theme==='auto'&&this._hass?.themes?.darkMode);root.style.colorScheme=dark?'dark':'light';root.style.setProperty('--vs-a',dark?`color-mix(in srgb, ${this._config.colors.a} 58%, #ffffff)` : this._config.colors.a);root.style.setProperty('--vs-e',dark?`color-mix(in srgb, ${this._config.colors.e} 58%, #ffffff)` : this._config.colors.e);
      this._set('title',this._config.title);this._set('updated','Live-Werte · '+this._clock(Date.now()));const power=DEVICES.map(d=>this._power(d.id,true)),soc=DEVICES.map(d=>this._percent(d.id+'_soc',true)),capacity=DEVICES.map(d=>this._capacity(d.id)),totalPower=sum(power),energy=sum(soc.map((v,i)=>valid(v)?v/100*capacity[i]:null));
      this._set('total-soc',fmt(valid(energy)?energy/sum(capacity)*100:null,0));this._set('total-energy',fmt(energy,2));this._set('total-capacity','SoC-Schätzung · Referenz '+fmt(sum(capacity),2)+' kWh');this._set('total-power',fmt(valid(totalPower)?Math.abs(totalPower):null,2));this._set('total-flow',!valid(totalPower)?'Daten fehlen':Math.abs(totalPower)*1000<=this._config.power_deadband_w?'Bereit':totalPower>0?'Entladen → Haus':'Laden ← AC');
      DEVICES.forEach(({id},i)=>{this._set(id+'-soc',fmt(soc[i],0));this._socTrack(id,soc[i]);this._set(id+'-power',fmt(valid(power[i])?Math.abs(power[i]):null,2));this._set(id+'-flow',this._flow(power[i]));this._set(id+'-stored',fmt(valid(soc[i])?soc[i]/100*capacity[i]:null,2)+' kWh · SoC-Schätzung');this._set(id+'-reference','Referenz '+fmt(capacity[i],2)+' kWh');this._set(id+'-mode-label',this._text(id+'_mode'));
        const discharging=valid(power[i])&&power[i]*1000>this._config.power_deadband_w,charging=valid(power[i])&&power[i]*1000< -this._config.power_deadband_w;this._set(id+'-eta-label',discharging?'Bis SoC-Minimum':charging?'Bis SoC-Maximum':'Bis SoC-Grenze');this._set(id+'-eta',discharging?this._duration(id+'_eta_min'):charging?this._duration(id+'_eta_max'):'–');this._set(id+'-eta_min',this._duration(id+'_eta_min'));this._set(id+'-eta_max',this._duration(id+'_eta_max'));
        this._set(id+'-temperature',fmt(this._read(id+'_temperature','temperature','°C'),1));const electrical=this._electrical(id,power[i]);
        this._set(id+'-ac',fmt(valid(electrical.ac)?Math.abs(electrical.ac)*1000:null,0)+' W');this._set(id+'-dc',fmt(valid(electrical.dc)?Math.abs(electrical.dc)*1000:null,0)+' W');
        this._set(id+'-ratio',fmt(electrical.ratio,1)+' %');this._set(id+'-loss',fmt(electrical.loss,0)+' W');this._set(id+'-ratio-note',electrical.note);
        this.$('#vs-'+id+'-ratio').closest('.entity-info').parentElement.querySelector(':scope > span').textContent=electrical.loss<0?'Rechnerisches Verhältnis · aktuell':'Wirkungsgrad · aktuell';
        this.$('#vs-'+id+'-loss').closest('.entity-info').parentElement.querySelector(':scope > span').textContent=electrical.loss<0?'Leistungsdifferenz · aktuell':'Verlustleistung · Näherung';
        for(const [key,kind,unit,decimals]of [['voltage','voltage','V',2],['current','current','A',2],['mos1','temperature','°C',1],['mos2','temperature','°C',1],['load','percent','%',0],['usable','energy','kWh',2]])this._set(id+'-'+key,fmt(this._read(id+'_'+key,kind,unit),decimals)+' '+unit);
        this._set(id+'-status',this._text(id+'_status'));this._syncControls(id);this._syncFan(id);
      });
      for(const p of this._packs()){const v=this._percent('a_p'+p+'_soc');this._set('a-p'+p+'-soc',fmt(v,0)+' %');this._socTrack('a-p'+p,v);}
      this._set('e-mini-mos1',fmt(this._read('e_mos1','temperature','°C'),1));this._set('e-mini-mos2',fmt(this._read('e_mos2','temperature','°C'),1));this._set('e-mini-drift',fmt(this._read('e_drift','drift','V'),0));
      this._syncDateInputs();this._energyTable();this._cellTable();this.$$('[data-view]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.view===this._mode)));this.$$('[data-period]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.period===this._period)));this._showIssues();this._queueCharts();
    }
    _energyTable(){const values=DEVICES.map(({id})=>[this._read(id+'_charge_'+this._period,'energy','kWh'),this._read(id+'_discharge_'+this._period,'energy','kWh')]),rows=[...DEVICES.map((d,i)=>({...d,values:values[i]})),{id:'sum',name:'Gesamt',values:[sum(values.map(v=>v[0])),sum(values.map(v=>v[1]))]}];const signature=JSON.stringify([this._period,rows]);if(this._energySignature===signature)return;this._energySignature=signature;this.$('#vs-energy-rows').replaceChildren(...rows.map(d=>{const row=document.createElement('tr');if(d.id==='sum')row.className='vs-sum';const name=document.createElement('td');if(d.color){const dot=document.createElement('span');dot.className='vs-device-dot';dot.style.setProperty('--vs-color',d.color);name.append(dot);}name.append(document.createTextNode(d.name));row.append(name);[fmt(d.values[0],2),fmt(d.values[1],2),fmt(d.values[0]>0&&valid(d.values[1])?d.values[1]/d.values[0]*100:null,1)].forEach((v,index)=>{const td=document.createElement('td');td.append(entityInfoButton(this,()=>{const ids=d.id==='sum'?['a','e']:[d.id];return ids.flatMap(id=>(index===2?['charge','discharge']:[index===0?'charge':'discharge']).map(k=>id+'_'+k+'_'+this._period));},d.name+' · '+['Laden','Entladen','Energieverhältnis'][index],v));row.append(td);});return row;}));}
    _cellTable(){const stats=[...this._packs().map(pack=>({pack,name:'A · Pack '+pack,color:'var(--vs-a)',...this._cellStats(pack),drift:this._read('a_p'+pack+'_drift','drift','mV')})),{name:'Venus E',color:'var(--vs-e)',min:this._read('e_cell_min','voltage','V'),max:this._read('e_cell_max','voltage','V'),drift:this._read('e_drift','drift','V')}];
      const signature=JSON.stringify(stats);if(this._cellsSignature!==signature){this._cellsSignature=signature;this.$('#vs-cell-summary').replaceChildren(...stats.map((d,index)=>{const row=document.createElement('tr'),name=document.createElement('td'),dot=document.createElement('span');dot.className='vs-device-dot';dot.style.setProperty('--vs-color',d.color);name.append(dot,document.createTextNode(d.name));row.append(name);[fmt(d.min,3),fmt(d.max,3),fmt(d.drift,0)].forEach((v,column)=>{const td=document.createElement('td'),keys=!d.pack?[["e_cell_min"],["e_cell_max"],["e_drift"]][column]:column===2?['a_p'+d.pack+'_drift']:this._cellKeys(d.pack);td.append(entityInfoButton(this,keys,d.name+' · '+['Minimale Zellspannung','Maximale Zellspannung','Zelldrift'][column],v));row.append(td);});return row;}));}
      this.$('#vs-cell-details').hidden=!this._packs().length;
      if(!this._packs().length)return;
      const pack=+this.$('#vs-cell-pack').value,keys=this._cellKeys(pack),data=keys.map(k=>this._read(k,'voltage','V')),cellSignature=JSON.stringify([pack,data]);if(cellSignature!==this._cellValuesSignature){this._cellValuesSignature=cellSignature;this.$('#vs-cell-values').replaceChildren(...data.map((v,i)=>{const div=document.createElement('div');div.dataset.cell=String(i+1);const label=document.createElement('span'),value=document.createElement('strong'),unit=document.createElement('small');label.textContent='Zelle '+(i+1);value.append(document.createTextNode(fmt(v>0?v:null,3)));unit.textContent='V';value.append(unit);div.append(label,entityInfoButton(this,[keys[i]],'Venus A · Pack '+pack+' · Zelle '+(i+1),value));return div;}));}
      this._set('cell-count',data.filter(v=>v>0).length+'/13 Zellen verfügbar');for(const [p,s]of this._packs().map(p=>[p,this._cellStats(p)]))if(s.count!==13)this._issues.add('Venus A · Pack '+p+': '+s.count+'/13 Zellspannungen verfügbar. Min./Max. erst bei vollständigen Daten.');
    }
    _showIssues(){const items=[...this._issues],details=this.$('#vs-data-notes');details.hidden=!items.length;this._set('data-notes-title',items.length+(items.length===1?' Datenhinweis':' Datenhinweise'));const list=this.$('#vs-data-notes-list');if(list.textContent!==items.join(''))list.replaceChildren(...items.map(v=>{const li=document.createElement('li');li.textContent=v;return li;}));}

    _controlMeta(id,key){const s=this._state(id+'_'+key);if(!available(s))return null;if(key==='mode'){const options=s.attributes?.options;return Array.isArray(options)&&options.length&&options.every(v=>typeof v==='string')?{state:s,options}:null;}const min=num(s.attributes?.min),max=num(s.attributes?.max),step=num(s.attributes?.step),unit=s.attributes?.unit_of_measurement||'W',factor=convert(1,'power',unit);return min!==null&&max!==null&&max>min&&step>0&&factor!==null&&num(s.state)!==null?{state:s,min,max,step,unit,factor}:null;}
    _validDraft(key,value,meta){if(!meta)return false;if(key==='mode')return meta.options.includes(value);if(!valid(value)||value<meta.min-1e-8||value>meta.max+1e-8)return false;const steps=(value-meta.min)/meta.step;return Math.abs(steps-Math.round(steps))<1e-5;}
    _syncControls(id){const busy=!!this._busy[id],draft=this._draft[id],enabled=this._config.enable_controls&&typeof this._hass?.callService==='function';let invalid=false,missing=false;
      for(const key of ['mode','charge_limit','discharge_limit']){const input=this.$('#vs-'+id+'-'+key),meta=this._controlMeta(id,key),entry=draft[key];input.disabled=!enabled||busy||!meta;if(!meta){missing=true;if(key==='mode'){if(input.dataset.options!=='missing'){input.replaceChildren(new Option('Nicht verfügbar',''));input.dataset.options='missing';}}else{this._set(id+'-'+key+'-value','–');this._set(id+'-'+key+'-range','Grenzen oder Messwert nicht verfügbar');}if(entry)invalid=true;continue;}
        if(key==='mode'){const options=JSON.stringify(meta.options);if(input.dataset.options!==options){input.replaceChildren(...meta.options.map(value=>new Option(value,value)));input.dataset.options=options;}const value=entry?entry.value:meta.state.state;if(meta.options.includes(value))input.value=value;else input.value='';}
        else{input.min=String(meta.min);input.max=String(meta.max);input.step=String(meta.step);const value=entry?entry.value:num(meta.state.state);if(this._validDraft(key,value,meta))input.value=String(value);this._set(id+'-'+key+'-value',fmt(valid(value)?value*meta.factor*1000:null,0)+' W');this._set(id+'-'+key+'-range',fmt(meta.min*meta.factor*1000,0)+'–'+fmt(meta.max*meta.factor*1000,0)+' W');}
        if(entry&&!this._validDraft(key,entry.value,meta))invalid=true;
      }
      const dirty=Object.keys(draft).length,button=this.$('[data-apply="'+id+'"]');button.disabled=!enabled||busy||!dirty||invalid;button.textContent=busy?'Wird übergeben …':'Übernehmen';let message=this._messages[id]||'';
      if(!enabled)message='Steuerung deaktiviert';else if(invalid)message='Entwurf passt nicht zu den aktuellen Optionen oder Grenzen.';else if(dirty&&!busy&&!this._controlErrors?.[id])message='Änderungen noch nicht übernommen';else if(!message&&missing)message='Einzelne Bedienelemente nicht verfügbar';
      this._set(id+'-feedback',message);this.$('#vs-'+id+'-feedback').dataset.error=String(!!this._controlErrors?.[id]);
    }
    async _apply(id){if(this._busy[id]||!this._config.enable_controls||!this._hass?.callService)return;const draft=this._draft[id],keys=['charge_limit','discharge_limit','mode'].filter(k=>Object.hasOwn(draft,k));if(!keys.length)return;const plan=keys.map(key=>({key,value:draft[key].value,target:this._config.entities[id+'_'+key]}));if(plan.some(p=>!this._validDraft(p.key,p.value,this._controlMeta(id,p.key)))){this._messages[id]='Bitte die aktuellen Optionen und Grenzen prüfen.';this._syncControls(id);return;}
      this._busy[id]=true;this._controlErrors||={};this._controlErrors[id]=false;this._messages[id]='';this._syncControls(id);const epoch=this._configEpoch;let sent=0;
      try{for(const item of plan){if(epoch!==this._configEpoch||!this.isConnected)throw new Error('Konfiguration oder Ansicht geändert; weitere Änderungen gestoppt.');const meta=this._controlMeta(id,item.key);if(!this._validDraft(item.key,item.value,meta))throw new Error('Optionen oder Grenzen haben sich geändert.');const current=item.key==='mode'?meta.state.state:num(meta.state.state);if(current!==item.value){await this._service(item.key==='mode'?'select':'number',item.key==='mode'?'select_option':'set_value',{entity_id:item.target,...(item.key==='mode'?{option:item.value}:{value:item.value})});sent++;}if(epoch===this._configEpoch)delete draft[item.key];}
        if(epoch===this._configEpoch)this._messages[id]=sent?'An Home Assistant übergeben.':'Werte sind bereits eingestellt.';
      }catch(e){if(epoch===this._configEpoch){this._controlErrors[id]=true;this._messages[id]=(sent?'Teilweise übergeben. ':'')+'Fehler: '+(e?.message||String(e));}}
      finally{if(epoch===this._configEpoch){this._busy[id]=false;this._syncControls(id);}}
    }
    _syncFan(id){const s=this._state(id+'_fan'),input=this.$('#vs-'+id+'-fan');input.disabled=!this._config.enable_controls||!this._hass?.callService||this._fanBusy[id]||!['on','off'].includes(s?.state);input.checked=s?.state==='on';this._set(id+'-fan-label',s?.state==='on'?'Ein':s?.state==='off'?'Aus':'Nicht verfügbar');}
    async _setFan(id,on){const s=this._state(id+'_fan');if(this._fanBusy[id]||!this._config.enable_controls||!this._hass?.callService||!['on','off'].includes(s?.state))return;const target=this._config.entities[id+'_fan'],epoch=this._configEpoch;this._fanBusy[id]=true;this._set(id+'-fan-message','');this._syncFan(id);try{await this._service('switch',on?'turn_on':'turn_off',{entity_id:target});if(epoch===this._configEpoch)this._set(id+'-fan-message','An Home Assistant übergeben.');}catch(e){if(epoch===this._configEpoch)this._set(id+'-fan-message','Fehler: '+(e?.message||String(e)));}finally{if(epoch===this._configEpoch){this._fanBusy[id]=false;this._syncFan(id);}}}
    async _service(domain,action,data){let timer;try{return await Promise.race([this._hass.callService(domain,action,data),new Promise((_,reject)=>{timer=setTimeout(()=>reject(new Error('Keine Bestätigung erhalten; aktuellen Zustand prüfen.')),20000);})]);}finally{clearTimeout(timer);}}

    _zone(){return this._hass?.config?.time_zone||Intl.DateTimeFormat().resolvedOptions().timeZone||'Europe/Berlin';}
    _dateKey(t){const p=new Intl.DateTimeFormat('en-CA',{timeZone:this._zone(),year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(t),o=Object.fromEntries(p.map(v=>[v.type,v.value]));return `${o.year}-${o.month}-${o.day}`;}
    _clock(t){return new Intl.DateTimeFormat('de-DE',{timeZone:this._zone(),hour:'2-digit',minute:'2-digit'}).format(t);}
    _dateLabel(t){return new Intl.DateTimeFormat('de-DE',{timeZone:this._zone(),day:'2-digit',month:'2-digit'}).format(t);}
    _range(hours=this._ranges.main){const end=Date.now();return {start:end-hours*3600000,end,hours,fixed:false};}
    _viewRange(chart){const fixed=this._fixedRanges[chart];return fixed?{...fixed,hours:(fixed.end-fixed.start)/3600000,fixed:true}:this._range(this._ranges[chart]);}
    _rangeLabel(range){if(typeof range==='number')range=this._range(range);if(range.fixed){const full=t=>new Intl.DateTimeFormat('de-DE',{timeZone:this._zone(),day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'}).format(t);return full(range.start)+' – '+full(range.end);}const hours=range.hours;return hours===1?'Letzte Stunde':hours===168?'Letzte 7 Tage':'Letzte '+fmt(hours,0)+' Stunden';}
    _wallParts(time){if(this._wallZone!==this._zone()){this._wallZone=this._zone();this._wallFormat=new Intl.DateTimeFormat('en-CA',{timeZone:this._zone(),year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'});}return Object.fromEntries(this._wallFormat.formatToParts(time).map(p=>[p.type,p.value]));}
    _wallInput(time){const p=this._wallParts(time);return p.year+'-'+p.month+'-'+p.day+'T'+p.hour+':'+p.minute;}
    _wallCandidates(value){
      const match=/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/.exec(value);if(!match)return [];
      const [year,month,day,hour,minute]=match.slice(1).map(Number),desired=Date.UTC(year,month-1,day,hour,minute),check=new Date(desired);
      if(year<100||check.getUTCFullYear()!==year||check.getUTCMonth()!==month-1||check.getUTCDate()!==day||check.getUTCHours()!==hour||check.getUTCMinutes()!==minute)return [];
      const wall=time=>{const p=this._wallParts(time);return Date.UTC(+p.year,+p.month-1,+p.day,+p.hour,+p.minute,+p.second);},offsets=new Set([-36,-12,0,12,36].map(h=>{const t=desired+h*3600000;return wall(t)-t;}));
      return [...new Set([...offsets].map(offset=>desired-offset).filter(time=>wall(time)===desired))].sort((a,b)=>a-b);
    }
    _dateFeedback(chart,message,error=false){const el=this.$('#vs-'+chart+'-date-feedback');el.textContent=message;el.dataset.error=String(error);}
    _markDateDraft(chart){this._dateDirty[chart]=true;this.$('#vs-'+chart+'-range').value='custom';this._dateFeedback(chart,'Noch nicht angewendet. Mit „Anzeigen“ laden.');}
    _syncDateInputs(){if(!this._config||!this._ranges)return;for(const chart of ['main',...this._packs().map(p=>'pack'+p)]){const from=this.$('#vs-'+chart+'-from'),to=this.$('#vs-'+chart+'-to');if(!from||!to)continue;this._set(chart+'-timezone','Zeiten in '+this._zone());if(this._dateDirty[chart]||[from,to].includes(this.shadowRoot.activeElement))continue;const range=this._viewRange(chart);from.value=this._wallInput(range.start);to.value=this._wallInput(range.end);this.$('#vs-'+chart+'-range').value=range.fixed?'custom':String(range.hours);}}
    _applyDateRange(chart){
      const from=this.$('#vs-'+chart+'-from').value,to=this.$('#vs-'+chart+'-to').value;
      if(!from||!to){this._dateFeedback(chart,'Bitte Von und Bis vollständig ausfüllen.',true);return;}
      const starts=this._wallCandidates(from),ends=this._wallCandidates(to);
      if(!starts.length||!ends.length){this._dateFeedback(chart,'Datum oder Uhrzeit ist ungültig oder existiert wegen der Zeitumstellung nicht.',true);return;}
      if(ends[0]<=starts[0]){this._dateFeedback(chart,'„Bis“ muss nach „Von“ liegen.',true);return;}
      this._fixedRanges[chart]={start:starts[0],end:ends[0]};delete this._dateDirty[chart];
      this._dateFeedback(chart,starts.length>1||ends.length>1?'Zeitumstellung: Bei doppelt vorkommender Uhrzeit wird das erste Vorkommen verwendet.':'');
      this._syncDateInputs();this._queueCharts();this._refreshHistory();
    }
    _syncRanges(){for(const select of this.$$('[data-history-range]')){const chart=select.dataset.historyRange,hours=this._ranges[chart],choices=[...new Set([...HISTORY_RANGES,hours])].sort((a,b)=>a-b);select.replaceChildren(...choices.map(value=>new Option(value===168?'7 Tage':fmt(value,0)+(value===1?' Stunde':' Stunden'),String(value))),new Option('Benutzerdefiniert','custom'));select.value=this._fixedRanges[chart]?'custom':String(hours);}this._syncDateInputs();}
    _cacheKey(group,range){return group+':'+(typeof range==='number'?range:range.fixed?range.start+':'+range.end:range.hours);}
    _requestedRanges(){return [[this._group(),this._viewRange('main')],...this._packs().map(p=>['cells_'+p,this._viewRange('pack'+p)])];}
    _rangeNeeded(key){return this.isConnected&&this._requestedRanges().some(([group,range])=>this._cacheKey(group,range)===key);}
    _spec(key,kind,unit,name,color,dash=''){return {key,kind,unit,name,color,dash};}
    _group(){return this._mode==='temperature'?'temperature_'+this.$('#vs-chart-device').value:this._mode==='cells'?'cells_'+this.$('#vs-history-pack').value:'overview';}
    _specs(group){
      const s=(...args)=>this._spec(...args),c=i=>'var(--vs-chart-'+i+')',a=c(1),e=c(2),p1=c(3),p2=c(4);
      if(group.startsWith('cells_')){const p=+group.slice(-1);return this._cellKeys(p).map((key,i)=>s(key,'voltage','V','Zelle '+(i+1),c(i+1),['','','','','','','','7 3','3 3','9 3 2 3','7 3','3 3','9 3 2 3'][i]));}
      if(group.startsWith('temperature_')){const id=group.slice(-1);return [['temperature','Intern',''],['mos1','MOS 1','7 3'],['mos2','MOS 2','2 3']].map(([key,name,dash],i)=>s(id+'_'+key,'temperature','°C',name,c(i+1),dash));}
      return [s('a_power','power','W','Venus A',a),s('e_power','power','W','Venus E',e),s('grid_power','power','W','Netzbezug / Einspeisung',c(13),'3 4'),s('a_soc','percent','%','Venus A',a),s('e_soc','percent','%','Venus E',e),...this._packs().map((p,i)=>s('a_p'+p+'_soc','percent','%','A · Pack '+p,c(i+3),i%2?'2 3':'7 3')),s('a_efficiency','percent','%','Venus A',a),s('e_efficiency','percent','%','Venus E',e),...this._packs().map((p,i)=>s('a_p'+p+'_drift','drift','mV','Venus A · Pack '+p,c(i+3),i%2?'7 3':'')),s('e_drift','drift','V','Venus E',e)];
    }
    _swatch(spec){const mark=node('svg',{class:'vs-swatch',viewBox:'0 0 24 10',width:24,height:10,'aria-hidden':'true'});mark.append(node('line',{x1:1,x2:23,y1:5,y2:5,stroke:spec.color,'stroke-width':2.5,'stroke-dasharray':spec.dash}));return mark;}
    _emphasize(key,chart='main'){const lines=this.$$('#vs-'+chart+'-chart path[data-series]');if(!lines.some(p=>p.dataset.series===key))key=null;lines.forEach(p=>{const active=p.dataset.series===key;p.style.opacity=key?(active?'1':'.18'):'1';p.style.strokeWidth=active?'3.3':'';});}
    async _refreshHistory(force=false){
      if(!this._config||!this._hass||!this.isConnected)return;
      const unique=new Map(this._requestedRanges().map(([group,range])=>[this._cacheKey(group,range),[group,range]]));
      await Promise.allSettled([...unique.values()].map(([group,range])=>this._fetch(group,force,range)));
    }
    async _fetch(group,force,range){
      const cacheKey=this._cacheKey(group,range),old=this._cache[cacheKey],now=Date.now(),signature=cacheKey+':'+this._zone();
      if(old?.signature===signature&&(old.pending||(!force&&now-old.fetched<this._config.history_refresh_seconds*1000)))return;
      const cache={signature,pending:true,fetched:0,data:old?.signature===signature?old.data:{},coveredEnd:old?.coveredEnd||range.start,error:'',loaded:0,total:0,aborted:false};this._cache[cacheKey]=cache;this._queueCharts();
      const epoch=this._epoch,specs=this._specs(group),ids=[...new Set(specs.map(s=>this._config.entities[s.key]).filter(Boolean))],queryEnd=Math.min(range.end,now),chunkMs=7*24*3600000;let timer;
      cache.total=Math.max(0,Math.ceil((queryEnd-range.start)/chunkMs));
      try{
        if(ids.length&&queryEnd>range.start&&!this._hass.callApi)throw new Error('History API nicht verfügbar');
        if(!ids.length||queryEnd<=range.start){cache.data={};cache.coveredEnd=range.start;}
        for(let start=range.start;ids.length&&start<queryEnd;start+=chunkMs){
          if(epoch!==this._epoch||this._cache[cacheKey]!==cache)return;
          if(!this._rangeNeeded(cacheKey)){cache.aborted=true;return;}
          const end=Math.min(queryEnd,start+chunkMs),params=new URLSearchParams({filter_entity_id:ids.join(','),end_time:new Date(end).toISOString(),minimal_response:'',no_attributes:''});
          let rows;try{rows=await Promise.race([this._hass.callApi('GET','history/period/'+encodeURIComponent(new Date(start).toISOString())+'?'+params),new Promise((_,reject)=>{timer=setTimeout(()=>reject(new Error('Zeitüberschreitung')),20000);})]);}finally{clearTimeout(timer);}
          if(epoch!==this._epoch||this._cache[cacheKey]!==cache)return;
          if(!this._rangeNeeded(cacheKey)){cache.aborted=true;return;}
          if(!Array.isArray(rows))throw new Error('Unerwartete History-Antwort');
          if(!cache.loaded){cache.data={};cache.coveredEnd=range.start;}
          const byId=new Map(rows.filter(Array.isArray).map(list=>[list.find(row=>row.entity_id)?.entity_id,list]));
          for(const spec of specs){const state=this._state(spec.key),points=[];for(const row of byId.get(this._config.entities[spec.key])||[]){const t=Date.parse(row.last_updated||row.last_changed);if(!Number.isFinite(t)||t>end)continue;const v=convert(num(row.state),spec.kind,state?.attributes?.unit_of_measurement||spec.unit);points.push({t,v});}points.sort((a,b)=>a.t-b.t);const before=points.filter(p=>p.t<start).at(-1),inside=points.filter(p=>p.t>=start);if(before)inside.unshift({t:start,v:before.v});const combined=[...(cache.data[spec.key]||[]),...inside];cache.data[spec.key]=thin([...new Map(combined.map(p=>[p.t,p])).values()],this._config.history_max_points);}
          cache.coveredEnd=end;cache.loaded++;this._queueCharts();
        }
      }catch(e){if(epoch===this._epoch&&this._cache[cacheKey]===cache)cache.error='Verlauf nicht abrufbar. Recorder und Leserechte prüfen.';}
      finally{clearTimeout(timer);if(epoch===this._epoch&&this._cache[cacheKey]===cache){cache.pending=false;cache.fetched=cache.aborted?0:Date.now();this._queueCharts();}}
    }
    _chartSpecs(){const group=this._group(),all=this._specs(group);if(this._mode==='power')return all.filter(s=>['a_power','e_power','grid_power'].includes(s.key));if(this._mode==='soc')return all.filter(s=>['_soc'].some(k=>s.key.endsWith(k)));if(this._mode==='efficiency')return all.filter(s=>s.key.endsWith('_efficiency'));if(this._mode==='drift')return all.filter(s=>s.key.endsWith('_drift'));return all;}
    _series(spec,group,range){
      const cache=this._cache[this._cacheKey(group,range)],raw=cache?.data?.[spec.key]||[],before=raw.filter(p=>p.t<=range.start).at(-1),points=raw.filter(p=>p.t>range.start&&p.t<=range.end).map(p=>({...p}));if(before)points.unshift({t:range.start,v:before.v});
      const factor=['a_power','e_power'].includes(spec.key)?this._sign(spec.key[0]):spec.key==='grid_power'?this._config.grid_power_sign:1;
      points.forEach(p=>{if(valid(p.v))p.v*=factor;if(spec.kind==='voltage'&&p.v<=0)p.v=null;if(spec.kind==='percent'&&valid(p.v)&&(p.v<0||p.v>100))p.v=null;});
      const recorded=points.some(p=>valid(p.v));
      if(range.fixed){const last=points.at(-1),end=Math.min(range.end,Date.now(),cache?.coveredEnd??range.start);if(last&&last.t<end)points.push({t:end,v:last.v});}
      else if(this._state(spec.key)){let current=this._read(spec.key,spec.kind,spec.unit);if(spec.kind==='percent'&&valid(current)&&(current<0||current>100))current=null;if(spec.kind==='voltage'&&current<=0)current=null;points.push({t:Math.min(range.end,Date.now()),v:valid(current)?current*factor:null});}
      return {...spec,points,recorded};
    }
    _drawChart(){
      if(!this._config||!this.$('#vs-main-chart'))return;
      const group=this._group(),cells=this._mode==='cells',unit=this._mode==='power'?'kW':this._mode==='temperature'?'°C':this._mode==='drift'?'mV':cells?'V':'%';
      this.$('#vs-chart-device').hidden=this._mode!=='temperature';this.$('#vs-history-pack').hidden=!cells;
      const suffix=this._mode==='power'?' · + Entladen / − Laden':this._mode==='soc'?' · Speicher & Packs':this._mode==='efficiency'?' · vorhandene AC-Wirkungsgrad-Sensoren':this._mode==='drift'?' · Venus A & E':cells?' · Venus A · Pack '+this.$('#vs-history-pack').value+' · 13 Einzelzellen':' · Venus '+this.$('#vs-chart-device').value.toUpperCase();
      const mainRange=this._viewRange('main');this._set('chart-caption',this._rangeLabel(mainRange)+suffix);
      this._drawPanel('main',group,this._chartSpecs(),unit,cells,this._mode==='soc',this._mode+':'+group,mainRange,'Gemeinsamer Verlauf · '+MODES[this._mode]);
      for(const pack of this._packs()){const chart='pack'+pack,range=this._viewRange(chart);this._set(chart+'-caption',this._rangeLabel(range)+' · alle 13 Einzelzellen · V');this._drawPanel(chart,'cells_'+pack,this._specs('cells_'+pack),'V',true,false,chart,range,'Venus A · Pack '+pack+' · Zellspannungen');}
    }
    _drawPanel(chart,group,specs,unit,cells,soc,key,range,label){
      const set=this._hidden.get(key)||new Set();this._hidden.set(key,set);const series=specs.map(s=>this._series(s,group,range));
      this._plot(series.filter(s=>!set.has(s.key)),unit,cells,soc,chart,range,label);
      const legend=this.$('#vs-'+chart+'-legend');
      if(legend.dataset.key!==key){legend.replaceChildren(...series.map(s=>{const b=document.createElement('button');b.type='button';b.dataset.series=s.key;b.dataset.dash=String(!!s.dash);b.style.setProperty('--vs-color',s.color);b.append(this._swatch(s),document.createTextNode(s.name));b.addEventListener('click',()=>{if(set.has(s.key))set.delete(s.key);else set.add(s.key);this._drawChart();});b.addEventListener('pointerenter',()=>this._emphasize(s.key,chart));b.addEventListener('pointerleave',()=>this._emphasize(null,chart));b.addEventListener('focus',()=>this._emphasize(s.key,chart));b.addEventListener('blur',()=>this._emphasize(null,chart));return b;}));legend.dataset.key=key;}
      [...legend.children].forEach(b=>b.setAttribute('aria-pressed',String(!set.has(b.dataset.series))));this._emphasize(legend.contains(this.shadowRoot.activeElement)?this.shadowRoot.activeElement?.dataset.series:null,chart);
      const cache=this._cache[this._cacheKey(group,range)],notes=[];if(cache?.pending)notes.push(cache.total>1?'Verlauf wird geladen ('+cache.loaded+'/'+cache.total+') …':'Verlauf wird geladen …');if(cache?.error)notes.push(cache.error+(Object.keys(cache.data).length?' Zuletzt geladene Daten bleiben sichtbar.':''));if(!cache?.pending&&!series.some(s=>s.recorded))notes.push(range.fixed?'Keine aufgezeichneten Daten für diesen Zeitraum.':'Keine aufgezeichneten Verlaufsdaten; nur aktuelle Zustände verfügbar.');if(range.fixed&&range.end>Date.now())notes.push(range.start>=Date.now()?'Der gewählte Zeitraum liegt in der Zukunft.':'Daten bis jetzt; der zukünftige Teil bleibt leer.');this._set(chart==='main'?'history-note':chart+'-note',notes.join(' '));
    }
    _plot(series,unit,cells,soc,chart,range,label){const box=this.$('#vs-'+chart+'-chart'),width=Math.floor(box.clientWidth);if(!width)return;const focused=box.contains(this.shadowRoot.activeElement);box.replaceChildren();const height=width<440?235:250,left=cells?64:width<440?45:51,right=width-10,top=20,bottom=height-31,values=series.flatMap(s=>s.points.filter(p=>valid(p.v)).map(p=>p.v)),has=values.length>0;
      const minimum=soc?0:unit==='kW'?Math.min(0,...values):Math.max(0,(has?Math.min(...values):0)-(cells?.002:unit==='°C'?2:3)),maximum=soc?100:(has?Math.max(...values):1)+(cells?.002:unit==='kW'?.3:2),rough=Math.max(.0001,(maximum-minimum)/4),mag=10**Math.floor(Math.log10(rough)),step=[1,2,2.5,5,10].map(v=>v*mag).find(v=>v>=rough)||10*mag,min=Math.floor(minimum/step)*step,max=Math.ceil(maximum/step)*step,x=t=>left+(t-range.start)/(range.end-range.start)*(right-left),y=v=>bottom-(v-min)/(max-min)*(bottom-top);
      const clipId=this._chartId+'-'+chart+'-clip';const svg=node('svg',{viewBox:`0 0 ${width} ${height}`,role:'img',tabindex:0,'aria-label':`${label}. ${this._rangeLabel(range)}. Verlauf in ${unit}. Mit Pfeiltasten Werte erkunden.`}),defs=node('defs'),clip=node('clipPath',{id:clipId});clip.append(node('rect',{x:left,y:top,width:right-left,height:bottom-top}));defs.append(clip);svg.append(defs);
      for(let i=0;i<=4;i++){const v=min+(max-min)*i/4,yy=y(v);svg.append(node('line',{x1:left,x2:right,y1:yy,y2:yy,stroke:'var(--vs-line)','stroke-width':1}),node('text',{x:left-9,y:yy+4,'text-anchor':'end'},fmt(v,cells?3:unit==='kW'?1:0)));}svg.append(node('text',{x:left,y:11},unit));const ticks=width<440?3:5;for(let i=0;i<ticks;i++){const t=range.start+(range.end-range.start)*i/(ticks-1);svg.append(node('text',{x:x(t),y:height-9,'text-anchor':i===0?'start':i===ticks-1?'end':'middle'},range.hours>24?this._dateLabel(t):this._clock(t)));}
      series.forEach(s=>{const d=pathFor(s.points,x,y);if(d)svg.append(node('path',{d,fill:'none',stroke:s.color,'stroke-width':s.key==='grid_power'?1.7:2.2,'stroke-dasharray':s.dash,'clip-path':'url(#'+clipId+')','data-series':s.key}));const last=s.points[s.points.length-1];if(last&&valid(last.v))svg.append(node('circle',{cx:x(last.t),cy:y(last.v),r:2.4,fill:s.color}));});if(!has||!series.some(s=>s.recorded))svg.append(node('text',{x:(left+right)/2,y:(top+bottom)/2,'text-anchor':'middle'},!series.length?'Alle Kurven ausgeblendet':!has?'Keine Verlaufsdaten verfügbar':'Nur aktuelle Werte · kein Verlauf'));
      const guide=node('line',{x1:left,x2:left,y1:top,y2:bottom,stroke:'var(--vs-sub)','stroke-dasharray':'3 3',visibility:'hidden'});svg.append(guide);const tip=document.createElement('div');tip.className='vs-tooltip';tip.dataset.cells=String(cells);tip.setAttribute('role','tooltip');tip.hidden=true;box.append(svg,tip);
      const show=fraction=>{box._cursor=fraction;box._cursorActive=true;const xx=Math.min(right,Math.max(left,fraction*width)),t=range.start+(xx-left)/(right-left)*(range.end-range.start);guide.setAttribute('x1',xx);guide.setAttribute('x2',xx);guide.setAttribute('visibility','visible');tip.replaceChildren();const title=document.createElement('strong');title.textContent=this._dateLabel(t)+' · '+this._clock(t);tip.append(title);series.forEach(s=>{const row=document.createElement('div');row.className='vs-tip-row';const name=document.createElement('span'),dot=document.createElement('span');name.className='vs-tip-name';dot.className='vs-tip-dot';dot.style.background=s.color;dot.setAttribute('aria-hidden','true');name.append(dot,document.createTextNode(s.name));const value=entityInfoButton(this,[s.key],s.name,fmt(stateAt(s.points,t),cells?3:unit==='kW'?2:1)+' '+unit);row.append(name,value);tip.append(row);});tip.hidden=false;tip.style.top='23px';tip.style.left=Math.max(0,Math.min(width-tip.offsetWidth,xx+12))+'px';};
      svg.addEventListener('pointermove',e=>{const r=svg.getBoundingClientRect();show((e.clientX-r.left)/r.width);});svg.addEventListener('pointerdown',e=>{const r=svg.getBoundingClientRect();show((e.clientX-r.left)/r.width);});box.onpointerleave=e=>{if(e.pointerType==='touch')return;box._cursorActive=false;tip.hidden=true;guide.setAttribute('visibility','hidden');};let cursor=.5;svg.addEventListener('keydown',e=>{if(e.key==='Escape'){box._cursorActive=false;tip.hidden=true;guide.setAttribute('visibility','hidden');return;}if(!['ArrowLeft','ArrowRight'].includes(e.key))return;e.preventDefault();cursor=Math.min(1,Math.max(0,cursor+(e.key==='ArrowRight'?.02:-.02)));show((left+cursor*(right-left))/width);this._set('live',tip.textContent);});if(focused)svg.focus({preventScroll:true});if(box._cursorActive&&valid(box._cursor))show(box._cursor);
    }
  }
  if(!customElements.get(TAG))customElements.define(TAG,VenusSpeicherCockpitCard);
})();

