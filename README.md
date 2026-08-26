# 办公数字员工（Codex Plugin）

一个面向真实办公场景的开源 Codex Plugin。一次安装即可使用三位独立数字员工，把零散材料转成可继续使用、可验收的本地成果。

## 包含的 Skills

| Skill | 作用 | 默认成果 |
| --- | --- | --- |
| `task-execution-employee` | 把聊天、语音转写或业务要求拆成任务与验收标准 | 本地 HTML 任务包 |
| `meeting-minutes-employee` | 从会议材料中提炼观点、决定、行动项和数据 | 响应式 HTML 会议纪要 |
| `visual-design-employee` | 从业务目标和品牌材料形成设计 brief 并制作视觉成果 | brief、提示词与本地图片 |

所有 Skills 都遵循同一条边界：默认只生成本地成果；发送、发布、付款、删除、覆盖或写入第三方系统前必须再次确认。

## 安装

仓库公开后，可以直接把它添加为 Codex Plugin Marketplace：

```bash
codex plugin marketplace add yaoran/codex-training-digital-employees --ref main
codex plugin add codex-training-digital-employees@yaoran-open-source
```

安装完成后请新建一个 Codex 任务，以避免旧任务仍使用缓存版本。

只想安装单个 Skill 时，也可以使用 Skills CLI：

```bash
npx skills add https://github.com/yaoran/codex-training-digital-employees \
  --skill task-execution-employee --global --yes
```

## 使用示例

- `使用 $task-execution-employee 把这段业务要求整理成可执行的 HTML 任务包。`
- `使用 $meeting-minutes-employee 把附件整理成适配手机阅读的会议纪要。`
- `使用 $visual-design-employee 根据活动 brief 制作一张本地宣传图。`

## 隐私与安全

- 不要把密钥、Cookie、客户私有材料或未脱敏数据提交到仓库。
- Skill 产物默认保存在本地；本地生成不等于已经发送或发布。
- 真人肖像、Logo、二维码和第三方素材必须有明确授权。
- 发现安全问题时，请遵循 [SECURITY.md](SECURITY.md) 的私下报告方式。

## 本地验证

```bash
python3 scripts/validate_repository.py
python3 -m unittest discover -s tests -v
```

验证会检查 Marketplace、Plugin 清单、每个 Skill 的基本结构，以及路径、HTML 输出和不可信输入边界的安全回归。提交前还应运行当前 Codex Plugin/Skill 官方验证器，并进行敏感信息检查。

任务包或会议纪要生成后，在打开前运行 HTML 安全检查：

```bash
python3 plugins/codex-training-digital-employees/scripts/check_html_safety.py <生成的文件.html>
```

## 开源范围

当前版本只包含郭振耀原创的三项 Skill。原本地教学版中的 `ppt-master` 未纳入此仓库，因为其第三方来源和再分发授权仍需单独核验。

## 参与贡献

欢迎提交真实问题、复现材料和改进建议。请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。

本项目采用 [MIT License](LICENSE)。
