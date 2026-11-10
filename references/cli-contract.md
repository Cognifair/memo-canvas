# CLI 契约

墨兰迪只暴露以下稳定入口；不要在 skill 里临时写绘图脚本、拼 SVG/HTML 或手画机构图。

## 入口

```text
python -B scripts/canvas.py setup|doctor|formula|svg|flowchart|recognize
python -B scripts/image_pipeline.py original|enhance|chemistry
node scripts/render_table.cjs <input.json> <output.png> [output.html]
```

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
