# Contributing

简体中文 | [English](CONTRIBUTING.en.md)

欢迎提交清晰、范围单一的改进建议。请先查看现有 Issues，说明问题、预期行为、复现条件以及为什么变更不会削弱四角色和用户最终决定边界。

代码变更应：

- 不合并或隐藏 00/01/02/03 的职责；
- 不把 `TECHNICALLY_CLOSED` 写成 `PRODUCT_ACCEPTED`；
- 不引入默认联网、下载或凭据依赖；
- 使用 `python3 -B -m unittest discover -s tests -p 'test_*.py'` 运行公开套件；
- 不提交本地账本、缓存、日志或个人路径。

提交贡献即表示你有权提供相关内容，并同意它按本仓库适用的非商业许可证发布。商业许可安排不通过公开贡献流程自动授予。

文档变更应同步中英文，保留精确触发词与标识，并区分历史验证记录和本次实际运行的检查。见[覆盖表](docs/DOCUMENTATION-COVERAGE.md)。
