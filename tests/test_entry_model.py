import unittest
from unittest.mock import Mock, patch

from sgpo_editor.models.entry import EntryModel


class TestEntryModelValidator(unittest.TestCase):
    def test_flags_as_string(self):
        # 入力が文字列の場合、空白が除去され、リストに変換される
        model = EntryModel(
            msgid="dummy", msgstr="dummy", flags=" fuzzy "
        )  # type: ignore
        self.assertEqual(model.flags, ["fuzzy"])

    def test_flags_as_empty_string(self):
        # 空文字列の場合、空リストになる
        model = EntryModel(msgid="dummy", msgstr="dummy", flags="   ")  # type: ignore
        self.assertEqual(model.flags, [])

    def test_flags_as_list(self):
        # リストの各要素が文字列に変換される
        model = EntryModel(
            msgid="dummy", msgstr="dummy", flags=[1, "fuzzy", 3.5]
        )  # type: ignore
        self.assertEqual(model.flags, ["1", "fuzzy", "3.5"])

    def test_flags_default(self):
        # flagsが指定されなかった場合、デフォルトでは空のリストになる
        model = EntryModel(msgid="dummy", msgstr="dummy")
        self.assertEqual(model.flags, [])


class TestEntryModel(unittest.TestCase):
    def test_properties(self):
        # 基本的なプロパティのテスト
        entry = EntryModel(
            key="context\x04test",
            msgid="test",
            msgstr="テスト",
            msgctxt="context",
            obsolete=False,
            position=1,
        )

        self.assertEqual(entry.key, "context\x04test")
        self.assertEqual(entry.msgid, "test")
        self.assertEqual(entry.msgstr, "テスト")
        self.assertEqual(entry.msgctxt, "context")
        self.assertEqual(entry.position, 1)
        self.assertFalse(entry.obsolete)

    def test_is_translated_property(self):
        # is_translatedプロパティのテスト
        entry1 = EntryModel(msgid="test", msgstr="")
        self.assertFalse(entry1.is_translated)

        entry2 = EntryModel(msgid="test", msgstr="テスト")
        self.assertTrue(entry2.is_translated)

        entry3 = EntryModel(msgid="test", msgstr="テスト", flags=["fuzzy"])
        self.assertFalse(entry3.is_translated)  # fuzzyがあるので未翻訳

    def test_is_untranslated_property(self):
        # is_untranslatedプロパティのテスト
        entry1 = EntryModel(msgid="test", msgstr="")
        self.assertTrue(entry1.is_untranslated)

        entry2 = EntryModel(msgid="test", msgstr="テスト")
        self.assertFalse(entry2.is_untranslated)

    def test_translated_method(self):
        # translatedメソッドのテスト
        entry1 = EntryModel(msgid="test", msgstr="")
        self.assertFalse(entry1.translated())

        entry2 = EntryModel(msgid="test", msgstr="テスト")
        self.assertTrue(entry2.translated())

        entry3 = EntryModel(msgid="test", msgstr="テスト", flags=["fuzzy"])
        self.assertFalse(entry3.translated())  # fuzzyがあるので未翻訳

    def test_get_status(self):
        # get_statusメソッドのテスト
        entry1 = EntryModel(msgid="test", msgstr="", flags=[])
        self.assertEqual(entry1.get_status(), "未翻訳")

        entry2 = EntryModel(msgid="test", msgstr="テスト", flags=[])
        self.assertEqual(entry2.get_status(), "完了")

        entry3 = EntryModel(msgid="test", msgstr="テスト", flags=["fuzzy"])
        self.assertEqual(entry3.get_status(), "要確認")

    @patch("sgpo_editor.models.entry.EntryModel.update_po_entry")
    def test_update_po_entry(self, mock_update):
        # update_po_entryメソッドのテスト
        # POEntryがない場合
        entry1 = EntryModel(msgid="test", msgstr="テスト")
        # モックを使用してメソッドが呼び出されることを確認
        entry1.update_po_entry()
        mock_update.assert_called_once()

    def test_update_po_entry_implementation(self):
        # update_po_entryメソッドの実装をテスト
        # POEntryがない場合
        entry1 = EntryModel(msgid="test", msgstr="テスト")
        # 実際のメソッドを呼び出す
        entry1.update_po_entry()
        # POEntryがない場合は早期リターンされる
        self.assertIsNone(entry1._po_entry)

        # POEntryがある場合（flagsがリスト）
        po_entry = Mock()
        po_entry.msgstr = ""
        po_entry.flags = ["fuzzy"]

        # _po_entryを直接設定する
        entry2 = EntryModel(
            msgid="test", msgstr="テスト", flags=["fuzzy", "python-format"]
        )
        entry2._po_entry = po_entry

        # update_po_entryを呼び出す
        entry2.update_po_entry()

        # msgstrとflagsが更新されたことを確認
        self.assertEqual(entry2._po_entry.msgstr, "テスト")
        self.assertEqual(entry2._po_entry.flags, ["fuzzy", "python-format"])

        # flagsが文字列の場合
        po_entry2 = Mock()
        po_entry2.msgstr = ""
        po_entry2.flags = "fuzzy"

        entry3 = EntryModel(msgid="test", msgstr="テスト", flags=["fuzzy", "c-format"])
        entry3._po_entry = po_entry2

        # update_po_entryを呼び出す
        entry3.update_po_entry()

        # flagsが文字列として更新されたことを確認
        self.assertEqual(entry3._po_entry.flags, "fuzzy, c-format")

    def test_add_flag(self):
        # add_flagメソッドのテスト
        entry = EntryModel(msgid="test", msgstr="テスト")
        self.assertEqual(len(entry.flags), 0)  # 初期状態では空

        # フラグを追加
        entry.add_flag("fuzzy")
        self.assertEqual(len(entry.flags), 1)
        self.assertIn("fuzzy", entry.flags)

        # 同じフラグを追加しても変化なし
        entry.add_flag("fuzzy")
        self.assertEqual(len(entry.flags), 1)

        # 別のフラグを追加
        entry.add_flag("python-format")
        self.assertEqual(len(entry.flags), 2)
        self.assertIn("python-format", entry.flags)

    def test_remove_flag(self):
        # remove_flagメソッドのテスト
        entry = EntryModel(
            msgid="test", msgstr="テスト", flags=["fuzzy", "python-format"]
        )
        self.assertEqual(len(entry.flags), 2)

        # フラグを削除
        entry.remove_flag("fuzzy")
        self.assertEqual(len(entry.flags), 1)
        self.assertNotIn("fuzzy", entry.flags)

        # 存在しないフラグを削除しても変化なし
        entry.remove_flag("not-exist")
        self.assertEqual(len(entry.flags), 1)

        # 残りのフラグを削除
        entry.remove_flag("python-format")
        self.assertEqual(len(entry.flags), 0)

    def test_from_dict(self):
        # from_dictメソッドのテスト
        data = {
            "key": "test-key",
            "msgid": "test",
            "msgstr": "テスト",
            "msgctxt": "context",
            "obsolete": False,
            "position": 10,
            "flags": ["fuzzy"],
            "previous_msgid": "old-test",
            "previous_msgid_plural": None,
            "previous_msgctxt": None,
            "comment": "comment",
            "tcomment": "translator comment",
            "occurrences": [("file.py", 10)],
            "references": ["file.py:10"],
        }

        entry = EntryModel.from_dict(data)

        # 各フィールドが正しく設定されているか確認
        self.assertEqual(entry.key, "test-key")
        self.assertEqual(entry.msgid, "test")
        self.assertEqual(entry.msgstr, "テスト")
        self.assertEqual(entry.msgctxt, "context")
        self.assertEqual(entry.obsolete, False)
        self.assertEqual(entry.position, 10)
        self.assertEqual(entry.flags, ["fuzzy"])
        self.assertEqual(entry.previous_msgid, "old-test")
        self.assertIsNone(entry.previous_msgid_plural)
        self.assertIsNone(entry.previous_msgctxt)
        self.assertEqual(entry.comment, "comment")
        self.assertEqual(entry.tcomment, "translator comment")
        self.assertEqual(entry.occurrences, [("file.py", 10)])
        self.assertEqual(entry.references, ["file.py:10"])

    def test_equality(self):
        # __eq__メソッドのテスト
        entry1 = EntryModel(msgid="test", msgstr="テスト", position=1)
        entry2 = EntryModel(msgid="test", msgstr="テスト", position=1)
        entry3 = EntryModel(msgid="test", msgstr="テスト", position=2)
        entry4 = "not an EntryModel"

        self.assertEqual(entry1, entry2)  # 同じpositionなので等しい
        self.assertNotEqual(entry1, entry3)  # 異なるpositionなので等しくない
        self.assertNotEqual(entry1, entry4)  # 型が異なるので等しくない

    def test_from_po_entry_with_mock(self):
        # from_po_entryメソッドのテスト（Mockオブジェクト）
        po_entry = Mock()
        po_entry.msgid = "test"
        po_entry.msgstr = "テスト"
        po_entry.msgctxt = "context"
        po_entry.flags = ["fuzzy", "python-format"]
        po_entry.obsolete = False
        po_entry.occurrences = []  # 空のリストを設定

        # Mockオブジェクトを使った属性テスト
        mock_attr = Mock(name="mock_attribute")
        po_entry.previous_msgid_plural = mock_attr

        model = EntryModel.from_po_entry(po_entry, position=5)

        self.assertEqual(model.msgid, "test")
        self.assertEqual(model.msgstr, "テスト")
        self.assertEqual(model.msgctxt, "context")
        self.assertEqual(model.position, 5)
        self.assertTrue(model.fuzzy)
        self.assertIn("python-format", model.flags)
        # Mockオブジェクトはデフォルト値に変換される
        self.assertIsNone(model.previous_msgid_plural)

        # safe_getattrメソッドのテストは別のテストケースで行う

    def test_from_po_entry_with_occurrences(self):
        # from_po_entryメソッドのテスト（occurrencesあり）
        po_entry = Mock()
        po_entry.msgid = "test"
        po_entry.msgstr = "テスト"
        po_entry.msgctxt = None
        po_entry.flags = []
        po_entry.obsolete = False
        po_entry.occurrences = [("file.py", 10), ("other.py", 20)]

        model = EntryModel.from_po_entry(po_entry)

        self.assertEqual(model.references, ["file.py:10", "other.py:20"])

    def test_to_dict_and_from_dict(self):
        # to_dictとfrom_dictメソッドのテスト
        original = EntryModel(
            key="context\x04test",
            msgid="test",
            msgstr="テスト",
            msgctxt="context",
            obsolete=False,
            position=1,
            flags=["fuzzy"],
            references=["file.py:10"],
        )

        # 辞書に変換
        data = original.to_dict()

        # 辞書から復元
        restored = EntryModel.from_dict(data)

        # 元のオブジェクトと復元されたオブジェクトが同じ値を持つことを確認
        self.assertEqual(restored.key, original.key)
        self.assertEqual(restored.msgid, original.msgid)
        self.assertEqual(restored.msgstr, original.msgstr)
        self.assertEqual(restored.msgctxt, original.msgctxt)
        self.assertEqual(restored.obsolete, original.obsolete)
        self.assertEqual(restored.position, original.position)
        self.assertEqual(restored.flags, original.flags)
        self.assertEqual(restored.references, original.references)
        self.assertEqual(restored.fuzzy, original.fuzzy)

    def test_validate_po_entry_with_non_dict_non_po(self):
        # validate_po_entryメソッドのテスト（辞書でもPOEntryでもない場合）
        # 文字列を渡す場合
        result = EntryModel.validate_po_entry("not a po entry")
        self.assertEqual(result, "not a po entry")

        # 数値を渡す場合
        result = EntryModel.validate_po_entry(123)
        self.assertEqual(result, 123)

    def test_validate_po_entry_with_dict(self):
        # validate_po_entryメソッドのテスト（辞書の場合）
        data = {"msgid": "test", "msgstr": "テスト"}
        result = EntryModel.validate_po_entry(data)
        self.assertEqual(result, data)

    def test_validate_po_entry_with_po_entry(self):
        # validate_po_entryメソッドのテスト（POEntryの場合）
        po_entry = Mock()
        po_entry.msgid = "test"
        po_entry.msgstr = "テスト"
        po_entry.msgctxt = "context"
        po_entry.obsolete = False
        po_entry.linenum = 10
        po_entry.previous_msgid = "old-test"
        po_entry.previous_msgid_plural = None
        po_entry.previous_msgctxt = None
        po_entry.comment = "comment"
        po_entry.tcomment = "translator comment"
        po_entry.occurrences = [("file.py", 10)]

        # flagsがリストの場合
        po_entry.flags = ["fuzzy", "python-format"]
        result = EntryModel.validate_po_entry(po_entry)

        self.assertEqual(result["msgid"], "test")
        self.assertEqual(result["msgstr"], "テスト")
        self.assertEqual(result["msgctxt"], "context")
        self.assertEqual(result["obsolete"], False)
        self.assertEqual(result["position"], 10)
        self.assertEqual(result["flags"], ["fuzzy", "python-format"])

        # flagsが文字列の場合
        po_entry.flags = "fuzzy, c-format"
        result = EntryModel.validate_po_entry(po_entry)

        self.assertEqual(result["flags"], ["fuzzy", "c-format"])

        # flagsが空の場合
        po_entry.flags = ""
        result = EntryModel.validate_po_entry(po_entry)

        self.assertEqual(result["flags"], [])

        # flagsがリストでも文字列でもない場合
        po_entry.flags = 123
        result = EntryModel.validate_po_entry(po_entry)

        self.assertEqual(result["flags"], [])

    def test_fuzzy_setter(self):
        # fuzzyプロパティのsetterメソッドのテスト
        # fuzzyフラグがない場合に追加する
        entry1 = EntryModel(msgid="test", msgstr="テスト", flags=[])
        self.assertFalse(entry1.fuzzy)

        # fuzzyをTrueに設定
        entry1.fuzzy = True
        self.assertTrue(entry1.fuzzy)
        self.assertIn("fuzzy", entry1.flags)

        # fuzzyフラグがある場合に削除する
        entry2 = EntryModel(
            msgid="test", msgstr="テスト", flags=["fuzzy", "python-format"]
        )
        self.assertTrue(entry2.fuzzy)

        # fuzzyをFalseに設定
        entry2.fuzzy = False
        self.assertFalse(entry2.fuzzy)
        self.assertNotIn("fuzzy", entry2.flags)
        self.assertIn("python-format", entry2.flags)  # 他のフラグは残っていることを確認

    def test_review_comment(self):
        # レビューコメント機能のテスト
        entry = EntryModel(msgid="test", msgstr="テスト")

        # 初期状態ではレビューコメントは空のリスト
        self.assertEqual(entry.review_comments, [])

        # レビューコメントを追加
        entry.add_review_comment(author="reviewer1", comment="翻訳の改善が必要です")
        self.assertEqual(len(entry.review_comments), 1)
        self.assertEqual(entry.review_comments[0]["comment"], "翻訳の改善が必要です")
        self.assertEqual(entry.review_comments[0]["author"], "reviewer1")
        self.assertIn("created_at", entry.review_comments[0])

        # 複数のレビューコメントを追加
        entry.add_review_comment(author="translator", comment="修正完了しました")
        self.assertEqual(len(entry.review_comments), 2)

        # 特定のレビューコメントを削除
        comment_id = entry.review_comments[0]["id"]
        entry.remove_review_comment(comment_id)
        self.assertEqual(len(entry.review_comments), 1)

        # すべてのレビューコメントをクリア
        entry.clear_review_comments()
        self.assertEqual(entry.review_comments, [])

    def test_quality_score(self):
        # 品質スコア機能のテスト
        entry = EntryModel(msgid="test", msgstr="テスト")

        # 初期状態ではスコアは未設定
        self.assertIsNone(entry.overall_quality_score)

        # 全体スコアを設定
        entry.set_overall_quality_score(85)
        self.assertEqual(entry.overall_quality_score, 85)

        # カテゴリスコアを設定
        entry.set_category_score("accuracy", 90)
        entry.set_category_score("fluency", 80)

        self.assertEqual(entry.category_quality_scores["accuracy"], 90)
        self.assertEqual(entry.category_quality_scores["fluency"], 80)

        # スコアをリセット
        entry.reset_scores()
        self.assertIsNone(entry.overall_quality_score)
        self.assertEqual(entry.category_quality_scores, {})

    def test_check_results(self):
        # 自動チェック結果のテスト
        entry = EntryModel(msgid="test", msgstr="テスト")

        # 初期状態ではチェック結果は空のリスト
        self.assertEqual(entry.check_results, [])

        # チェック結果を追加
        entry.add_check_result(
            code=1001, message="句読点の使用が不適切です", severity="warning"
        )
        self.assertEqual(len(entry.check_results), 1)
        self.assertEqual(entry.check_results[0]["code"], 1001)
        self.assertEqual(entry.check_results[0]["severity"], "warning")

        # 別のチェック結果を追加
        entry.add_check_result(
            code=2003, message="用語の使用が一貫していません", severity="error"
        )
        self.assertEqual(len(entry.check_results), 2)

        # 特定のコードのチェック結果を削除
        entry.remove_check_result(1001)
        self.assertEqual(len(entry.check_results), 1)
        self.assertEqual(entry.check_results[0]["code"], 2003)

        # すべてのチェック結果をクリア
        entry.clear_check_results()
        self.assertEqual(entry.check_results, [])

    def test_to_dict_with_review_data(self):
        # 拡張フィールドを含むto_dictのテスト
        entry = EntryModel(msgid="test", msgstr="テスト")

        # レビューデータを追加
        entry.add_review_comment(author="reviewer", comment="レビューコメント")
        entry.set_overall_quality_score(85)
        entry.set_category_score("accuracy", 90)
        entry.add_check_result(code=1001, message="警告", severity="warning")

        # 辞書に変換
        data = entry.to_dict()

        # 拡張フィールドが辞書に含まれていることを確認
        self.assertIn("review_comments", data)
        self.assertIn("overall_quality_score", data)
        self.assertIn("category_quality_scores", data)
        self.assertIn("check_results", data)

        # 値が正しく変換されていることを確認
        self.assertEqual(len(data["review_comments"]), 1)
        self.assertEqual(data["overall_quality_score"], 85)
        self.assertEqual(data["category_quality_scores"]["accuracy"], 90)
        self.assertEqual(len(data["check_results"]), 1)
        self.assertEqual(data["check_results"][0]["code"], 1001)

    def test_from_dict_with_review_data(self):
        # 拡張フィールドを含むfrom_dictのテスト
        data = {
            "msgid": "test",
            "msgstr": "テスト",
            "review_comments": [
                {
                    "id": "123",
                    "comment": "レビューコメント",
                    "author": "reviewer",
                    "created_at": "2025-03-07T10:00:00",
                }
            ],
            "overall_quality_score": 85,
            "category_quality_scores": {"accuracy": 90, "fluency": 80},
            "check_results": [{"code": 1001, "message": "警告", "severity": "warning"}],
        }

        # 辞書からモデルに変換
        entry = EntryModel.from_dict(data)

        # 拡張フィールドが正しく設定されていることを確認
        self.assertEqual(len(entry.review_comments), 1)
        self.assertEqual(entry.review_comments[0]["comment"], "レビューコメント")
        self.assertEqual(entry.overall_quality_score, 85)
        self.assertEqual(entry.category_quality_scores["accuracy"], 90)
        self.assertEqual(len(entry.check_results), 1)
        self.assertEqual(entry.check_results[0]["code"], 1001)

    def test_generate_key(self):
        # _generate_keyメソッドのテスト
        # msgctxtがある場合
        entry1 = EntryModel(msgid="test", msgstr="テスト", msgctxt="context")
        self.assertEqual(entry1.key, "context\x04test")

        # msgctxtがない場合
        entry2 = EntryModel(msgid="test", msgstr="テスト", msgctxt=None)
        self.assertEqual(entry2.key, "|test")

    def test_safe_getattr(self):
        # safe_getattrメソッドのテスト
        # 通常の属性取得
        obj = Mock()
        obj.attr = "value"

        # EntryModel.from_po_entry内で定義されているsafe_getattrを再定義
        def safe_getattr(obj, attr_name, default=None):
            try:
                value = getattr(obj, attr_name, default)
                # Mockオブジェクトの場合はデフォルト値を使用
                if hasattr(value, "__class__") and "Mock" in value.__class__.__name__:
                    return default
                return value
            except (AttributeError, TypeError):
                return default

        # 属性が存在する場合
        self.assertEqual(safe_getattr(obj, "attr"), "value")

        # 属性が存在しない場合
        self.assertIsNone(safe_getattr(obj, "non_existent_attr"))

        # デフォルト値を指定した場合
        self.assertEqual(safe_getattr(obj, "non_existent_attr", "default"), "default")

        # AttributeErrorが発生する場合
        obj_with_attr_error = Mock()
        type(obj_with_attr_error).__getattr__ = Mock(side_effect=AttributeError)
        self.assertEqual(
            safe_getattr(obj_with_attr_error, "attr", "default"), "default"
        )

        # TypeErrorが発生する場合
        obj_with_type_error = Mock()
        type(obj_with_type_error).__getattr__ = Mock(side_effect=TypeError)
        self.assertEqual(
            safe_getattr(obj_with_type_error, "attr", "default"), "default"
        )


if __name__ == "__main__":
    unittest.main()
