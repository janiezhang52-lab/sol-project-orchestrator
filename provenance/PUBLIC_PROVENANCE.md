# Public provenance

简体中文 | [English](PUBLIC_PROVENANCE.en.md)

本文件只记录可公开的技术身份，不包含本机路径、内部验收材料位置、任务标识或账号信息。

## 正式发布身份

- version：`0.3.3`
- formal ZIP：`sol-project-orchestrator-0.3.3.zip`
- formal ZIP bytes：`31633`
- formal ZIP SHA-256：`92a62af2641e027390c8bbfe2d64d710bc2fb5f267cf470cb75d5dc31d3c0b84`
- release tree SHA-256：`0cb9a029e29cd57af9609d4b6be88dfe63e5dd8dfc9c424afb9e90fedd5641ae`

正式 ZIP 的 7 个普通文件与公开仓 `release/sol-project-orchestrator/` 中的正式 release tree 逐字节一致。私有开发仓的 Git object 身份只保留在内部冻结记录中，不在公共仓发布。

## 公开仓历史与记录范围

公开仓已有独立于私有开发仓的历史，`v0.3.3` 指向公开发布快照；公开 commit 身份请查看仓库 tag，不得冒充内部开发历史。[已发布的 v0.3.3](https://github.com/janiezhang52-lab/sol-project-orchestrator/releases/tag/v0.3.3)提供正式 ZIP 和校验文件。文档更新不重打包，也不改变上述正式包身份。

`source-manifest.json` 和根目录 `SHA256SUMS.txt` 保留为冻结快照记录；其中发布前状态字段和文件哈希描述的是记录时的快照，不覆盖后续每次 README 更新或翻译，也不表示当前分支完整清单。本次文档更新不改这些记录或正式运行包的七个文件，新文档及修订由 Git 记录。

## 平台验证边界

同一 exact 正式 ZIP 已分别在 fresh Windows Git 与 fresh macOS Git 项目中走完完整产品链，并分别在用户作出明确的最终产品决定后进入 `PRODUCT_ACCEPTED`。这是对上述 exact ZIP 的验证，不是对未来修改或重打包产物的外推。

## 静态套件边界

v0.3.3 frozen source 在正式产品仓已验证完整原始 suite `59/59 PASS`。本 GitHub 公开快照不包含内部 `CURRENT/GAPS` 状态文档，公开布局 suite 为 `57/57 PASS`；少的两项只覆盖这些不公开的内部状态文档，不是运行时代码测试。

逐文件来源分类、大小和 SHA-256 见 `source-manifest.json`；公开树校验值见根目录 `SHA256SUMS.txt`。

本次英文资料更新的检查见[文档覆盖与验证记录](../docs/DOCUMENTATION-COVERAGE.md)。
