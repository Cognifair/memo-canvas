/* Local, non-browser renderers. Inputs are data, never shell commands. */
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const {createRequire} = require('node:module');
const dep = createRequire(path.join(__dirname, '../toolchain/package.json'));
const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&apos;'}[c]));

function safeSvg(svg) {
  if (Buffer.byteLength(svg) > 4_000_000 || /<!DOCTYPE|<!ENTITY|<\?(?!xml\s)/i.test(svg)) throw Error('SVG too large or contains DTD/entities/processing instructions');
  const {DOMParser} = dep('@xmldom/xmldom');
  const doc = new DOMParser({onError: level => {throw Error(`Invalid XML: ${level}`);}}).parseFromString(svg, 'image/svg+xml');
  const allowed = new Set('svg g defs path rect circle ellipse line polyline polygon text tspan title desc marker clipPath linearGradient radialGradient stop use'.split(' '));
  function visit(el) {
    if (!allowed.has(el.localName) || (el.namespaceURI && el.namespaceURI !== 'http://www.w3.org/2000/svg')) throw Error(`Unsupported SVG element: ${el.nodeName}`);
    for (const a of Array.from(el.attributes || [])) {
      if (a.name === 'style' && /[\\@()\/]/.test(a.value)) throw Error('Complex SVG styles forbidden; use simple presentation attributes');
      if (/^on/i.test(a.name) || /(?:href)$/i.test(a.name) && !/^#[\w:.-]+$/.test(a.value)) throw Error('SVG scripts/external resources forbidden');
      if (/url\s*\(/i.test(a.value) && !/^\s*url\(#[\w:.-]+\)\s*$/.test(a.value)) throw Error('External SVG URL forbidden');
      if (/@import|javascript:|data:|https?:|file:/i.test(a.value) && !/^xmlns(?::\w+)?$/.test(a.name)) throw Error('External resource forbidden');
    }
    for (const child of Array.from(el.childNodes)) if (child.nodeType === 1) visit(child);
  }
  if (doc.documentElement.localName !== 'svg') throw Error('Expected SVG root');
  visit(doc.documentElement);
  return svg;
}

async function formula(tex, size) {
  if (!tex.trim() || tex.length > 20000) throw Error('LaTeX must contain 1..20000 characters');
  const {mathjax} = dep('mathjax-full/js/mathjax.js');
  const {TeX} = dep('mathjax-full/js/input/tex.js');
  dep('mathjax-full/js/input/tex/ams/AmsConfiguration.js');
  const {SVG} = dep('mathjax-full/js/output/svg.js');
  const {liteAdaptor} = dep('mathjax-full/js/adaptors/liteAdaptor.js');
  const {RegisterHTMLHandler} = dep('mathjax-full/js/handlers/html.js');
  const adaptor = liteAdaptor(); RegisterHTMLHandler(adaptor);
  const input = new TeX({packages:['base','ams'], maxBuffer:20000, formatError:(_jax, e) => {throw e;}});
  const document = mathjax.document('', {InputJax:input, OutputJax:new SVG({fontCache:'none'})});
  const container = document.convert(tex, {display:true, em:size, ex:size/2, containerWidth:1200});
  const svg = adaptor.firstChild(container);
  // MathJax emits ex units; normalize to pixels for consistent raster dimensions.
  for (const dim of ['width','height']) {
    const v = adaptor.getAttribute(svg, dim);
    if (v && v.endsWith('ex')) adaptor.setAttribute(svg, dim, `${parseFloat(v)*size/2}px`);
  }
  return adaptor.outerHTML(svg);
}

async function flow(graph) {
  if (!graph || !Array.isArray(graph.nodes) || !Array.isArray(graph.edges) || !graph.nodes.length || graph.nodes.length > 150 || graph.edges.length > 400) throw Error('Expected 1..150 nodes and at most 400 edges');
  if (graph.groups || graph.nodes.some(n => n.group)) throw Error('Groups/swimlanes are not supported; use a reviewed SVG instead');
  if (graph.direction != null && !['LR','TB'].includes(graph.direction)) throw Error('Direction must be LR or TB');
  const ids = new Set();
  const shapes = {rect:'box', decision:'diamond', start:'ellipse', end:'ellipse'};
  const labels = new Map();
  const sharp = dep('sharp');
  async function measure(text, size) {
    const lines = text.split(/\r?\n/);
    let width = 1;
    for (const line of lines) if (line.trim()) {
      const {info} = await sharp({text:{text:esc(line),font:`Microsoft YaHei ${size}`,dpi:72}}).png().toBuffer({resolveWithObject:true});
      width = Math.max(width, info.width);
    }
    return {lines, size, width:width+32, height:lines.length*size*1.5+24};
  }
  let dot = `digraph G { graph [rankdir=${graph.direction === 'LR' ? 'LR' : 'TB'}, bgcolor="transparent", pad="0.3", nodesep="0.55", ranksep="0.7"]; node [fontname="Microsoft YaHei", fontsize=18, margin="0.2,0.12", style="filled", fillcolor="#f4f7f5", color="#46675c"]; edge [fontname="Microsoft YaHei", fontsize=15, color="#46675c"];\n`;
  const literal = s => JSON.stringify(s); // DOT quoted strings; never interpolate raw input.
  for (const n of graph.nodes) {
    if (typeof n.id !== 'string' || !/^[A-Za-z][A-Za-z0-9_-]{0,63}$/.test(n.id) || ids.has(n.id)) throw Error('Invalid/duplicate node ID');
    if (typeof n.text !== 'string' || n.text.length > 500 || !shapes[n.shape || 'rect']) throw Error('Invalid node text/shape');
    ids.add(n.id);
    const m = await measure(n.text,18);
    labels.set(`mc-node-${n.id}`,m);
    const factor = n.shape === 'decision' ? 2 : ['start','end'].includes(n.shape) ? 1.45 : 1;
    dot += `${literal(n.id)} [id="mc-node-${n.id}", shape=${shapes[n.shape || 'rect']}, fixedsize=true, width=${m.width*factor/72}, height=${m.height*factor/72}, label=""];\n`;
  }
  for (const [index,e] of graph.edges.entries()) {
    if (!ids.has(e.from) || !ids.has(e.to) || e.label != null && (typeof e.label !== 'string' || e.label.length > 150) || e.directed != null && typeof e.directed !== 'boolean') throw Error('Invalid edge endpoint/label/direction');
    const m = await measure(e.label || '',15);
    labels.set(`mc-edge-${index}`,m);
    const label = e.label ? `<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="0" FIXEDSIZE="TRUE" WIDTH="${Math.ceil(m.width)}" HEIGHT="${Math.ceil(m.height)}"><TR><TD> </TD></TR></TABLE>>` : '""';
    dot += `${literal(e.from)} -> ${literal(e.to)} [id="mc-edge-${index}", dir=${e.directed === false ? 'none' : 'forward'}, label=${label}];\n`;
  }
  dot += '}';
  const {instance} = dep('@viz-js/viz');
  const viz = await instance();
  let svg = viz.renderString(dot, {format:'svg', engine:'dot'}).replace(/<!DOCTYPE[^>]*>/g, '');
  // WASM Graphviz does not measure CJK with the host font. Reserve measured boxes,
  // then anchor host-rendered text at the exact node/edge-label centers.
  const layout = viz.renderJSON(dot, {engine:'dot'});
  const {DOMParser, XMLSerializer} = dep('@xmldom/xmldom');
  const document = new DOMParser().parseFromString(svg,'image/svg+xml');
  for (const obj of [...(layout.objects || []), ...(layout.edges || [])]) {
    const m = labels.get(obj.id);
    const position = obj.lp || obj.pos;
    if (!m || !position || !m.lines.some(Boolean)) continue;
    const group = document.getElementById(obj.id);
    const [x,y] = position.split(',').map(Number);
    // Remove placeholder spaces; paths/polygons remain unchanged.
    for (const text of Array.from(group.getElementsByTagName('text'))) group.removeChild(text);
    m.lines.forEach((line,i) => {
      const el = document.createElementNS('http://www.w3.org/2000/svg','text');
      for (const [key,value] of Object.entries({x,y:-y+(i-(m.lines.length-1)/2)*m.size*1.5+m.size*.35,'text-anchor':'middle','font-family':'Microsoft YaHei','font-size':m.size,fill:'#17251f'})) el.setAttribute(key,String(value));
      el.appendChild(document.createTextNode(line)); group.appendChild(el);
    });
  }
  svg = new XMLSerializer().serializeToString(document);
  return {svg, dot};
}

async function render(mode, input, output, size=32) {
  if (!['formula','svg','flowchart'].includes(mode)) throw Error('Unknown renderer');
  if (!Number.isInteger(size) || size < 12 || size > 96) throw Error('Size must be 12..96');
  const suffix = path.extname(output).toLowerCase();
  if (!['.svg','.png'].includes(suffix)) throw Error('Output must be SVG or PNG');
  const sourceFile = output + (mode === 'formula' ? '.tex' : mode === 'flowchart' ? '.graph.json' : '.source.svg');
  const metadata = output + '.json';
  const targets = [output, sourceFile, metadata];
  for (const p of targets) if (fs.existsSync(p)) throw Error(`Refusing to overwrite: ${p}`);
  if (fs.statSync(input).size > 4_000_000) throw Error('Input exceeds 4 MB');
  const source = fs.readFileSync(input, 'utf8');
  let svg = mode === 'formula' ? await formula(source, size) : mode === 'flowchart' ? (await flow(JSON.parse(source))).svg : source;
  svg = safeSvg(svg);
  let data = Buffer.from(svg);
  if (suffix === '.png') {
    const sharp = dep('sharp');
    data = await sharp(data, {density:144, limitInputPixels:40_000_000}).png().toBuffer();
  }
  const result = {mode, output:path.resolve(output), editable_source:path.resolve(sourceFile), source_verified:false, visual_audit:'not_checked', note:'Rendering is not source recognition or fidelity verification'};
  for (const p of targets) fs.mkdirSync(path.dirname(p), {recursive:true});
  fs.writeFileSync(output, data, {flag:'wx'});
  fs.writeFileSync(sourceFile, source, {flag:'wx'});
  fs.writeFileSync(metadata, JSON.stringify(result, null, 2), {flag:'wx'});
  return result;
}

if (require.main === module) {
  const [mode, input, output, size] = process.argv.slice(2);
  (async () => {
    if (mode === 'doctor') {
      const report = {};
      for (const name of ['mathjax-full','@viz-js/viz','sharp','@xmldom/xmldom']) {
        try {dep(name === 'mathjax-full' ? 'mathjax-full/js/mathjax.js' : name); report[name] = 'loadable';} catch(e) {report[name] = `missing_or_broken: ${e.message}`;}
      }
      console.log(JSON.stringify(report)); return;
    }
    if (!input || !output) throw Error('Usage: canvas_render.cjs formula|svg|flowchart INPUT OUTPUT [FONT_SIZE]');
    console.log(JSON.stringify(await render(mode, input, output, size ? Number(size) : 32), null, 2));
  })().catch(e => {console.error(e.message); process.exitCode=1;});
}
module.exports = {safeSvg, formula, flow, render};
