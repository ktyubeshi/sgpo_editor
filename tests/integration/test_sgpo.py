from __future__ import annotations

import unittest
from pathlib import Path

from sgpo.core import KeyTuple, SGPOFile, pofile, pofile_from_text


def get_test_data_dir() -> Path:
    # プロジェクトルートディレクトリを取得
    project_root = Path(__file__).parents[2]  # tests/integration から2階層上がプロジェクトルート
    # プロジェクトルートからのテストデータへの相対パス
    return project_root / "tests" / "data" / "test_sgpo"


def get_test_data_path(*paths: str) -> Path:
    return get_test_data_dir().joinpath(*paths)


class TestSgpo(unittest.TestCase):
    def test_init_sgpo(self) -> None:
        obj = SGPOFile()
        self.assertIsNotNone(obj)

    def test_from_file_sgpo(self) -> None:
        po_file = get_test_data_path("common", "language.po")
        po = pofile(str(po_file))
        print(f"\n{po}")
        self.assertIsNotNone(po)

    def test_from_text_sgpo(self) -> None:
        po_file = get_test_data_path("common", "language.po")
        with open(po_file) as file:
            content = file.read()

        po = pofile_from_text(content)
        print(f"\n{po}")
        self.assertIsNotNone(po)

    def test_find_by_key_sgpo_key_type1(self) -> None:
        po_file = get_test_data_path("common", "language.po")
        po = pofile(str(po_file))
        msgctxt = "context:"
        msgid = "msgid_2"
        expected_msgstr = "msgstr_2"
        result = po.find_by_key(msgctxt, msgid)

        print(f"\n{result}")

        self.assertIsNotNone(result)
        self.assertEqual(expected_msgstr, result.msgstr)

    def test_find_by_key_sgpo_key_type2(self) -> None:
        po_file = get_test_data_path("common", "language.po")
        po = pofile(str(po_file))
        msgctxt = "unique_key_2"
        msgid = "unique_msgid_2"
        expected_msgstr = "unique_msgstr_2"
        result = po.find_by_key(msgctxt, msgid)

        print(f"\n{result}")

        self.assertIsNotNone(result)
        self.assertEqual(expected_msgstr, result.msgstr)

    def test_sort_sgpo(self) -> None:
        normal_po_file = get_test_data_path("sort", "normal_order.po")
        reverse_po_file = get_test_data_path("sort", "reverse_order.po")

        po: SGPOFile = pofile(str(normal_po_file))
        po_reverse: SGPOFile = pofile(str(reverse_po_file))

        print("\nBefore:")
        print(po_reverse.get_key_list())
        print(po.get_key_list())
        self.assertNotEqual(po_reverse.get_key_list(), po.get_key_list())

        po_reverse.sort(reverse=False)

        print("\nAfter:")
        print(po_reverse.get_key_list())
        print(po.get_key_list())

        self.assertEqual(po_reverse.get_key_list(), po.get_key_list())

    def test_sort_sgpo_reverse(self) -> None:
        normal_po_file = get_test_data_path("sort", "normal_order.po")
        reverse_po_file = get_test_data_path("sort", "reverse_order.po")

        po = pofile(str(normal_po_file))
        reverse_order_po = pofile(str(reverse_po_file))

        print("\nBefore:")
        print(reverse_order_po.get_key_list())
        print(po.get_key_list())
        self.assertNotEqual(reverse_order_po.get_key_list(), po.get_key_list())

        po.sort(reverse=True)
        print("\nAfter:")
        print(reverse_order_po.get_key_list())
        print(po.get_key_list())
        self.assertEqual(reverse_order_po.get_key_list(), po.get_key_list())

    def test_format_sgpo_with_no_header_po(self) -> None:
        po_file = get_test_data_path("format", "formatted.po")
        po_header_less_file = get_test_data_path("format", "header_less.po")

        po = pofile(str(po_file))
        header_less_po = pofile(str(po_header_less_file))

        print(f"\n#### Before ####\n{header_less_po}")
        header_less_po.format()
        print(f"\n#### After ####\n{header_less_po}")

        self.assertEqual(po.__unicode__(), header_less_po.__unicode__())

    def test_format_sgpo_with_unnecessary_header_items(self) -> None:
        po_file = get_test_data_path("format", "formatted.po")
        unnecessary_header_po_file = get_test_data_path(
            "format", "unnecessary_header.po"
        )

        po = pofile(str(po_file))
        unnecessary_header_po = pofile(str(unnecessary_header_po_file))

        print(f"\n#### Before ####\n{unnecessary_header_po}")
        unnecessary_header_po.format()
        print(f"\n#### After ####\n{unnecessary_header_po}")

        self.assertEqual(po.__unicode__(), unnecessary_header_po.__unicode__())

    def test_format_sgpo_with_abnormal_header_order(self) -> None:
        po_file = get_test_data_path("format", "formatted.po")
        abnormal_order_header_po_file = get_test_data_path(
            "format", "abnormal_order_header.po"
        )
        po = pofile(str(po_file))
        abnormal_order_header_po = pofile(str(abnormal_order_header_po_file))

        print(f"\n#### Before ####\n{abnormal_order_header_po}")
        abnormal_order_header_po.format()
        print(f"\n#### After ####\n{abnormal_order_header_po}")

        self.assertEqual(po.__unicode__(), abnormal_order_header_po.__unicode__())

    def test_get_key_list_sgpo(self) -> None:
        pot = pofile_from_text(get_key_list_test_data)
        result = pot.get_key_list()

        print(f"\n{result}")

        self.assertEqual(expected_key_list, result)

    def test_import_unknown_sgpo_case1(self) -> None:
        """
        No conflict between the pot file and the unknown file
        """
        pot_file = get_test_data_path("import_unknown", "case_1_messages.pot")
        unknown_file = get_test_data_path("import_unknown", "case_1_unknown.24_1")
        expected_result_file = get_test_data_path(
            "import_unknown", "case_1_expected_result.pot"
        )

        pot = pofile(str(pot_file))
        unknown = pofile(str(unknown_file))
        expected_result = pofile(str(expected_result_file))

        pot.import_unknown(unknown)
        pot.sort()
        print("\n======== New pot content ========\n")
        print(pot)

        self.assertEqual(expected_result.__unicode__(), pot.__unicode__())

    def test_import_unknown_sgpo_case2(self) -> None:
        """
        Conflicting entries between the pot file and the unknown file
        """
        pot_file = get_test_data_path("import_unknown", "case_2_messages.pot")
        unknown_file = get_test_data_path("import_unknown", "case_2_unknown.24_1")
        expected_result_file = get_test_data_path(
            "import_unknown", "case_2_expected_result.pot"
        )

        pot = pofile(str(pot_file))
        unknown = pofile(str(unknown_file))
        expected_result = pofile(str(expected_result_file))

        pot.import_unknown(unknown)
        pot.sort()
        print("\n======== New pot content ========\n")
        print(pot)

        self.assertEqual(expected_result.__unicode__(), pot.__unicode__())

    def test_import_unknown_sgpo_case3(self) -> None:
        """
        Conflicting entries between the pot file and the unknown file
        """
        pot_file = get_test_data_path("import_unknown", "case_3_messages.pot")
        unknown_file = get_test_data_path("import_unknown", "case_3_unknown.24_1")
        expected_result_file = get_test_data_path(
            "import_unknown", "case_3_expected_result.pot"
        )

        pot = pofile(str(pot_file))
        unknown = pofile(str(unknown_file))
        expected_result = pofile(str(expected_result_file))

        pot.import_unknown(unknown)
        pot.sort()
        print("\n======== New pot content ========\n")
        print(pot)

        self.assertEqual(expected_result.__unicode__(), pot.__unicode__())

    def test_import_mismatch_sgpo(self) -> None:
        pot_file = get_test_data_path("import_mismatch", "case_1_messages.pot")
        mismatch_file = get_test_data_path("import_mismatch", "case_1_mismatch.24_1")
        expected_result_file = get_test_data_path(
            "import_mismatch", "case_1_expected_result.pot"
        )

        pot = pofile(str(pot_file))
        mismatch = pofile(str(mismatch_file))
        expected_result = pofile(str(expected_result_file))

        pot.import_mismatch(mismatch)
        pot.sort()
        print("\n======== New pot content ========\n")
        print(pot)

        self.assertEqual(expected_result.__unicode__(), pot.__unicode__())

    def test_import_pot_sgpo_case1(self) -> None:
        """
        Only new entries are added.
        """
        pot_file = get_test_data_path("import_pot", "case_1_messages.pot")
        po_file = get_test_data_path("import_pot", "case_1_language.po")
        expected_result_file = get_test_data_path(
            "import_pot", "case_1_expected_result.po"
        )

        pot = pofile(str(pot_file))
        po = pofile(str(po_file))
        expected_result = pofile(str(expected_result_file))

        po.import_pot(pot)
        po.sort()
        print("\n======== New pot content ========\n")
        print(po)

        self.assertEqual(expected_result.__unicode__(), po.__unicode__())

    def test_import_pot_sgpo_case2(self) -> None:
        """
        Changes occurred in the original text (msgid)
        """
        pot_file = get_test_data_path("import_pot", "case_2_messages.pot")
        po_file = get_test_data_path("import_pot", "case_2_language.po")
        expected_result_file = get_test_data_path(
            "import_pot", "case_2_expected_result.po"
        )

        pot = pofile(str(pot_file))
        po = pofile(str(po_file))
        expected_result = pofile(str(expected_result_file))

        po.import_pot(pot)
        po.sort()
        print("\n======== New pot content ========\n")
        print(po)

        self.assertEqual(expected_result.__unicode__(), po.__unicode__())

    def test_import_pot_sgpo_case3(self) -> None:
        """
        The po contains entries that were deleted from the pot
        """
        pot_file = get_test_data_path("import_pot", "case_3_messages.pot")
        po_file = get_test_data_path("import_pot", "case_3_language.po")
        expected_result_file = get_test_data_path(
            "import_pot", "case_3_expected_result.po"
        )

        pot = pofile(str(pot_file))
        po = pofile(str(po_file))
        expected_result = pofile(str(expected_result_file))

        po.import_pot(pot)
        po.sort()
        print("\n======== New pot content ========\n")
        print(po)

        self.assertEqual(expected_result.__unicode__(), po.__unicode__())

    def test_delete_extracted_comments(self) -> None:
        pot_file = get_test_data_path("delete_extracted_comments", "messages.pot")
        expected_result_file = get_test_data_path(
            "delete_extracted_comments", "expected_result.pot"
        )
        pot = pofile(str(pot_file))
        expected_result_pot = pofile(str(expected_result_file))

        print("\n======== Input ========")
        print(pot)

        pot.delete_extracted_comments()
        print("\n======== Output ========")
        print(pot)

        self.assertEqual(expected_result_pot.__unicode__(), pot.__unicode__())

    def test_diff_with_no_differences(self) -> None:
        po1_content = '''msgctxt "test"
msgid "Hello"
msgstr "こんにちは"'''

        po1 = pofile_from_text(po1_content)
        po2 = pofile_from_text(po1_content)

        diff_result = po1.diff(po2)
        assert not diff_result.new_entries
        assert not diff_result.removed_entries
        assert not diff_result.modified_entries
        assert not bool(diff_result)

    def test_diff_with_new_entry(self) -> None:
        po1_content = '''msgctxt "test1"
msgid "Hello"
msgstr "こんにちは"'''

        po2_content = '''msgctxt "test1"
msgid "Hello"
msgstr "こんにちは"

msgctxt "test2"
msgid "World"
msgstr "世界"'''

        po1 = pofile_from_text(po1_content)
        po2 = pofile_from_text(po2_content)

        diff_result = po1.diff(po2)
        assert len(diff_result.new_entries) == 1
        assert diff_result.new_entries[0].key.msgctxt == "test2"
        assert diff_result.new_entries[0].key.msgid == "World"
        assert diff_result.new_entries[0].new_value == "世界"
        assert not diff_result.removed_entries
        assert not diff_result.modified_entries

    def test_diff_with_removed_entry(self) -> None:
        po1_content = '''msgctxt "test1"
msgid "Hello"
msgstr "こんにちは"

msgctxt "test2"
msgid "World"
msgstr "世界"'''

        po2_content = '''msgctxt "test1"
msgid "Hello"
msgstr "こんにちは"'''

        po1 = pofile_from_text(po1_content)
        po2 = pofile_from_text(po2_content)

        diff_result = po1.diff(po2)
        assert len(diff_result.removed_entries) == 1
        assert diff_result.removed_entries[0].key.msgctxt == "test2"
        assert diff_result.removed_entries[0].key.msgid == "World"
        assert diff_result.removed_entries[0].old_value == "世界"
        assert not diff_result.new_entries
        assert not diff_result.modified_entries

    def test_diff_with_modified_entry(self) -> None:
        po1_content = '''msgctxt "test"
msgid "Hello"
msgstr "こんにちは"'''

        po2_content = '''msgctxt "test"
msgid "Hello"
msgstr "ハロー"'''

        po1 = pofile_from_text(po1_content)
        po2 = pofile_from_text(po2_content)

        diff_result = po1.diff(po2)
        assert len(diff_result.modified_entries) == 1
        assert diff_result.modified_entries[0].key.msgctxt == "test"
        assert diff_result.modified_entries[0].key.msgid == "Hello"
        assert diff_result.modified_entries[0].old_value == "こんにちは"
        assert diff_result.modified_entries[0].new_value == "ハロー"
        assert not diff_result.new_entries
        assert not diff_result.removed_entries


# ====== Test data ====
get_key_list_test_data = '''#
msgid ""
msgstr ""
"Project-Id-Version: SmartGit\\n"
"Report-Msgid-Bugs-To: https://github.com/syntevo/smartgit-translations\\n"
"POT-Creation-Date: 2024-03-25 10:00+0900\\n"
"PO-Revision-Date: 2024-03-25 10:00+0900\\n"
"Last-Translator: \\n"
"Language-Team: \\n"
"Language: ja\\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=UTF-8\\n"
"Content-Transfer-Encoding: 8bit\\n"
"Plural-Forms: nplurals=1; plural=0;\\n"

msgctxt "context:"
msgid "msgid_1"
msgstr "msgstr_1"

msgctxt "context:"
msgid "msgid_2"
msgstr "msgstr_2"

msgctxt "unique_key_1"
msgid "unique_msgid_1"
msgstr "unique_msgstr_1"

msgctxt "unique_key_2"
msgid "unique_msgid_2"
msgstr "unique_msgstr_2"'''

expected_key_list = [
    KeyTuple(msgctxt="context:", msgid="msgid_1"),
    KeyTuple(msgctxt="context:", msgid="msgid_2"),
    KeyTuple(msgctxt="unique_key_1", msgid=""),
    KeyTuple(msgctxt="unique_key_2", msgid=""),
]
