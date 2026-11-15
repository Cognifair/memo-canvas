# CLI 契约

墨兰迪只暴露以下稳定入口；不要在 skill 里临时写绘图脚本、拼 SVG/HTML 或手画机构图。

## 入口

```text
python -B scripts/canvas.py setup|doctor|formula|svg|flowchart|mathplot|recognize
python -B scripts/image_pipeline.py original|enhance|chemistry
node scripts/render_table.cjs <input.json> <output.png> [output.html]
```

## 函数图：明确表达式 → SVG/PNG

```text
python -B scripts/canvas.py mathplot --input function.json --output plot.png
python -B scripts/canvas.py mathplot --input function.json --output plot.svg
```

配置示例：

```json
{
  "expression": "sin(x^2)cos(3x)+2sin(5x)/(1+x^2)+x/4",
  "xrange": [-6, 6],
  "yrange": [-5, 5],
  "width": 1600,
  "height": 900,
  "samples": 4000,
  "color": "#36B59D",
  "axis_color": "#000000",
  "background": "#FFFFFF",
  "x_labels": [{"value": -3.14159, "text": "−π"}, {"value": 3.14159, "text": "π"}],
  "y_labels": [{"value": -1, "text": "-1"}, {"value": 1, "text": "1"}]
}
```

- 表达式只允许 `x`、数字、`+ - * / ^`、括号和 `sin/cos/tan/sec/csc/cot/asin/acos/atan/sinh/cosh/tanh/exp/log/ln/log10/sqrt/abs/floor/ceil`；
- 支持隐式乘法：`2sin(5x)`、`x(x+1)`、`2pi`；
- `x_labels` / `y_labels` 只画指定文字，不自动画其他刻度数字；
- 超出 `yrange` 或非有限的点会断段，不画渐近线；需要渐近线或更多标注时明确说明；
- `.png` 会生成同名 `.source.svg` 和 `.json`；`.svg` 只生成 SVG 和 `.json`；
- 拒绝覆盖已有输出；默认白底，可用 `"background": "transparent"`。

## 工具必须先加载

- 化学结构/反应式：`python scripts/canvas.py doctor --require rdkit`，非 0 就直接停止；
- 图片转结构：`doctor --require molscribe` / `decimer` 只说明包可加载，真实权重推理另验；没有可运行模型就让用户提供 SMILES/Molfile；
- 公式/流程图/SVG：先跑对应实际命令，不能把“命令存在”当成“已生成成功”；
- 表格：需要 Playwright + 浏览器 + 字体；先跑 `python scripts/canvas.py doctor --require table` 或 `node scripts/render_table.cjs --doctor`，缺失就停。默认参数只能由 `render_table.cjs` 提供；不要复制 CSS 自写 HTML。宽/字号/字体/标题/透明底/颜色/列宽任一偏离，出图前确认并记录 `defaults`/`overrides`。

锁定样式仍通过 `scripts/locked/` 的固定模板；不修改锁定包。

## 约定

- 所有命令必须支持 `--help`；参数错误退出非 0；
- 成功退出 0，输入/渲染/依赖失败退出 1；
- 需要机器读取时输出 JSON；错误只给可理解的原因，不回显凭证或整份源文；
- 没有对应命令时停下说明，不临时发明脚本；
- 机构/流程图只按 [redraw-gates.md](redraw-gates.md) 的准入和审计交付，不能从文字自由编造；
- 不把网页深链、LaTeX 代码或 Card 引用混入图片/表格稿。

## 禁止

- 临时写 `figgen.py` / matplotlib 脚本作为“重绘”；
- 手拼 SVG 路径替代源图描绘；
- 用 `ax.text` 手填坐标后凭肉眼判断；
- 在 skill 目录外生成后声称已交付；
- 用放大/锐化冒充生成式重绘。
