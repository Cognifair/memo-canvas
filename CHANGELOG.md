# 变更记录

遵循语义化版本：修 bug → patch，新增能力 → minor，改变契约 → major。

## v2.1.2 — 2026-11-14

影响面：memo-canvas(SKILL.md, README.md [未改], CHANGELOG.md, references/cli-contract.md, references/tables.md, scripts/canvas.py, scripts/render_table.cjs)

### 修复

- `canvas.py doctor --require table` 与 `render_table.cjs --doctor` 检查 Playwright 和本机浏览器；缺失时明确失败，不允许静默 fallback。
- 表格默认参数改为硬约束：只能走 `render_table.cjs`，不得复制 `table-theme.css` 自写 HTML，也不得用 Python Playwright 另做截图。
- 宽、字号、字体、标题、透明底、颜色、列宽任一偏离，必须出图前说明并确认；交付时列出 `defaults`/`overrides`。
- 记录「先出图再问白底/透明」属于顺序错误，不能把自写模板说成墨兰迪默认。

## v2.1.1 — 2026-11-10

影响面：memo-canvas(SKILL.md, README.md, CHANGELOG.md, references/toolchain.md, references/redraw-gates.md, references/cli-contract.md, scripts/canvas.py)

### 变更

- `canvas.py doctor` 增加 `--require`：化学结构强制 `--require rdkit`，未加载时退出 1，不再让模型回退到手写 SVG/matplotlib。
- 文档明确：画有机结构/反应式必须先跑 RDKit 预检；图片转结构还需要 MolScribe/DECIMER 的真实模型，包存在不等于权重已加载。
- 公式、流程图、SVG、表格同样要求先跑实际命令/doctor，不能把“命令存在”当成“已生成成功”。

## v2.1.0 — 2026-11-07

影响面：memo-canvas（本地工具链、可选识别适配器、测试与调用文档）；锁定表格渲染包不变。

- 增加隔离核心安装入口、依赖清单、Node 锁文件和 doctor，明确可用、缺失与未推理验证的区别。
- 接入 MathJax LaTeX→SVG/PNG、Graphviz WASM 节点/边 JSON→流程图及 sharp SVG→PNG，拒绝覆盖，保存可编辑输入和未审计记录。
- 增加 MolScribe、DECIMER、pix2tex 的真实调用适配器和独立环境安装入口；大型依赖及模型下载必须显式确认，不捆绑权重、不自动上传、不自动采用识别候选。
- 本机安装验证后修正 MolScribe 的 Python 3.10 默认值，支持共享识别运行环境及本地权重默认路径，延长大型依赖安装超时。
- 增加渲染行为、安全拒绝及识别接口契约测试；保留 v2.0.2 准入/交付闸门。模型识别测试不冒充真实权重推理验证。
- 增加稳定 CLI 契约：表格、图片、公式、流程图统一走已列命令；禁止临时写 `figgen.py`、手拼 SVG/HTML 或自由画机构图。
- 化学样式测试缺 RDKit 时改为 `SkipTest`，不再让系统 Python 整套测试直接失败；`.runtime` 下仍执行真实 RDKit 检查。
- `render_table.cjs` 自动查找 Codex 运行时、技能目录和工作区 `node_modules` 里的 Playwright；找不到时才要求 `NODE_PATH`/`MEMO_CANVAS_PLAYWRIGHT`。

## v2.0.2 — 2026-11-07

影响面：memo-canvas(SKILL.md, README.md, CHANGELOG.md, references/redraw.md, references/redraw-gates.md)

### 变更

- 增加「重绘准入闸门」：没有源图/清晰裁切、不能看图、不能先做代表图、不能执行审计时，只能原样/高清化，禁止仅凭文字自由编造机构图或流程图。
- 增加交付前审计：文字与填充图元碰撞、图元间无意重叠、箭头连续与端点、标注归属、目标尺寸可读性。
- 明确机构/工程图必须先建立构件/连接/箭头/标注清单，不能手填坐标直接画；表格数据生成不受此限制。
- 保留“原样/高清化是正式交付”的边界，避免为了重绘而生成近似示意图。

## v2.0.1 — 2026-11-04

影响面：memo-canvas(技能名称、调用示例与系列引用) / memo-ankigo / memo-txt

- 将 Anki 迁移技能标识统一为 `memo-ankigo`，TXT 技能标识统一为 `memo-txt`，更新安装路径与系列引用。
- 本次仅调整命名与文档；Anki 历史迁移包格式保持兼容。

## v2.0.0 — 2026-11-03

影响面：memo-canvas(SKILL.md, references/tables.md, references/redraw.md, references/flowcharts.md, scripts/image_pipeline.py, scripts/test_image_pipeline.py, agents/openai.yaml, version.json, README.md) / memo-table(本地兼容入口)

- Memo-Table 更名为「墨兰迪 Memo-Canvas」，保留六种表格输出、选型约定与锁定包，表格流程移至按需参考。
- 合并扫描图像重绘 DEMO：原样保留、传统高清化、按图形类型忠实重绘，保留用户指定开局三选项。
- 增加公式、化学结构、数学图和流程图分工；专业绘图后再调参数，内容与视觉分别核验。
- 保留本地旧调用兼容；模型权重和识图服务未捆绑，不将可选路线说成已完成端到端集成。
- GitHub 仓库沿用原历史并更名为 memo-canvas；更新安装与迁移说明。其他技能的系列清单不在本次发布范围。

## v1.3.2 — 2026-10-30

影响面：memo-table(README.md, references/satellites.md)

### 变更

- Memo 系列清单加入「卡跳跳 Memo-CardLink」，同步 README 系列表与 satellites。

## v1.3.1 — 2026-10-30

影响面：memo-table(README.md)

### 变更

- README 顶部增加「墨卡大师 · 专业制卡工作流」在线介绍页链接。

## v1.3.0 — 2026-10-29

影响面：memo-table(SKILL.md, references/style-selection.md, agents/openai.yaml, README.md, version.json)

- 选型前按材料结构与语义标注推荐、有条件推荐、不推荐；检查合并、多级表头、长文本与视觉强调。
- 圆角墨墨简约风作为可调整布局的通用兜底，复杂合并优先做同风格保真适配；区分当前 JSON/array 的能力限制与可扩展的视觉风格，固定装饰样式不硬塞字段。
- 已指定样式仍做适配检查，批量材料分类型处理；无合适现成样式时提出结构优先的独立适配方案，不修改锁定包。
- README 同步材料适配与圆角布局路径，补充安装、使用入口和当前渲染器的结构边界。

## v1.2.4 — 2026-10-26

影响面：memo-table(SKILL.md)

### 修复

- 解锁/修改锁定包明确为权限请求：有交互式问题框时用问题框；Codex 的 `request_user_input` 不允许权限请求时，用单条文字确认，不合并多个问题。

## v1.2.3 — 2026-10-24

### 修复

- 圆角渲染器校验 `fontFamily`（字符白名单与长度上限），并禁用页面 JavaScript、阻断外部请求，修复字体配置注入。
- 新增 `.gitattributes` 固定锁定包换行；`verify()` 对文本文件归一化 CRLF，Windows 默认克隆不再误报 LOCK 失败。
- 新增字体注入回归脚本 `scripts/test_render_inputs.cjs`。

## v1.2.2 — 2026-10-24

### 变更

- 新增 MIT `LICENSE`，README 补 License 说明。

## v1.2.1 — 2026-10-23

### 修复

- 预览展示前先把图片复制到当前工作目录：客户端只能预览工作区内的图片，直接引用技能目录会显示“无法预览”。
- `selftest.cjs` 的基准校验从「PNG 字节完全一致」改为「尺寸一致 + 文件大小容差 ≤25%」，换机器/字体不再被自检拦死。
- `render.cjs` 查找 Playwright 时改用 `USERPROFILE` 判断（原先判断 `LOCALAPPDATA` 却拼 `USERPROFILE`）。
- 文档同步说明容差规则；`LOCK.json` 随 `render.cjs` 更新哈希。
- README 的「Memo 系列」表与 `references/satellites.md` 改由 `memo-series.json` 生成（`sync-series`），不再手写跨技能清单。

## v1.2.2 — 2026-10-24

### 变更

- 新增 MIT `LICENSE`，README 补 License 说明。

## v1.2.0 — 2026-10-23

### 变更

- 接入 Memo-Table Locked v1 渲染包：`table`、`comparison`、`sales` 三款改为固定结构，只填数据 JSON；模板、渲染器、哈希清单锁定，`report.json` 做布局校验。
- 选型改为「先展示预览，再用问题框选」：`rounded` 用用户数据渲染预览，锁定三款直接展示定稿样稿。
- 保留「墨墨风·圆角」（`rounded`，通用结构）；取消「墨墨风·直角」（`square`）。
- `table`、`comparison` 为不透明浅灰绿背景；`rounded`、`sales` 为透明底。

### 测试

- 锁定包自检 13/13 通过，三款基准 PNG 与本机定稿逐字节一致。
- 圆角渲染与锁定渲染均从新目录调用成功。

## v1.2.2 — 2026-10-24

### 变更

- 新增 MIT `LICENSE`，README 补 License 说明。

## v1.1.1 — 2026-10-19

### 新增

- 新增 `version.json`，供墨卡大师的支链版本检查读取；此后每次发版随版本号同步更新。

## v1.2.2 — 2026-10-24

### 变更

- 新增 MIT `LICENSE`，README 补 License 说明。

## v1.1.0 — 2026-10-18

- 首次纳入版本清单的发布；更早的改动未单独记录。
