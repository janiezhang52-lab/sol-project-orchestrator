# Chinese–English documentation coverage / 中英文资料覆盖

Review date / 检查日期: 2026-10-22. This is a documentation-only update. Chinese material is retained; no program behavior, license terms, or release package is changed. / 本次只更新公开资料，保留中文，不改功能、许可证条文或发布包。

## Coverage / 覆盖表

| Chinese source / 中文来源 | English entry / 英文入口 | Scope / 范围 |
| --- | --- | --- |
| [README.md](../README.md) | [README.en.md](../README.en.md) | Overview, install, use, limits / 首页、安装、使用、限制 |
| [CONTRIBUTING.md](../CONTRIBUTING.md) | [CONTRIBUTING.en.md](../CONTRIBUTING.en.md) | Contribution rules and test command / 贡献与测试 |
| [SECURITY.md](../SECURITY.md) | [SECURITY.en.md](../SECURITY.en.md) | Private reporting, no unverified availability promise / 私下报告，不保证未核实的渠道状态 |
| [SUPPORT.md](../SUPPORT.md) | [SUPPORT.en.md](../SUPPORT.en.md) | Issue guidance / 支持入口 |
| [CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md) | [CODE_OF_CONDUCT.en.md](../CODE_OF_CONDUCT.en.md) | Community standards / 行为准则 |
| [CHANGELOG.md](../CHANGELOG.md) | [CHANGELOG.en.md](../CHANGELOG.en.md) | v0.3.3 history / 版本记录 |
| [docs/PRODUCT-CONTRACT.md](../docs/PRODUCT-CONTRACT.md) | [docs/PRODUCT-CONTRACT.en.md](../docs/PRODUCT-CONTRACT.en.md) | All invariants and role boundaries / 全部不变量与角色边界 |
| [provenance/PUBLIC_PROVENANCE.md](../provenance/PUBLIC_PROVENANCE.md) | [provenance/PUBLIC_PROVENANCE.en.md](../provenance/PUBLIC_PROVENANCE.en.md) | Package identity and evidence scope / 发布身份与证据范围 |

## Images / 图片

Both Chinese diagrams and their existing English counterparts were visually inspected. `assets/sol-readme-hero.en.png` and `assets/sol-workflow-contract.en.png` are retained unchanged, with English alt text in the README. They illustrate responsibilities and sequence; they are not execution screenshots. / 已查看中英四张图，保留现有英文图及替代文字，图示不冒充执行截图。

## Exclusions and pending items / 排除与待确认

- The seven files under `release/sol-project-orchestrator/`, including operational `SKILL.md`, `agents/openai.yaml`, Python driver, license files, and manifest, stay byte-identical. Chinese trigger phrases and runtime instructions remain exact. / 正式七文件、触发词及运行指令不改动。
- Root `LICENSE` and `LICENSES/` already provide English legal text and are unchanged. Sol remains noncommercial source-available, not OSI open source; no legal grant is rewritten. / 英文法律文本已存在，不修改许可、不改称 OSI 开源。
- `provenance/source-manifest.json` and `SHA256SUMS.txt` are frozen-snapshot records, not a fresh inventory of this documentation branch. Their historical hashes/status are preserved and explained in both provenance pages. / 冻结清单原样保留，双语说明适用范围。
- Code comments, internal logs, private validation material, historical commits, and runtime machine-readable instructions are outside translation scope. / 程序注释、内部日志、私有验收材料、历史提交、机器操作文件排除。
- Existing GitHub release body/assets are unchanged; English changelog and provenance are available in the repository. No release is published or modified. / 不修改或新增 release。
- Availability of GitHub private vulnerability reporting was not confirmed; the bilingual security policy gives a conditional route and asks readers not to disclose details publicly. / 未确认私密漏洞报告开关，文档不作已启用承诺。

## Validation / 检查

See the checks recorded below. Historical acceptance claims in translated pages remain explicitly attributed to the original reports; they are not presented as new end-to-end tests. / 翻译中的历史验收结论注明原有记录，不冒充本次端到端测试。

- `python3 -B -m unittest discover -s tests -p 'test_*.py'`: **57/57 passed**. No fresh Windows/macOS Host product chain was run. / 公开套件通过，未重跑双平台 Host 产品链。
- Local Markdown/image destinations and balanced code fences checked; `git diff --check` passed. / 本地链接、图片目标、代码围栏及差异空白检查通过。
- Across both repositories, 32 unique public HTTPS destinations returned HTTP 200 on 2026-10-22, including release/download URLs. HTTP availability does not verify every anchor, private-reporting permission, or page content claim. / 两仓库共 32 个 HTTPS 地址返回 200，不等于逐一验证锚点、私密报告权限或内容结论。
- Runtime files, original legal texts, and image pixels match the base commit. No release ZIP was rebuilt. / 运行文件、法律原文和图片与基线一致，未重打包。
