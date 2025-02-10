import unittest
from sgpo_editor.gui.models.entry import EntryModel


class TestEntryModelValidator(unittest.TestCase):
    def test_flags_as_string(self):
        # 入力が文字列の場合、空白が除去され、リストに変換される
        model = EntryModel(msgid="dummy", msgstr="dummy", flags=" fuzzy ")  # type: ignore
        self.assertEqual(model.flags, ["fuzzy"])

    def test_flags_as_empty_string(self):
        # 空文字列の場合、空リストになる
        model = EntryModel(msgid="dummy", msgstr="dummy", flags="   ")  # type: ignore
        self.assertEqual(model.flags, [])

    def test_flags_as_list(self):
        # リストの各要素が文字列に変換される
        model = EntryModel(msgid="dummy", msgstr="dummy", flags=[1, "fuzzy", 3.5])  # type: ignore
        self.assertEqual(model.flags, ["1", "fuzzy", "3.5"])

    def test_flags_default(self):
        # flagsが指定されなかった場合、デフォルトでは空のリストになる
        model = EntryModel(msgid="dummy", msgstr="dummy")
        self.assertEqual(model.flags, [])


if __name__ == '__main__':
    unittest.main() 