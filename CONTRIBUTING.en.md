# Contributing

[简体中文](CONTRIBUTING.md) | English

Clear, focused improvements are welcome. Check existing [issues](https://github.com/janiezhang52-lab/sol-project-orchestrator/issues) first. Explain the problem, expected behavior, reproduction conditions, and why your proposal preserves the four roles and the user's final decision.

Code changes should:

- Keep the responsibilities of 00, 01, 02, and 03 distinct and visible.
- Never equate `TECHNICALLY_CLOSED` with `PRODUCT_ACCEPTED`.
- Introduce no default networking, downloads, or credential dependencies.
- Run the public suite from the repository root:

  ```sh
  python3 -B -m unittest discover -s tests -p 'test_*.py'
  ```

- Exclude local ledgers, caches, logs, and personal paths from commits.

By contributing, you represent that you have the right to provide the material and agree to its release under the repository's applicable noncommercial license. Contributing does not automatically grant commercial-use permission. See [LICENSE](LICENSE).

For documentation, keep Chinese and English pages synchronized, preserve exact trigger phrases and identifiers, and distinguish reported historical validation from checks actually run for your change. See the [coverage table](docs/DOCUMENTATION-COVERAGE.md).
