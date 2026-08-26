# 会议纪要 HTML 工作流

## 来源核验

- 先确认附件确实是目标会议的录音转写、讨论记录或聊天记录，并检查内容是否完整可读。
- 无法读取、来源不匹配或内容截断时，明确说明可核实范围，并将缺失部分标记为“待补充”。
- 只记录材料中能够证实的会议主题、时间、参会者、观点、决策、行动项和数据，不用常识补全。
- 口语可转为书面语，但不得改变原意；重要数字、日期、名称和承诺必须回查原文。
- 原始记录没有写明的负责人和截止时间统一标为“待确认”。

## 内容组织

1. 标题区：会议主题、时间以及可证实的基本信息。
2. 核心观点：提炼 3–5 个关键要点，优先展示会议结论和重要共识。
3. 详细内容：按议题或主题分块整理，区分事实、观点、决定和待确认事项；待确认事项单独使用卡片或清单呈现，每项均包含“确认事项、负责人、截止时间”。
4. 行动清单：列明具体事项、负责人、截止时间和备注；缺失字段写“待确认”。
5. 数据汇总：集中展示会议中的重要数字、指标和日期；没有重要数据时写“本次材料未出现明确数据”，不得编造。

## HTML 输出规则

- 输出为可直接打开的独立 UTF-8 HTML 文件，CSS 写在文件内部，不引用在线字体、图片、脚本或其他外部资源。
- 所有来自附件、转写、聊天或会议材料的动态文本必须按所处 HTML 上下文编码，至少处理 `&`、`<`、`>`、双引号和单引号；不得把材料原文作为 HTML、CSS 或属性值直接拼接。
- 禁止 `script`、`iframe`、`object`、`embed`、`form`、`base`、`link`、SVG/MathML 活动内容、meta refresh、`on*` 事件属性、`javascript:` URL、CSS `@import` 和任何网络资源。
- 页面主色使用 `#BC1F1A`；正文使用微软雅黑、苹方、思源黑体等中文友好字体回退栈。
- 使用语义化标题、卡片、标签和适量图标突出重点，保证文字与背景对比清晰。
- 桌面端保持舒适阅读宽度；手机端不得出现页面横向滚动、内容遮挡或过小文字。
- 行动清单、待确认事项或数据表在窄屏上转换为纵向卡片，避免依赖横向滚动。
- 不用只有颜色才能表达的状态；同时配合文字标签，例如“已决定”“待确认”。

## HTML 结构模板

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:; base-uri 'none'; form-action 'none'">
  <title>[会议主题]会议纪要</title>
  <style>
    :root { --brand: #BC1F1A; }
    body { font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", sans-serif; }
    /* 根据内容完善桌面与移动端样式 */
  </style>
</head>
<body>
  <header><!-- 会议主题、时间和基本信息 --></header>
  <main>
    <section id="key-points"><!-- 3–5 个核心观点 --></section>
    <section id="details"><!-- 按主题分块的详细内容 --></section>
    <section id="actions"><!-- 行动清单 --></section>
    <section id="pending"><!-- 待确认事项：确认事项、负责人、截止时间 --></section>
    <section id="data"><!-- 数据汇总 --></section>
  </main>
</body>
</html>
```

## 交付前检查

- 检查附件可读取范围，确认没有把缺失内容写成完整事实。
- 回查会议名称、人员、数字、日期、决策和行动项。
- 检查每一条待确认事项均展示负责人和截止时间；原始材料未写明时，两个字段都明确写“待确认”。
- 确认文件是 UTF-8 单文件 HTML，双击可直接打开。
- 打开文件前，运行 Plugin 根目录的 `scripts/check_html_safety.py`；确认不存在活动元素、事件属性、危险 URL 或网络资源，且 CSP 完整。检查失败时先修正并重跑。
- 分别检查桌面和手机视口：页面非空、层级清楚、无横向滚动、无文字遮挡或裁切。
- 报告真实文件路径；本地文件生成不等于已经发送、发布或写入协作系统。
