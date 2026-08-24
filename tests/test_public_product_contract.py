"""Public-layout checks for contract invariants that do not require private status documents."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "PRODUCT-CONTRACT.md"


class PublicProductContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = CONTRACT.read_text(encoding="utf-8")

    def test_four_visible_roles_are_immutable(self):
        for title in (
            "00｜Sol 项目总控",
            "01｜任务执行",
            "02｜独立验收",
            "03｜技术收口",
        ):
            self.assertIn(title, self.text)
        self.assertIn("不得删除、合并或由隐藏代理替代", self.text)

    def test_stage_and_product_decision_boundaries_are_distinct(self):
        self.assertIn("execution=COMPLETE", self.text)
        self.assertIn("acceptance=PASS", self.text)
        self.assertIn("closeout=TECHNICALLY_CLOSED", self.text)
        self.assertIn("TECHNICALLY_CLOSED` 不等于 `PRODUCT_ACCEPTED", self.text)
        self.assertIn("只有用户", self.text)

    def test_git_forensics_stays_outside_runtime(self):
        self.assertIn("由外部黑盒 harness 单列观察", self.text)
        self.assertIn("不得把 checkpoint 路径、对象取证或 actor 归因规则塞进运行时", self.text)


if __name__ == "__main__":
    unittest.main()
