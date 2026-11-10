#!/usr/bin/env node

const fs = require("fs");
const path = require("path");

function fail(message) {
  console.error(`Maimemo Table: ${message}`);
  process.exit(1);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;")
    .replaceAll("\n", "<br>");
}

function loadPlaywright() {
  const home = process.env.USERPROFILE || process.env.HOME || "";
  const candidates = [
    "playwright",
    path.join(home, ".cache", "codex-runtimes", "codex-primary-runtime",
      "dependencies", "node", "node_modules", "playwright"),
    path.join(__dirname, "..", "node_modules", "playwright"),
    path.join(process.cwd(), "node_modules", "playwright"),
    process.env.MEMO_CANVAS_PLAYWRIGHT || "",
  ].filter(Boolean);
  const errors = [];
  for (const candidate of candidates) {
    try {
      return require(candidate);
    } catch (error) {
      errors.push(`${candidate}: ${error.code || error.message}`);
    }
  }
  throw new Error(errors.join("; "));
}

function findBrowser() {
  const candidates = [
    process.env.MAIMEMO_TABLE_BROWSER,
    "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
    "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
    "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
  ].filter(Boolean);
  return candidates.find((candidate) => fs.existsSync(candidate));
}

const [, , inputArg, pngArg, htmlArg] = process.argv;
if (!inputArg || !pngArg) {
  fail("usage: node render_table.cjs <input.json> <output.png> [output.html]");
}

const inputPath = path.resolve(inputArg);
const pngPath = path.resolve(pngArg);
const htmlPath = path.resolve(
  htmlArg || path.join(path.dirname(pngPath), `${path.basename(pngPath, path.extname(pngPath))}.html`),
);

let data;
try {
  data = JSON.parse(fs.readFileSync(inputPath, "utf8"));
} catch (error) {
  fail(`cannot read valid UTF-8 JSON from ${inputPath}: ${error.message}`);
}

if (typeof data.title !== "string" || !data.title.trim()) fail("title must be a non-empty string");
if (!Array.isArray(data.headers) || data.headers.length < 2) fail("headers must contain at least two columns");
if (!Array.isArray(data.rows) || data.rows.length === 0) fail("rows must be a non-empty array");
for (const [index, row] of data.rows.entries()) {
  if (!Array.isArray(row) || row.length !== data.headers.length) {
    fail(`row ${index + 1} must contain exactly ${data.headers.length} cells`);
  }
}
if (data.metrics !== undefined) {
  if (!Array.isArray(data.metrics) || data.metrics.length > 2) fail("metrics must be an array of at most two items");
  for (const metric of data.metrics) {
    if (!metric || typeof metric.value !== "string" || typeof metric.caption !== "string") {
      fail("each metric needs string `value` and `caption`");
    }
  }
}

const defaults = { accent: "#36b59d", light: "#e6f3f0", deep: "#247465", white: "#ffffff" };
const theme = { ...defaults, ...(data.theme || {}) };
for (const [key, value] of Object.entries(theme)) {
  if (!/^#[0-9a-fA-F]{6}$/.test(value)) fail(`theme.${key} must be a six-digit hex color`);
}

// The locked three styles live in scripts/locked/render.cjs; this renderer only keeps "rounded".
const requested = data.style || data.cornerStyle || "rounded";
if (requested !== "rounded") {
  fail('this renderer only handles "rounded"; table/comparison/sales use scripts/locked/render.cjs');
}
const styleName = "rounded";
const width = Number.isInteger(data.width) && data.width >= 800 ? data.width : 2000;
if (data.fontFamily !== undefined) {
  if (typeof data.fontFamily !== "string" || data.fontFamily.length > 200 ||
      !/^[A-Za-z0-9 \t,'"._-]+$/.test(data.fontFamily)) {
    fail("fontFamily must be a plain CSS font stack (letters, digits, spaces, commas, quotes, dots or hyphens; max 200 characters)");
  }
}
const fontFamily = data.fontFamily || '"Microsoft YaHei", "Noto Sans CJK SC", sans-serif';
const headerHtml = data.headers.map((cell) => `<th scope="col">${escapeHtml(cell)}</th>`).join("");

function roundedHtml() {
  const css = fs.readFileSync(path.join(__dirname, "..", "assets", "table-theme.css"), "utf8");
  const otherWidth = (87 / (data.headers.length - 1)).toFixed(6);
  const columns = ["<col>", ...data.headers.slice(1).map(() => `<col style="width:${otherWidth}%">`)].join("");
  const bodyHtml = data.rows
    .map((row) => {
      const [label, ...cells] = row;
      return `<tr><th scope="row">${escapeHtml(label)}</th>${cells.map((cell) => `<td>${escapeHtml(cell)}</td>`).join("")}</tr>`;
    })
    .join("\n");
  return `<!doctype html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>${escapeHtml(data.title)}</title>
<style>
:root { --mt-accent:${theme.accent}; --mt-light:${theme.light}; --mt-deep:${theme.deep}; --mt-white:${theme.white}; --mt-font:${fontFamily}; }
${css}
</style></head>
<body>
<main id="maimemo-table" data-corner-style="rounded">
  <h1>${escapeHtml(data.title)}</h1>
  <table aria-label="${escapeHtml(data.title)}"><colgroup>${columns}</colgroup>
    <thead><tr>${headerHtml}</tr></thead><tbody>${bodyHtml}</tbody>
  </table>
</main>
</body></html>`;
}

function salesHtml() {
  const rest = data.headers.length - 1;
  const grid = `96px 27% repeat(${rest}, minmax(0, 1fr))`;
  const head = `<div class="ms-head" style="grid-template-columns:${grid}">
    <span></span><span class="ms-head-name">${escapeHtml(data.headers[0])}</span>
    ${data.headers.slice(1).map((cell) => `<span class="ms-head-value">${escapeHtml(cell)}</span>`).join("")}
  </div>`;
  const rows = data.rows
    .map((row, index) => {
      const [label, ...cells] = row;
      const [name, ...description] = String(label).split("\n");
      const desc = description.length ? `<div class="ms-desc">${escapeHtml(description.join(" "))}</div>` : "";
      return `<div class="ms-row" style="grid-template-columns:${grid}">
    <div class="ms-index">${index + 1}</div>
    <div class="ms-name"><div class="ms-name-main">${escapeHtml(name)}</div>${desc}</div>
    ${cells.map((cell) => `<div class="ms-value">${escapeHtml(cell)}</div>`).join("")}
  </div>`;
    })
    .join("\n");
  return `<!doctype html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>${escapeHtml(data.title)}</title>
<style>
html,body{margin:0;padding:0;background:transparent}
#memo-sales{box-sizing:border-box;width:100%;padding:44px 56px 52px;background:transparent;font-family:${fontFamily};color:#3c4a46}
#memo-sales *{box-sizing:border-box}
.ms-top{display:flex;justify-content:space-between;align-items:center;gap:24px;margin-bottom:20px}
.ms-title{margin:0;min-height:64px;padding:0 34px;display:flex;align-items:center;justify-content:center;background:#5d5d5d;border-radius:16px;color:#f3faf8;font-size:30px;line-height:1.25;font-weight:700}
.ms-dots{display:flex;gap:10px;align-items:center;height:40px;padding:0 18px;border-radius:20px;background:#5d5d5d;flex:none}
.ms-dots i{width:12px;height:12px;border-radius:50%;background:${theme.accent}}
.ms-dots i:nth-child(2){background:#ea9d29}.ms-dots i:nth-child(3){background:#da643f}
.ms-head{display:grid;align-items:center;gap:0;padding:0 20px 10px 0;color:#8a9691;font-size:15px}
.ms-head-name{padding-left:8px}.ms-head-value{text-align:center}
.ms-row{display:grid;align-items:center;gap:0;min-height:92px;margin-bottom:16px;padding-right:20px;border-radius:16px;background:#fff;box-shadow:0 2px 6px #2239330c,0 10px 20px #22393312;font-size:19px}
.ms-index{justify-self:center;width:48px;height:48px;border-radius:50%;background:#e3f4ef;color:#269780;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:20px}
.ms-name-main{font-size:23px;color:#269780;font-weight:700}
.ms-desc{margin-top:4px;font-size:14px;color:#7b8984}
.ms-value{text-align:center;font-weight:600;color:#3c4a46;overflow-wrap:anywhere;padding:8px 6px}
.ms-row:last-child{margin-bottom:0;background:${theme.accent};color:#fff;box-shadow:0 3px 8px #22393312,0 14px 26px #22393322}
.ms-row:last-child .ms-index{background:#fff;color:#269780}
.ms-row:last-child .ms-name-main,.ms-row:last-child .ms-desc,.ms-row:last-child .ms-value{color:#fff}
</style></head>
<body><main id="memo-sales">
  <header class="ms-top"><h1 class="ms-title">${escapeHtml(data.title)}</h1>
    <div class="ms-dots" aria-hidden="true"><i></i><i></i><i></i></div></header>
  ${head}${rows}
</main></body></html>`;
}

function tableHtml() {
  const metrics = Array.isArray(data.metrics) ? data.metrics : [];
  const cols = data.headers.length;
  const grid = `76px repeat(${cols}, minmax(0, 1fr))`;
  const head = `<div class="mt-head" style="grid-template-columns:${grid}">
    <span class="mt-th">NO</span>${data.headers.map((cell) => `<span class="mt-th">${escapeHtml(cell)}</span>`).join("")}
  </div>`;
  const rows = data.rows
    .map((row, index) => `<div class="mt-row" style="grid-template-columns:${grid}">
      <span class="mt-index">${index + 1}</span>${row.map((cell) => `<span class="mt-cell">${escapeHtml(cell)}</span>`).join("")}
    </div>`)
    .join("\n");
  const metricHtml = metrics.length
    ? `<aside class="mt-metrics">${metrics.map((metric) => `<div class="mt-metric">
        <div class="mt-icon"><i></i><i></i><i></i></div>
        <div class="mt-metric-value">${escapeHtml(metric.value)}</div>
        <div class="mt-metric-caption">${escapeHtml(metric.caption)}</div>
      </div>`).join("")}</aside>`
    : "";
  return `<!doctype html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>${escapeHtml(data.title)}</title>
<style>
html,body{margin:0;padding:0}
#memo-table-style{box-sizing:border-box;width:100%;padding:40px;background:#f2f5f4;font-family:${fontFamily}}
#memo-table-style *{box-sizing:border-box}
.mt-card{background:#fff;border-radius:24px;overflow:hidden;box-shadow:0 18px 40px #2239331f}
.mt-bar{height:96px;display:flex;align-items:center;justify-content:space-between;padding:0 36px;background:#5d5d5d;color:#f3faf8}
.mt-bar h1{margin:0;font-size:34px;font-weight:700}
.mt-dots{display:flex;gap:12px;align-items:center}
.mt-dots i{width:14px;height:14px;border-radius:50%;background:${theme.accent}}
.mt-dots i:nth-child(2){background:#ea9d29}.mt-dots i:nth-child(3){background:#da643f}
.mt-body{display:grid;grid-template-columns:1fr;gap:36px;padding:32px 36px 36px}
.mt-body.with-metrics{grid-template-columns:minmax(0,1fr) 250px}
.mt-head{display:grid;gap:8px;margin-bottom:10px}
.mt-th{background:${theme.accent};color:#fff;text-align:center;padding:18px 10px;border-radius:10px;font-size:24px;font-weight:700;overflow-wrap:anywhere}
.mt-row{display:grid;align-items:center;gap:8px;padding:14px 0;border-bottom:1px solid #eef2f0}
.mt-index{text-align:center;font-weight:700;font-size:22px;color:#555f5d}
.mt-cell{text-align:center;font-size:22px;color:#555f5d;overflow-wrap:anywhere;padding:0 6px}
.mt-metrics{display:flex;flex-direction:column;justify-content:space-around;gap:30px}
.mt-icon{width:64px;height:64px;border-radius:14px;background:${theme.accent};display:flex;align-items:flex-end;justify-content:center;gap:4px;padding-bottom:16px}
.mt-icon i{width:7px;background:#fff;border-radius:2px}
.mt-icon i:nth-child(1){height:14px}.mt-icon i:nth-child(2){height:24px}.mt-icon i:nth-child(3){height:18px}
.mt-metric-value{margin-top:14px;font-size:46px;font-weight:700;color:#3f514c}
.mt-metric-caption{margin-top:6px;font-size:16px;line-height:1.5;color:#7b8984}
</style></head>
<body><main id="memo-table-style"><div class="mt-card">
  <header class="mt-bar"><h1>${escapeHtml(data.title)}</h1>
    <div class="mt-dots" aria-hidden="true"><i></i><i></i><i></i></div></header>
  <div class="mt-body${metrics.length ? " with-metrics" : ""}">
    <div class="mt-table">${head}${rows}</div>
    ${metricHtml}
  </div>
</div></main></body></html>`;
}

function comparisonHtml() {
  const values = data.headers.length - 1;
  const grid = `minmax(150px, 1.1fr) repeat(${values}, minmax(0, 1fr))`;
  const head = `<div class="cx-head" style="grid-template-columns:${grid}">
    ${data.headers.map((cell) => `<span>${escapeHtml(cell)}</span>`).join("")}
  </div>`;
  const rows = data.rows
    .map((row, index) => {
      const [label, ...cells] = row;
      const delta = cells.length > 1 ? cells.pop() : null;
      const cellsHtml = cells
        .map((cell, cellIndex) => `<div class="cx-value">${cellIndex > 0 ? '<span class="cx-arrow"></span>' : ""}${escapeHtml(cell)}</div>`)
        .join("");
      return `<div class="cx-row${index === 0 ? " cx-first" : ""}" style="grid-template-columns:${grid}">
        <div class="cx-label">${escapeHtml(label)}</div>${cellsHtml}
        ${delta === null ? "" : `<div class="cx-delta">${escapeHtml(delta)}</div>`}
      </div>`;
    })
    .join("\n");
  return `<!doctype html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>${escapeHtml(data.title)}</title>
<style>
html,body{margin:0;padding:0}
#memo-comparison{box-sizing:border-box;width:100%;padding:48px;background:#f2f5f4;font-family:${fontFamily}}
#memo-comparison *{box-sizing:border-box}
.cx-card{background:#5d5d5d;border-radius:36px;padding:44px 40px 48px;box-shadow:0 20px 44px #22393326}
.cx-top{display:flex;justify-content:space-between;align-items:center;gap:24px;margin-bottom:30px}
.cx-top h1{margin:0;font-size:30px;line-height:1.35;font-weight:600;color:#f3faf8}
.cx-dots{display:flex;gap:10px;align-items:center;height:40px;padding:0 18px;border-radius:20px;background:#7c8380;flex:none}
.cx-dots i{width:12px;height:12px;border-radius:50%;background:${theme.accent}}
.cx-dots i:nth-child(2){background:#ea9d29}.cx-dots i:nth-child(3){background:#da643f}
.cx-head{display:grid;align-items:center;gap:12px;margin:0 8px 14px;color:#cfd6d2;font-size:18px}
.cx-head span{text-align:center}
.cx-head span:first-child{text-align:left}
.cx-row{display:grid;align-items:stretch;gap:0;min-height:98px;margin-bottom:16px;border-radius:44px;background:#8a9391;color:#fff}
.cx-row.cx-first{background:#fff;color:#3c4a46}
.cx-label{display:flex;align-items:center;justify-content:center;margin:8px;padding:0 18px;border-radius:40px;background:#9aa3a0;font-size:24px;font-weight:700;text-align:center;overflow-wrap:anywhere}
.cx-first .cx-label{background:#e9f2ef;color:#269780}
.cx-value{display:flex;align-items:center;justify-content:center;gap:10px;font-size:24px;font-weight:600;padding:0 6px;overflow-wrap:anywhere}
.cx-arrow{flex:none;width:44px;height:2px;background:currentColor;opacity:.55;position:relative}
.cx-arrow::after{content:"";position:absolute;right:-1px;top:-4px;border-left:9px solid currentColor;border-top:5px solid transparent;border-bottom:5px solid transparent}
.cx-delta{display:flex;align-items:center;justify-content:center;border-radius:0 44px 44px 0;background:#9aa3a0;font-size:22px;font-weight:700;padding:0 10px;overflow-wrap:anywhere}
.cx-first .cx-delta{background:${theme.accent};color:#fff}
</style></head>
<body><main id="memo-comparison"><div class="cx-card">
  <header class="cx-top"><h1>${escapeHtml(data.title)}</h1>
    <div class="cx-dots" aria-hidden="true"><i></i><i></i><i></i></div></header>
  ${head}${rows}
</div></main></body></html>`;
}

const builders = { rounded: roundedHtml, table: tableHtml, comparison: comparisonHtml, sales: salesHtml };
const selectors = { rounded: "#maimemo-table", table: "#memo-table-style", comparison: "#memo-comparison", sales: "#memo-sales" };
const html = builders[styleName]();
const selector = selectors[styleName];

fs.mkdirSync(path.dirname(htmlPath), { recursive: true });
fs.mkdirSync(path.dirname(pngPath), { recursive: true });
fs.writeFileSync(htmlPath, html, "utf8");

let chromium;
try {
  chromium = loadPlaywright().chromium;
} catch (error) {
  fail("the playwright package is unavailable; set NODE_PATH to a node_modules directory containing playwright");
}

const executablePath = findBrowser();
if (!executablePath) {
  fail("no supported local Chrome, Edge, or Chromium executable was found; set MAIMEMO_TABLE_BROWSER to its absolute path");
}

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath });
  try {
    const page = await browser.newPage({ viewport: { width, height: 1800 }, deviceScaleFactor: 1,
      javaScriptEnabled: false });
    await page.route("**/*", (route) => {
      const url = route.request().url();
      return url.startsWith("file:") || url.startsWith("data:") ? route.continue() : route.abort();
    });
    await page.goto(`file:///${htmlPath.replaceAll("\\", "/")}`);
    await page.locator(selector).screenshot({ path: pngPath, omitBackground: true });
  } finally {
    await browser.close();
  }
  console.log(JSON.stringify({ png: pngPath, html: htmlPath, width, style: styleName }));
})().catch((error) => fail(error.message));
