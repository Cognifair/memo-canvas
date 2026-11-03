# 精美重绘：专业重建，再做视觉调整

## 先检查能力，而非假装后端存在

询问开局选项后，检查当前模型能否查看图片，以及所选路线的实际工具。Memo-Canvas 已提供原样复制、传统增强、从已知 SMILES/Molfile 生成分子 SVG/PNG 的脚本；图片识别由实际可用的模型或工具承担，不包含自动安装器。使用前核对对应项目当前接口和许可证，不直接复制上游代码或声称获得官方背书。

| 类型 | 重建路线 | 不可擅自改变 |
|---|---|---|
| 图片公式 | 多模态模型或公式 OCR 提取 LaTeX，再由可用的数学渲染器生成 SVG/PNG | 正负号、上下标、括号、等号、不等号、矩阵结构 |
| 表格 | 提取文字与行列关系，再读 [tables.md](tables.md)；按已指定样式或选型建立 HTML/CSS | 数值、单位、表头、合并单元格关系 |
| 流程/一般示意图 | 多模态模型参照原图编写 SVG | 箭头方向、分组、标签及连接关系 |
| 数学科学图 | SVG/TikZ；已有 DeTikZify 时可试验图转 TikZ | 坐标、角标、虚实线、已知几何和函数关系 |
| 单个化学结构 | MolScribe 或 DECIMER 识别，再交给 RDKit | 原子、键级、电荷、同位素、立体信息 |

优先保留原图布局，避免无必要重排。不把扫描曲线的近似外观当作已知精确函数。反应式中的箭头、条件、多分子布局需独立解析；单分子识别不是完整反应识别。

流程图执行 [flowcharts.md](flowcharts.md)，先建立节点/边/分支标签清单，再布局，不以装饰改变拓扑。其他数学图特别核验角度弧线端点及方向、坐标正负与虚实线。

## 化学路线的实际衔接

1. 保存原图，必要时生成单分子裁剪供识别；保留裁剪与原页对应关系。
2. 有可用多模态模型时可尝试提取结构，但不将其当作经过专业识别验证。有 MolScribe 时使用本地已配置的 checkpoint；其 `predict_image_file(..., return_atoms_bonds=True, return_confidence=True)` 可返回 `smiles`、`molfile`、原子、键和置信度。DECIMER 的 `predict_SMILES(image_path)` 返回 SMILES，首次运行可能下载权重，执行前说明并确认此类额外下载。
3. 保存原始识别输出，标注识别来源。低置信度、不可读区域或两模型不一致时，先给出疑点，不在多候选中凭美观选结构。
4. 把已核对的 SMILES 或 Molfile 交给 `image_pipeline.py chemistry`。例如：

   `python <skill-dir>/scripts/image_pipeline.py chemistry --smiles "CCO" --output ethanol.svg --width 600 --height 400 --line-width 2 --font-size 24 --padding 0.08`

   已有 Molfile 时用 `--molfile structure.mol` 替代 `--smiles`。这里的 `CCO` 只是调用示例，不是任何用户图片的识别结果。
5. 脚本同时输出结构 SHA256 和规范化 SMILES 的 JSON 记录。润色时复用同一结构输入，仅调整绘图参数；记录不同渲染的结构标识。标识一致只证明使用了同一结构，不证明识别与原图一致，也不保留原图所有文字缩写形式。

## 如何润色，而不重猜内容

先渲染初稿，有视觉能力时在目标卡片尺寸查看。选择有实际依据的修改，例如增大原子标签、加粗键、缩小外围留白或调整画布。通过专业引擎参数再绘制，不在生成的分子 SVG 中手工移动原子/修改键。相同结构可生成不同坐标布局；首版不承诺复刻教材坐标。

HTML 只负责外围标题、说明、背景、边距和尺寸：用 `<img>` 引用分子 SVG，不用 CSS 猜画化学键。通用 SVG 可直接调整元素；公式优先修改渲染字号而非手工拼符号。保持学习图高对比，不能为了莫兰迪配色压低细节可读性。

HTML 截图必须先确认浏览器/截图工具实际存在；没有就交付 SVG/PNG 或 HTML 源，说明未截图。不把浏览器显示尺寸等同于已测试 Markji 客户端效果。

## 核验与停止条件

分别检查：

- 语义：逐项对照公式符号、化学连接、图表数值与箭头。RDKit 能解析或两模型一致不等于忠实于原图。
- 视觉：正常显示尺寸下的字号、线宽、裁切、重叠和背景对比；保留初稿以供比较。

最多做两轮有针对性的视觉修改；仍有问题则交付草稿和问题清单，不宣称完成。模糊到无法判断的内容须由用户核对或补清晰图。

## 可选上游参考（未捆绑）

- SVG 重绘规范：https://github.com/ShiweiWu-545/Scientific-Svg-Redraw
- 科学图转 TikZ：https://github.com/potamides/DeTikZify
- 分子识别：https://github.com/thomas0809/MolScribe
- 分子识别备选：https://github.com/Kohulan/DECIMER-Image_Transformer
- 分子绘图：https://github.com/rdkit/rdkit

参考不是硬依赖；不要为本任务自动安装另一个 Skill。双路识别仅用于疑难图或用户要求：比较规范化且考虑立体信息的结构，不直接比较原始 SMILES 字符串。
