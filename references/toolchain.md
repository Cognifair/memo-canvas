# 可执行工具链

适用于公式、SVG、流程图和单分子重绘；表格仍走原有表格脚本，锁定包不受影响。以下命令均在本技能目录运行；输出使用新文件名，不覆盖源文件。安装工具不取消 [重绘闸门](redraw-gates.md)。

## 安装和检查

需要 Python 3.10+、uv、Node.js 20+（含 npm）。核心安装会联网下载普通依赖，但不安装识别模型、不下载权重、不发送源图。Python 依赖放在 `.runtime/python`，Node 依赖放在 `toolchain/node_modules`，不修改全局环境。

```text
python scripts/canvas.py setup
python scripts/canvas.py doctor
python scripts/canvas.py doctor --require rdkit
```

`doctor` 检查实际 Python 模块和 Node 加载情况，列出独立识别环境；模块存在或环境存在均不等于模型已加载、推理成功。可用性以实际运行记录为准。Node 使用 package-lock.json，Python 固定直接依赖；ML 可选依赖的传递版本未全量锁定，安装失败须报告，不自动改系统 Python 或降级全局依赖。

**化学结构强制：** 进入有机结构/反应式绘制前必须跑 `doctor --require rdkit`，非 0 就停止；不得用系统 Python（可能无 RDKit）、手写 SVG 或只靠 OCR 文本拼结构。`--require molscribe/decimer` 只证明包可加载，真实权重推理另验。

## 公式：已知 LaTeX → SVG/PNG

先由具备视觉能力的模型、可用公式 OCR 或用户提供 LaTeX，核对符号；保存为 UTF-8 文件（不带 `$`/`$$` 包裹），然后：

```text
python scripts/canvas.py formula --input formula.tex --output formula.svg --font-size 32
python scripts/canvas.py formula --input formula.tex --output formula.png --font-size 32
```

使用 MathJax 的 base/ams 数学包，字体轮廓内嵌为 SVG 路径，不依赖 TeX 安装。无浏览器、无外链字体；未知宏报错，不交付错误提示图片。这里不执行扫描识别。

## 流程图：清单 → 自动布局

从源图提取并核对以下 JSON；这是合成调用示例，不是用户源图的识别结果：

```json
{
  "direction": "TB",
  "nodes": [
    {"id":"start", "text":"开始", "shape":"start"},
    {"id":"check", "text":"符合条件？", "shape":"decision"},
    {"id":"done", "text":"结束", "shape":"end"}
  ],
  "edges": [
    {"from":"start", "to":"check"},
    {"from":"check", "to":"done", "label":"是"},
    {"from":"check", "to":"start", "label":"否"}
  ]
}
```

```text
python scripts/canvas.py flowchart --input graph.json --output flow.svg
python scripts/canvas.py flowchart --input graph.json --output flow.png
```

Graphviz WASM 自动布局，不依赖系统 dot。支持 TB/LR、rect/decision/start/end、换行、回路和边标签；`directed:false` 保留无箭头关系。最多 150 节点、400 边。分组、泳道和其他形状不支持，明确报错，不丢信息硬套；需要时另作可审计 SVG。布局可能不同于教材，边交叉、标签避让仍需视觉审查，不能称为自动审计通过。

## SVG → PNG

```text
python scripts/canvas.py svg --input reviewed.svg --output reviewed.png
```

用 sharp 本地光栅化。只接受受限 SVG 图元：拒绝脚本、事件、外部链接/资源、DTD、foreignObject、复杂 CSS 与不支持的元素；内嵌图片不支持。输入限制 4 MB、光栅化限制 4000 万像素。安全限制不等于任意 SVG 完全兼容。PNG 默认以 144 DPI 渲染，文字字体需本机安装。

以上渲染命令保存可编辑输入副本和 `.json` 记录，记录 `source_verified:false`、`visual_audit:not_checked`。这两个字段不能因为渲染退出码为 0 就宣称已通过审计。

## 扫描识别：可选适配器

不依赖 OpenAI，但需要专用识别模型；纯文本大模型可调这些工具，不能直接看图。以下 ML 依赖**不由核心 setup 安装**。先向用户说明依赖/权重大小、网络和本机兼容风险，获得确认后才执行对应命令；每个后端独立隔离，不能用核心环境的模块缺失判断后端不可用。

```text
python scripts/canvas.py setup --profile molscribe --allow-heavy-install
python scripts/canvas.py setup --profile decimer --allow-heavy-install
python scripts/canvas.py setup --profile pix2tex --allow-heavy-install
```

环境在 `.runtime/<backend>`；recognize 自动选择对应环境。安装入口是尽力安装，不保证所有 Windows/Python/torch/TensorFlow 组合兼容；核心渲染与可选识别相互隔离。大模型权重不随技能分发。只加载可信来源的 checkpoint：部分上游使用 torch.load，恶意权重可能执行代码。

MolScribe 1.1.1 的 PyPI 依赖需要旧版 torch，默认使用独立 Python 3.10，不复用 Python 3.12；其他环境可用 `setup --python <版本或路径>` 显式指定。已有不兼容环境不自动删除，先报告并保留。大型依赖安装超时为 30 分钟。

本机多个技能副本可用各自 `.runtime/recognition-runtime.json` 指向同一个已配置的识别根目录，内容为 `{"root":"绝对路径"}`；该本机文件和权重不进入 Git。只影响可选识别环境，核心绘图仍用各副本自己的环境。默认 MolScribe checkpoint 为该根目录下 `models/molscribe-swin-base-1m.pth`，也可用 `--checkpoint` 指定。DECIMER 缓存默认在该目录的 `models/decimer-cache`（不覆盖已有 PYSTOW_HOME 设置）。

### MolScribe：单分子图 → 结构候选

```text
python scripts/canvas.py recognize --backend molscribe --input molecule.png --checkpoint trusted-local-model.pth --output candidate.json
```

显式要求已有的本地权重；CPU 推理；Pillow 读取图片后调用 `MolScribe(...).predict_image(RGB数组, return_atoms_bonds=True, return_confidence=True)`，避免 OpenCV 在 Windows 中文路径上读图失败。MolScribe 环境固定 NumPy 1.26 和 OpenCV 4.11，避免旧 torch/RDKit 的二进制兼容问题。保留原始 SMILES/Molfile/原子/键/置信度，不把合法 SMILES 等同于识别正确。

### DECIMER：备选单分子识别

```text
python scripts/canvas.py recognize --backend decimer --input molecule.png --output candidate.json --allow-model-download
```

上游导入/首次使用可能联网下载权重，所以必须在获得下载许可后显式传开关；没有开关会在导入前拒绝。不是离线推理保证，也不自动作为 MolScribe 的备用。

### pix2tex：单个公式图片 → LaTeX 候选

```text
python scripts/canvas.py recognize --backend pix2tex --input equation.png --output equation-candidate.json --allow-model-download
```

同样需要确认下载许可；调用 `LatexOCR()(PIL.Image)`，禁用上游自动复制结果到剪贴板的副作用。不用于整页解析或化学结构识别。

三个后端都只生成 `candidate_requires_review` JSON（保留源图 SHA256）；不自动把候选送进重绘或上传。核对候选后，把 `raw.latex` 保存成 .tex 走公式渲染，或把 `raw.smiles` 交给核心环境的分子绘图命令（Windows）：

```text
.runtime/python/Scripts/python.exe scripts/image_pipeline.py chemistry --smiles "CCO" --output molecule.svg
```

macOS/Linux 的核心 Python 为 `.runtime/python/bin/python`。`CCO` 仅为示例。原样/高清化也用同一核心 Python 调 `image_pipeline.py original|enhance`。

### 已知结构新绘与墨墨风格启发样式

用户直接给分子名称或明确结构时，可转成已知 SMILES 新绘，不声称是源图识别或忠实重绘。名称存在异构体歧义时先确认。

```text
.runtime/python/Scripts/python.exe scripts/image_pipeline.py chemistry --smiles "Cc1ccccc1" --output outputs/toluene-memo.svg --style memo --explicit-methyl --width 1200 --height 840 --line-width 3.5 --font-size 42 --padding 0.20
```

输出扩展名改为 `.png` 可生成同尺寸位图。`standard` 保持原有默认；`memo` 为本地设计的浅薄荷底 `#F7FBF9`、深绿结构线 `#176B53`，不是官方品牌规范，不添加 Logo。`--explicit-methyl` 仅标注普通、不带同位素/电荷/自由基的末端 CH₃，不改变分子图。新绘也要核对分子式和连接、目视检查标签/裁切；渲染成功本身不证明结构准确。保留原文件和 SVG，不自动上传。

安装后的本机验证可记录在识别根目录的 `recognition-validation.json`，doctor 显示历史记录，但不重新加载模型、不保证记录仍适用于当前依赖。真实测试中可能出现 Ph→Pb、楔形线→额外三键、模糊公式括号错误；置信度高或结构可解析不能替代源图核对。两个化学模型不一致时不得自动选一个。

## 验证与尚未集成

```text
node --test scripts/test_canvas_render.cjs
.runtime/python/Scripts/python.exe -B -m unittest discover -s scripts -p "test_*.py" -v
node scripts/test_render_inputs.cjs
```

识别适配器的模拟测试只检验接口、拒绝条件与候选保存，不证明真实图像识别正确。真实权重推理需另测并逐次记录。DeTikZify 和通用科学图自动识别仍是研究参考，未接入；数学/工程图仍需视觉或用户提供的结构。没有把别的仓库整体塞进技能，也没有自动安装其他 Skill。
