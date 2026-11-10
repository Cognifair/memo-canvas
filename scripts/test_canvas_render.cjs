'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {createRequire} = require('node:module');
const dep = createRequire(path.join(__dirname, '../toolchain/package.json'));
const {safeSvg, formula, flow, render} = require('./canvas_render.cjs');
const svg = '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100"><rect width="100" height="50" fill="green"/></svg>';

test('valid local geometry', () => assert.equal(safeSvg(svg), svg));
for (const [name, value] of Object.entries({
  script:'<svg><script>alert(1)</script></svg>', event:'<svg onload="alert(1)"/>',
  external:'<svg><use href="file:///secret"/></svg>', foreign:'<svg><foreignObject/></svg>',
  entity:'<!DOCTYPE svg [<!ENTITY x SYSTEM "file:///secret">]><svg/>',
  css:'<svg><rect style="fill:url(https://example.com/a)"/></svg>', malformed:'<svg><g></svg>'
})) test(`reject ${name}`, () => assert.throws(() => safeSvg(value)));
test('formula vector glyphs and invalid TeX', async () => {
  const result = await formula('\\frac{-b \\pm \\sqrt{b^2-4ac}}{2a}', 32);
  assert.match(safeSvg(result), /<path/);
  assert.match(safeSvg(await formula('\\begin{aligned}x&=1\\\\y&=2\\end{aligned}',32)), /<path/);
  await assert.rejects(() => formula('\\invalidcommand{x}', 32));
});
test('flow preserves labels, loops and undirected edges', async () => {
  const result = await flow({nodes:[{id:'a',text:'A & <B>',shape:'decision'},{id:'b',text:'Finish',shape:'end'}], edges:[{from:'a',to:'b',label:'yes'},{from:'b',to:'a',label:'retry'},{from:'a',to:'a',directed:false}]});
  assert.match(safeSvg(result.svg), /A &amp; &lt;B&gt;/);
  assert.match(result.dot, /dir=none/);
  assert.match(result.svg, /retry/);
});
test('flow rejects invented endpoint, duplicate ID, unsupported groups', async () => {
  await assert.rejects(() => flow({nodes:[{id:'a',text:'a'}],edges:[{from:'a',to:'b'}]}));
  await assert.rejects(() => flow({nodes:[{id:'a',text:'a'},{id:'a',text:'b'}],edges:[]}));
  await assert.rejects(() => flow({nodes:[{id:'a',text:'a',group:'lane'}],edges:[]}));
});
test('CJK nodes reserve host-font dimensions and center text', async () => {
  const label='核对内容与视觉';
  const result=await flow({nodes:[{id:'cjk',text:label}],edges:[]});
  const {DOMParser}=dep('@xmldom/xmldom');
  const doc=new DOMParser().parseFromString(result.svg,'image/svg+xml');
  const group=doc.getElementById('mc-node-cjk');
  const text=group.getElementsByTagName('text')[0];
  assert.equal(text.getAttribute('text-anchor'),'middle');
  const coords=group.getElementsByTagName('polygon')[0].getAttribute('points').trim().split(/\s+/).map(p=>Number(p.split(',')[0]));
  const {info}=await dep('sharp')({text:{text:label,font:'Microsoft YaHei 18',dpi:72}}).png().toBuffer({resolveWithObject:true});
  assert.ok(Math.max(...coords)-Math.min(...coords)>=info.width+30);
  assert.ok(Math.abs(Number(text.getAttribute('x'))-(Math.max(...coords)+Math.min(...coords))/2)<0.1);
});
test('raster dimensions, source retention, no overwrite', async () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'memo-canvas-test-'));
  try {
    const input=path.join(tmp,'input.svg'), output=path.join(tmp,'result.png');
    fs.writeFileSync(input,svg);
    const result = await render('svg', input, output);
    const metadata = await dep('sharp')(output).metadata();
    assert.equal(metadata.width,400); assert.equal(metadata.height,200);
    assert.equal(result.source_verified,false);
    assert.equal(fs.readFileSync(result.editable_source,'utf8'),svg);
    const before=fs.readFileSync(output);
    await assert.rejects(() => render('svg', input, output));
    assert.deepEqual(fs.readFileSync(output),before);
  } finally {fs.rmSync(tmp,{recursive:true,force:true});}
});
test('invalid suffix, size and huge canvas rejected before writes', async () => {
  const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'memo-canvas-test-'));
  try {
    const input=path.join(tmp,'huge.svg');
    fs.writeFileSync(input,svg.replace('width="200" height="100"','width="100000" height="100000"'));
    await assert.rejects(() => render('svg',input,path.join(tmp,'bad.jpg')));
    await assert.rejects(() => render('svg',input,path.join(tmp,'bad.png'),0));
    await assert.rejects(() => render('svg',input,path.join(tmp,'huge.png')));
    assert.equal(fs.existsSync(path.join(tmp,'huge.png')),false);
  } finally {fs.rmSync(tmp,{recursive:true,force:true});}
});
