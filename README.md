# 墨兰迪 Memo-Canvas v2.1.1

> 🌐 [墨卡大师 · 专业制卡工作流](https://moka-master.app.workbuddy.host/?sharecode=ZYHGDS4GEB)

原 Memo-Table，现统一为表格制作与学习图像视觉处理技能。保留六款表格输出，新增扫描图片公式、数学图、化学结构和流程图的三档处理。调用名为 `$memo-canvas`，旧 `$memo-table` 通过本地兼容入口转入。版本以 [SKILL.md](SKILL.md) 为准。

## 图片三档处理

遇到待处理图片先问：“您的任务中包括图片公式、化学结构，需要怎么处理？”

1. 直接原样上传
2. 用墨兰迪简单高清化（更快，不使用大模型重绘）
3. 用墨兰迪精美重绘

选项保留用户指定文案，但本技能本身只交付本地文件，不实际上传。纯文本制表不问图片选项。精美重绘按内容分工：一般图与流程图用 SVG，数学图可用 SVG/TikZ，化学结构可识别后交由 RDKit 绘图；再调字号、线宽、间距并分别核验语义与视觉。流程图先核对节点、箭头、条件和回路，不为好看改连接。

**重绘准入是硬规则：** 没有源图/清晰裁切、当前模型不能看图、不能先出一张代表图、不能执行碰撞/箭头/标注审计时，只能原样或高清化；不得仅凭文字描述自由编造机构图或流程图，再把示意图说成“忠实重绘”。详细检查表见 [重绘准入与交付闸门](references/redraw-gates.md)。

`scripts/image_pipeline.py` 提供原样复制、Pillow 传统增强、已知 SMILES/Molfile 的 RDKit 绘图。`scripts/canvas.py` 新增隔离安装、自检、MathJax 公式渲染、Graphviz WASM 流程图布局及 SVG→PNG；另有 MolScribe、DECIMER、pix2tex 可选识别适配器，未捆绑模型权重，真实推理需另验，DeTikZify 未接入。不绑定 OpenAI，低清图片无法辨认的内容不会自动猜补。具体命令与依赖见 [可执行工具链](references/toolchain.md)，审查流程见 [重绘流程](references/redraw.md) 和 [流程图流程](references/flowcharts.md)。

**化学结构硬门槛：** 画有机结构/反应式前必须运行 `python scripts/canvas.py doctor --require rdkit`；非 0 就直接停止并安装/激活隔离运行时，不得用系统 Python、手写 SVG 或只靠 OCR 文本拼结构。图片转结构还需要真实可运行的 MolScribe/DECIMER 模型；没有就要求用户提供 SMILES/Molfile，或退回原样/高清化。

**只允许稳定 CLI：** 表格、图片、公式、流程图都走 `canvas.py` / `image_pipeline.py` / `render_table.cjs` 的已列命令，不临时写 `figgen.py`、手拼 SVG/HTML 或自由画机构图。入口和退出码见 [CLI 契约](references/cli-contract.md)。

## 六种样式

| 样式 | 实现 | 结构 |
|---|---|---|
| 墨墨风·圆角（`rounded`） | `scripts/render_table.cjs`；复杂结构另做非锁定布局适配 | 现有 JSON：单层表头、等长行数组；合并与层级另做适配验收 |
| 产品表格·指标卡（`table`） | `scripts/locked/render.cjs` | 固定：4 列 + 2 个指标 |
| 市场份额对比（`comparison`） | `scripts/locked/render.cjs` | 固定：5 列（标签、3 值、差值） |
| 销售列表·透明底（`sales`） | `scripts/locked/render.cjs` | 固定：6 个字段 |
| LaTeX 三线表 | 直接输出代码 | 仅三条横线 |
| LaTeX 网格表 | 直接输出代码 | 有竖线、逐行横线 |

**选型方式**：先根据材料的合并关系、表头层级、列语义和文本密度，说明各样式“推荐 / 有条件推荐 / 不推荐”的原因，再展示预览供选择。`rounded` 结构匹配时用用户数据渲染；复杂合并表可先做同风格的非锁定适配小样。锁定三款展示明确标注的示例，不硬套字段或补造指标。已指定样式不重复询问，但仍检查适配性。

圆角墨墨简约风可作为图片路线的通用布局方向；这不表示现有 JSON 渲染器原生支持所有复杂表格。按需调整非锁定布局后，仍需检查合并范围、表头层级与阅读效果。详见 [材料适配说明](references/style-selection.md)。

## 安装与使用

适合把文字或表格制作成图片/代码，以及改善扫描学习图的呈现；不负责知识拆解、Markji 账户操作或 TXT 文件容器。表格图片渲染需 Node.js、Playwright、Chrome/Edge 和字体；传统高清化需 Pillow，分子绘图需 RDKit，识图另需实际可用的模型。不会自动安装大型模型或上传图片。

仓库由 `Cognifair/memo-table` 更名为 `Cognifair/memo-canvas`，保留原提交历史与旧版本标签。将仓库克隆到客户端技能目录，文件夹名为 `memo-canvas`：

```text
git clone https://github.com/Cognifair/memo-canvas.git memo-canvas
```

已有旧版安装时先备份本地改动，再将技能文件夹由 `memo-table` 更名为 `memo-canvas`，并将 origin 更新为新地址；不要仅在旧目录里拉取后假设目录名已自动改变。旧名称可用于自然语言识别；`$memo-table` 的本地转接入口需单独保留，并非本仓库自动安装。以下是新入口的调用示例：

```text
使用 $memo-canvas 处理这张扫描图，先让我选择图片处理方式。
```

Codex / WorkBuddy 安装或更新后新开会话或重启客户端。使用时可直接说：

> 使用 $memo-canvas，把这份概念对照表做成圆角图片；先判断材料结构是否需要布局适配。

主要目录：`SKILL.md` 为入口；`references/tables.md` 保留原表格流程，其他 references 按需说明图像重绘、流程图与 LaTeX；`scripts/` 为绘图及测试入口；`scripts/locked/` 保持原样，不随品牌改名修改。

> 直角墨墨风（`square`）已在 v1.2.0 取消。
>
> `table`、`comparison` 是不透明浅灰绿背景；`rounded`、`sales` 是透明底。

## 圆角路线（通用结构）

```json
{
  "title": "概念对照",
  "style": "rounded",
  "headers": ["项目", "概念 A", "概念 B"],
  "rows": [["特征", "说明 A", "说明 B"]]
}
```

```text
node scripts/render_table.cjs input.json output.png output.html
```

默认 2000 px 宽；可选 `width`、`fontFamily`、`theme`（`accent`/`light`/`deep`/`white`）。该脚本只处理 `rounded`，其它样式会提示改用锁定渲染器。Playwright 会自动查找 Codex 运行时、技能目录和当前工作区的 `node_modules`；仍找不到时才需要设置 `NODE_PATH` 或 `MEMO_CANVAS_PLAYWRIGHT`。

## 锁定三款（固定结构）

模板、渲染器与哈希清单已锁定，**只填数据 JSON，不改样式**。数据结构以 [scripts/locked/examples](scripts/locked/examples) 为准：

- `table`：`headers` 恰好 `["NO","Item Preview","Date","Income"]`；每行 4 个字符串；`metrics` 恰好 2 条 `{value, caption}`。
- `comparison`：`headers` 恰好 5 项（标签、3 个值、差值）；每行 5 个字符串。
- `sales`：`rows` 每项含 `name`、`description`、`value1`、`value2`、`year`、`status`。

```text
node scripts/locked/render.cjs input.json <新输出目录>
```

输出目录必须不存在或为空；生成 `output.png`、`output.html`、`input.json`、`report.json`。检查 `report.json` 的 `pass` 为 true，再打开 PNG 视觉验收。失败按报错修数据，不改模板、不重算哈希。

首次在新环境使用先跑基准自检：

```text
node scripts/locked/selftest.cjs <新目录>
```

基准只校验尺寸与容差（文件大小差异 ≤25%），不要求跨机器逐字节相同；尺寸不符或超出容差时停止并检查字体/浏览器，不改基准图。

## LaTeX 路线

只输出裸 `array` 环境，不加 Markdown 代码围栏、数学定界符或标题解释；不使用 `tabular`、`longtable` 或额外宏包。中文、化学式直接书写，结晶水间隔号使用 `·`。

三线表严格只有三条横线；网格表逐行画横线。已明确进入 LaTeX 路线、但线型追问后仍含糊或让 AI 决定时，默认三线表，并在代码前用一行说明默认选择；没有回答不等于同意默认。

正确模板与检查规则见 [references/array-tables.md](references/array-tables.md)。该约定是本技能的交付要求，不代表所有 LaTeX 平台的通用限制，也不代表已经在墨墨客户端验证渲染。

生成表格不等于已上传或插入卡片；图片的 HTML 是本地编辑源，不直接写进 Markji 正文。

## Memo 系列

以下列出相关系列技能；仓库更名不代表其他技能的清单与本地目录会自动完成迁移。

<!-- memo-series:begin -->
| 技能 | 职责 |
|---|---|
| [墨卡大师 Memo-Cardest](https://github.com/Cognifair/memo-cardest) | 核心制卡：知识拆解、题型、正文语法与牌组操作 |
| [Memo-MinerUOCR](https://github.com/Cognifair/memo-mineruocr) | 扫描件与大 PDF 识别、拆分并合并 Markdown |
| [墨记文档导入 Memo-TXT](https://github.com/Cognifair/memo-txt) | TXT 容器格式、分卡校验与图片回填 |
| [迁墨 Memo-AnkiGo](https://github.com/Cognifair/memo-ankigo) | Anki 图片挖空转墨墨原生遮罩 |
| [Memo-QAhelper](https://github.com/Cognifair/memo-qahelper) | 墨墨记忆卡使用答疑（官方百科与论坛） |
| [卡跳跳 Memo-CardLink](https://github.com/Cognifair/memo-cardlink) | 卡片单向跳转、双向互链与 Card 引用审计（原 Memo-Link） |
<!-- memo-series:end -->

## License

[MIT](LICENSE)
