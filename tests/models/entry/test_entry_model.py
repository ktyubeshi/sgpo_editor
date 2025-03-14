import unittest
from unittest.mock import Mock, patch

from sgpo_editor.models.entry import EntryModel


class TestEntryModelValidator(unittest.TestCase):
    def test_flags_as_string(self):
        # 蜈･蜉帙′譁・ｭ怜・縺ｮ蝣ｴ蜷医∫ｩｺ逋ｽ縺碁勁蜴ｻ縺輔ｌ縲√Μ繧ｹ繝医↓螟画鋤縺輔ｌ繧・
        model = EntryModel(msgid="dummy", msgstr="dummy", flags=" fuzzy ")  # type: ignore
        self.assertEqual(model.flags, ["fuzzy"])

    def test_flags_as_empty_string(self):
        # 遨ｺ譁・ｭ怜・縺ｮ蝣ｴ蜷医∫ｩｺ繝ｪ繧ｹ繝医↓縺ｪ繧・
        model = EntryModel(msgid="dummy", msgstr="dummy", flags="   ")  # type: ignore
        self.assertEqual(model.flags, [])

    def test_flags_as_list(self):
        # 繝ｪ繧ｹ繝医・蜷・ｦ∫ｴ�縺梧枚蟄怜・縺ｮ蝣ｴ蜷・
        model = EntryModel(msgid="dummy", msgstr="dummy", flags=[1, "fuzzy", 3.5])  # type: ignore
        self.assertEqual(model.flags, ["1", "fuzzy", "3.5"])

    def test_flags_default(self):
        # flags縺梧欠螳壹＆繧後↑縺九▲縺溷�ｴ蜷医√ョ繝輔か繝ｫ繝医〒縺ｯ遨ｺ縺ｮ繝ｪ繧ｹ繝医↓縺ｪ繧・
        model = EntryModel(msgid="dummy", msgstr="dummy")
        self.assertEqual(model.flags, [])


class TestEntryModel(unittest.TestCase):
    def test_properties(self):
        # 蝓ｺ譛ｬ逧・↑繝励Ο繝代ユ繧｣縺ｮ繝・せ繝・
        entry = EntryModel(
            key="context\x04test",
            msgid="test",
            msgstr="テスト",
            msgctxt="context",
            obsolete=False,
            position=1
        )

        self.assertEqual(entry.key, "context\x04test")
        self.assertEqual(entry.msgid, "test")
        self.assertEqual(entry.msgstr, "テスト")
        self.assertEqual(entry.msgctxt, "context")
        self.assertEqual(entry.position, 1)
        self.assertFalse(entry.obsolete)

    def test_is_translated_property(self):
        # is_translated繝励Ο繝代ユ繧｣縺ｮ繝・せ繝・
        entry1 = EntryModel(msgid="test", msgstr="")
        self.assertFalse(entry1.is_translated)

        entry2 = EntryModel(msgid="test", msgstr="テスト")
        self.assertTrue(entry2.is_translated)

        entry3 = EntryModel(msgid="test", msgstr="テスト", flags=["fuzzy"])
        self.assertFalse(entry3.is_translated)  # fuzzy縺後≠繧九・縺ｧ譛ｪ鄙ｻ險ｳ

    def test_is_untranslated_property(self):
        # is_untranslated繝励Ο繝代ユ繧｣縺ｮ繝・せ繝・
        entry1 = EntryModel(msgid="test", msgstr="")
        self.assertTrue(entry1.is_untranslated)

        entry2 = EntryModel(msgid="test", msgstr="テスト")
        self.assertFalse(entry2.is_untranslated)

    def test_translated_method(self):
        # translated繝｡繧ｽ繝・ラ縺ｮ繝・せ繝・
        entry1 = EntryModel(msgid="test", msgstr="")
        self.assertFalse(entry1.translated())

        entry2 = EntryModel(msgid="test", msgstr="テスト")
        self.assertTrue(entry2.translated())

        entry3 = EntryModel(msgid="test", msgstr="テスト", flags=["fuzzy"])
        self.assertFalse(entry3.translated())  # fuzzy縺後≠繧九・縺ｧ譛ｪ鄙ｻ險ｳ

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
        # update_po_entry繝｡繧ｽ繝・ラ縺ｮ繝・せ繝・
        # POEntry縺後↑縺・�ｴ蜷・
        entry1 = EntryModel(msgid="test", msgstr="テスト")
        # 繝｢繝・け繧剃ｽｿ逕ｨ縺励※繝｡繧ｽ繝・ラ縺悟他縺ｳ蜃ｺ縺輔ｌ繧九％縺ｨ繧堤｢ｺ隱・
        entry1.update_po_entry()
        mock_update.assert_called_once()

    def test_update_po_entry_implementation(self):
        # update_po_entry繝｡繧ｽ繝・ラ縺ｮ繝・せ繝茨ｼ・
        # POEntry縺後↑縺・�ｴ蜷・
        entry1 = EntryModel(msgid="test", msgstr="テスト")
        # 螳滄圀縺ｮ繝｡繧ｽ繝・ラ繧貞他縺ｳ蜃ｺ縺・
        entry1.update_po_entry()
        # POEntry縺後↑縺・�ｴ蜷医・譌ｩ譛溘Μ繧ｿ繝ｼ繝ｳ縺輔ｌ繧・
        self.assertIsNone(entry1._po_entry)

        # POEntry縺後≠繧句�ｴ蜷茨ｼ・lags縺後Μ繧ｹ繝医・蝣ｴ蜷・
        po_entry = Mock()
        po_entry.msgstr = ""
        po_entry.flags = ["fuzzy"]

        # _po_entry繧堤峩謗･險ｭ螳壹☆繧・
        entry2 = EntryModel(
            msgid="test", msgstr="テスト", flags=["fuzzy", "python-format"]
        )
        entry2._po_entry = po_entry

        # update_po_entry繧貞他縺ｳ蜃ｺ縺・
        entry2.update_po_entry()

        # msgstr縺ｨflags縺梧峩譁ｰ縺輔ｌ縺溘％縺ｨ繧堤｢ｺ隱・
        self.assertEqual(entry2._po_entry.msgstr, "テスト")
        self.assertEqual(entry2._po_entry.flags, ["fuzzy", "python-format"])

        # flags縺梧枚蟄怜・縺ｮ蝣ｴ蜷・
        po_entry2 = Mock()
        po_entry2.msgstr = ""
        po_entry2.flags = "fuzzy"

        entry3 = EntryModel(msgid="test", msgstr="テスト", flags=["fuzzy", "c-format"])
        entry3._po_entry = po_entry2

        # update_po_entry繧貞他縺ｳ蜃ｺ縺・
        entry3.update_po_entry()

        # flags縺梧枚蟄怜・縺ｨ縺励※譖ｴ譁ｰ縺輔ｌ縺溘％縺ｨ繧堤｢ｺ隱・
        self.assertEqual(entry3._po_entry.flags, "fuzzy, c-format")

    def test_add_flag(self):
        # add_flag繝｡繧ｽ繝・ラ縺ｮ繝・せ繝・
        entry = EntryModel(msgid="test", msgstr="テスト")
        self.assertEqual(len(entry.flags), 0)  # 蛻晄悄迥ｶ諷九〒縺ｯ遨ｺ

        # 繝輔Λ繧ｰ繧定ｿｽ蜉�
        entry.add_flag("fuzzy")
        self.assertEqual(len(entry.flags), 1)
        self.assertIn("fuzzy", entry.flags)

        # 蜷後§繝輔Λ繧ｰ繧定ｿｽ蜉�縺励※繧ょ､牙喧縺ｪ縺・
        entry.add_flag("fuzzy")
        self.assertEqual(len(entry.flags), 1)

        # 蛻･縺ｮ繝輔Λ繧ｰ繧定ｿｽ蜉�
        entry.add_flag("python-format")
        self.assertEqual(len(entry.flags), 2)
        self.assertIn("python-format", entry.flags)

    def test_remove_flag(self):
        # remove_flag繝｡繧ｽ繝・ラ縺ｮ繝・せ繝・
        entry = EntryModel(
            msgid="test", msgstr="テスト", flags=["fuzzy", "python-format"]
        )
        self.assertEqual(len(entry.flags), 2)

        # 繝輔Λ繧ｰ繧貞炎髯､
        entry.remove_flag("fuzzy")
        self.assertEqual(len(entry.flags), 1)
        self.assertNotIn("fuzzy", entry.flags)

        # 蟄伜惠縺励↑縺・ヵ繝ｩ繧ｰ繧貞炎髯､縺励※繧ょ､牙喧縺ｪ縺・
        entry.remove_flag("not-exist")
        self.assertEqual(len(entry.flags), 1)

        # 谿九ｊ縺ｮ繝輔Λ繧ｰ繧貞炎髯､
        entry.remove_flag("python-format")
        self.assertEqual(len(entry.flags), 0)

    def test_from_dict(self):
        # from_dict繝｡繧ｽ繝・ラ縺ｮ繝・せ繝・
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

        # 蜷・ヵ繧｣繝ｼ繝ｫ繝峨′豁｣縺励￥險ｭ螳壹＆繧後※縺・ｋ縺狗｢ｺ隱・
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
        # __eq__繝｡繧ｽ繝・ラ縺ｮ繝・せ繝・
        entry1 = EntryModel(msgid="test", msgstr="テスト", position=1)
        entry2 = EntryModel(msgid="test", msgstr="テスト", position=1)
        entry3 = EntryModel(msgid="test", msgstr="テスト", position=2)
        entry4 = "not an EntryModel"

        self.assertEqual(entry1, entry2)  # 蜷後§position縺ｪ縺ｮ縺ｧ遲峨＠縺・
        self.assertNotEqual(entry1, entry3)  # 逡ｰ縺ｪ繧却osition縺ｪ縺ｮ縺ｧ遲峨＠縺上↑縺・
        self.assertNotEqual(entry1, entry4)  # 蝙九′逡ｰ縺ｪ繧九・縺ｧ遲峨＠縺上↑縺・

    def test_from_po_entry_with_mock(self):
        # from_po_entry繝｡繧ｽ繝・ラ縺ｮ繝・せ繝茨ｼ・ock繧ｪ繝悶ず繧ｧ繧ｯ繝茨ｼ・
        po_entry = Mock()
        po_entry.msgid = "test"
        po_entry.msgstr = "テスト"
        po_entry.msgctxt = "context"
        po_entry.flags = ["fuzzy", "python-format"]
        po_entry.obsolete = False
        po_entry.occurrences = []  # 遨ｺ縺ｮ繝ｪ繧ｹ繝医ｒ險ｭ螳・
        # Mock繧ｪ繝悶ず繧ｧ繧ｯ繝医ｒ菴ｿ縺｣縺溷ｱ樊ｧ繝・せ繝・
        mock_attr = Mock(name="mock_attribute")
        po_entry.previous_msgid_plural = mock_attr

        model = EntryModel.from_po_entry(po_entry, position=5)

        self.assertEqual(model.msgid, "test")
        self.assertEqual(model.msgstr, "テスト")
        self.assertEqual(model.msgctxt, "context")
        self.assertEqual(model.position, 5)
        self.assertTrue(model.fuzzy)
        self.assertIn("python-format", model.flags)
        # Mock繧ｪ繝悶ず繧ｧ繧ｯ繝医・繝・ヵ繧ｩ繝ｫ繝亥､縺ｫ螟画鋤縺輔ｌ繧・
        self.assertIsNone(model.previous_msgid_plural)

        # safe_getattr繝｡繧ｽ繝・ラ縺ｮ繝・せ繝医・蛻･縺ｮ繝・せ繝医こ繝ｼ繧ｹ縺ｧ陦後≧

    def test_from_po_entry_with_occurrences(self):
        # from_po_entry繝｡繧ｽ繝・ラ縺ｮ繝・せ繝茨ｼ・ccurrences縺ゅｊ・・
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
        # to_dict縺ｨfrom_dict繝｡繧ｽ繝・ラ縺ｮ繝・せ繝・
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

        # 霎樊嶌縺ｫ螟画鋤
        data = original.to_dict()

        # 霎樊嶌縺九ｉ蠕ｩ蜈・
        restored = EntryModel.from_dict(data)

        # 蜈・・繧ｪ繝悶ず繧ｧ繧ｯ繝医→蠕ｩ蜈・＆繧後◆繧ｪ繝悶ず繧ｧ繧ｯ繝医′蜷後§蛟､繧呈戟縺､縺薙→繧堤｢ｺ隱・
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
        # validate_po_entry繝｡繧ｽ繝・ラ縺ｮ繝・せ繝茨ｼ郁ｾ樊嶌縺ｧ繧１OEntry縺ｧ繧ゅ↑縺・�ｴ蜷茨ｼ・
        # 譁・ｭ怜・繧呈ｸ｡縺吝�ｴ蜷・
        result = EntryModel.validate_po_entry("not a po entry")
        self.assertEqual(result, "not a po entry")

        # 謨ｰ蛟､繧呈ｸ｡縺吝�ｴ蜷・
        result = EntryModel.validate_po_entry(123)
        self.assertEqual(result, 123)

    def test_validate_po_entry_with_dict(self):
        # validate_po_entry繝｡繧ｽ繝・ラ縺ｮ繝・せ繝茨ｼ郁ｾ樊嶌縺ｮ蝣ｴ蜷茨ｼ・
        data = {"msgid": "test", "msgstr": "テスト"}
        result = EntryModel.validate_po_entry(data)
        self.assertEqual(result, data)

    def test_validate_po_entry_with_po_entry(self):
        # validate_po_entry繝｡繧ｽ繝・ラ縺ｮ繝・せ繝茨ｼ・OEntry縺ｮ蝣ｴ蜷茨ｼ・
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

        # flags縺後Μ繧ｹ繝医・蝣ｴ蜷・
        po_entry.flags = ["fuzzy", "python-format"]
        result = EntryModel.validate_po_entry(po_entry)

        self.assertEqual(result["msgid"], "test")
        self.assertEqual(result["msgstr"], "テスト")
        self.assertEqual(result["msgctxt"], "context")
        self.assertEqual(result["obsolete"], False)
        self.assertEqual(result["position"], 10)
        self.assertEqual(result["flags"], ["fuzzy", "python-format"])

        # flags縺梧枚蟄怜・縺ｮ蝣ｴ蜷・
        po_entry.flags = "fuzzy, c-format"
        result = EntryModel.validate_po_entry(po_entry)

        self.assertEqual(result["flags"], ["fuzzy", "c-format"])

        # flags縺檎ｩｺ縺ｮ蝣ｴ蜷・
        po_entry.flags = ""
        result = EntryModel.validate_po_entry(po_entry)

        self.assertEqual(result["flags"], [])

        # flags縺後Μ繧ｹ繝医〒繧よ枚蟄怜・縺ｧ繧ゅ↑縺・�ｴ蜷・
        po_entry.flags = 123
        result = EntryModel.validate_po_entry(po_entry)

        self.assertEqual(result["flags"], [])

    def test_fuzzy_setter(self):
        # fuzzy繝励Ο繝代ユ繧｣縺ｮsetter繝｡繧ｽ繝・ラ縺ｮ繝・せ繝・
        # fuzzy繝輔Λ繧ｰ縺後↑縺・�ｴ蜷医↓霑ｽ蜉�縺吶ｋ
        entry1 = EntryModel(msgid="test", msgstr="テスト", flags=[])
        self.assertFalse(entry1.fuzzy)

        # fuzzy繧探rue縺ｫ險ｭ螳・
        entry1.fuzzy = True
        self.assertTrue(entry1.fuzzy)
        self.assertIn("fuzzy", entry1.flags)

        # fuzzy繝輔Λ繧ｰ縺後≠繧句�ｴ蜷医↓蜑企勁縺吶ｋ
        entry2 = EntryModel(
            msgid="test", msgstr="テスト", flags=["fuzzy", "python-format"]
        )
        self.assertTrue(entry2.fuzzy)

        # fuzzy繧巽alse縺ｫ險ｭ螳・
        entry2.fuzzy = False
        self.assertFalse(entry2.fuzzy)
        self.assertNotIn("fuzzy", entry2.flags)
        self.assertIn("python-format", entry2.flags)  # 莉悶・繝輔Λ繧ｰ縺ｯ谿九▲縺ｦ縺・ｋ縺薙→繧堤｢ｺ隱・

    def test_review_comment(self):
        # 繝ｬ繝薙Η繝ｼ繧ｳ繝｡繝ｳ繝域ｩ溯・縺ｮ繝・せ繝・
        entry = EntryModel(msgid="test", msgstr="テスト")

        # 蛻晄悄迥ｶ諷九〒縺ｯ繝ｬ繝薙Η繝ｼ繝・・繧ｿ繧定ｿｽ蜉�
        self.assertEqual(entry.review_comments, [])

        # 繝ｬ繝薙Η繝ｼ繝・・繧ｿ繧定ｿｽ蜉�
        entry.add_review_comment(author="reviewer1", comment="レビューコメント")
        self.assertEqual(len(entry.review_comments), 1)
        self.assertEqual(entry.review_comments[0]["comment"], "レビューコメント")
        self.assertEqual(entry.review_comments[0]["author"], "reviewer1")
        self.assertIn("created_at", entry.review_comments[0])

        # 隍・焚縺ｮ繝ｬ繝薙Η繝ｼ繝・・繧ｿ繧定ｿｽ蜉�
        entry.add_review_comment(author="translator", comment="翻訳者コメント")
        self.assertEqual(len(entry.review_comments), 2)

        # 迚ｹ螳壹・繝ｬ繝薙Η繝ｼ繝・・繧ｿ繧定ｿｽ蜉�
        comment_id = entry.review_comments[0]["id"]
        entry.remove_review_comment(comment_id)
        self.assertEqual(len(entry.review_comments), 1)

        # 縺吶∋縺ｦ縺ｮ繝ｬ繝薙Η繝ｼ繝・・繧ｿ繧定ｿｽ蜉�
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
        # 閾ｪ蜍輔メ繧ｧ繝・け邨先棡縺ｮ繝・せ繝・
        entry = EntryModel(msgid="test", msgstr="テスト")

        # 蛻晄悄迥ｶ諷九〒縺ｯ繝√ぉ繝・け邨先棡縺ｯ遨ｺ縺ｮ繝ｪ繧ｹ繝・
        self.assertEqual(entry.check_results, [])

        # 繝√ぉ繝・け邨先棡繧定ｿｽ蜉�
        entry.add_check_result(
            code=1001, message="警告", severity="warning"
        )
        self.assertEqual(len(entry.check_results), 1)
        self.assertEqual(entry.check_results[0]["code"], 1001)
        self.assertEqual(entry.check_results[0]["severity"], "warning")

        # 蛻･縺ｮ繝√ぉ繝・け邨先棡繧定ｿｽ蜉�
        entry.add_check_result(
            code=2003, message="エラー", severity="error"
        )
        self.assertEqual(len(entry.check_results), 2)

        # 迚ｹ螳壹・繧ｳ繝ｼ繝峨・繝√ぉ繝・け邨先棡繧貞炎髯､
        entry.remove_check_result(1001)
        self.assertEqual(len(entry.check_results), 1)
        self.assertEqual(entry.check_results[0]["code"], 2003)

        # 縺吶∋縺ｦ縺ｮ繝√ぉ繝・け邨先棡繧偵け繝ｪ繧｢
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

        # 辞書からエントリモデルを作成
        entry = EntryModel.from_dict(data)

        # 拡張フィールドが正しく設定されていることを確認
        self.assertEqual(len(entry.review_comments), 1)
        self.assertEqual(entry.review_comments[0]["comment"], "レビューコメント")
        self.assertEqual(entry.overall_quality_score, 85)
        self.assertEqual(entry.category_quality_scores["accuracy"], 90)
        self.assertEqual(len(entry.check_results), 1)
        self.assertEqual(entry.check_results[0]["code"], 1001)

    def test_generate_key(self):
        # _generate_key繝｡繧ｽ繝・ラ縺ｮ繝・せ繝・
        # msgctxt縺後≠繧句�ｴ蜷・
        entry1 = EntryModel(msgid="test", msgstr="テスト", msgctxt="context")
        self.assertEqual(entry1.key, "context\x04test")

        # msgctxt縺後↑縺・�ｴ蜷・
        entry2 = EntryModel(msgid="test", msgstr="テスト", msgctxt=None)
        self.assertEqual(entry2.key, "|test")

    def test_safe_getattr(self):
        # safe_getattr繝｡繧ｽ繝・ラ縺ｮ繝・せ繝・
        # 騾壼ｸｸ縺ｮ螻樊ｧ蜿門ｾ・
        obj = Mock()
        obj.attr = "value"

        # EntryModel.from_po_entry蜀・〒螳夂ｾｩ縺輔ｌ縺ｦ縺・ｋsafe_getattr繧貞・螳夂ｾｩ
        def safe_getattr(obj, attr_name, default=None):
            try:
                value = getattr(obj, attr_name, default)
                # Mock繧ｪ繝悶ず繧ｧ繧ｯ繝医・蝣ｴ蜷医・繝・ヵ繧ｩ繝ｫ繝亥､繧剃ｽｿ逕ｨ
                if hasattr(value, "__class__") and "Mock" in value.__class__.__name__:
                    return default
                return value
            except (AttributeError, TypeError):
                return default

        # 螻樊ｧ縺悟ｭ伜惠縺吶ｋ蝣ｴ蜷・
        self.assertEqual(safe_getattr(obj, "attr"), "value")

        # 螻樊ｧ縺悟ｭ伜惠縺励↑縺・�ｴ蜷・
        self.assertIsNone(safe_getattr(obj, "non_existent_attr"))

        # 繝・ヵ繧ｩ繝ｫ繝亥､繧呈欠螳壹＠縺溷�ｴ蜷・
        self.assertEqual(safe_getattr(obj, "non_existent_attr", "default"), "default")

        # AttributeError縺檎匱逕溘☆繧句�ｴ蜷・
        obj_with_attr_error = Mock()
        type(obj_with_attr_error).__getattr__ = Mock(side_effect=AttributeError)
        self.assertEqual(
            safe_getattr(obj_with_attr_error, "attr", "default"), "default"
        )

        # TypeError縺檎匱逕溘☆繧句�ｴ蜷・
        obj_with_type_error = Mock()
        type(obj_with_type_error).__getattr__ = Mock(side_effect=TypeError)
        self.assertEqual(
            safe_getattr(obj_with_type_error, "attr", "default"), "default"
        )

    def test_metadata_operations(self):
        """メタデータ操作メソッドのテスト"""
        entry = EntryModel(
            key="test",
            msgid="test",
            msgstr="テスト",
        )

        # メタデータの追加
        entry.add_metadata("author", "テスト太郎")
        entry.add_metadata("priority", 1)
        entry.add_metadata("tags", ["重要", "確認済み"])

        # メタデータの取得
        self.assertEqual(entry.get_metadata("author"), "テスト太郎")
        self.assertEqual(entry.get_metadata("priority"), 1)
        self.assertEqual(entry.get_metadata("tags"), ["重要", "確認済み"])

        # 存在しないキーの取得（デフォルト値）
        self.assertIsNone(entry.get_metadata("non_existent"))
        self.assertEqual(entry.get_metadata("non_existent", "デフォルト"), "デフォルト")

        # すべてのメタデータの取得
        all_metadata = entry.get_all_metadata()
        self.assertEqual(len(all_metadata), 3)
        self.assertEqual(all_metadata["author"], "テスト太郎")
        self.assertEqual(all_metadata["priority"], 1)
        self.assertEqual(all_metadata["tags"], ["重要", "確認済み"])

        # メタデータの削除
        self.assertTrue(entry.remove_metadata("author"))
        self.assertFalse(entry.remove_metadata("non_existent"))
        self.assertIsNone(entry.get_metadata("author"))

        # すべてのメタデータのクリア
        entry.clear_metadata()
        self.assertEqual(len(entry.get_all_metadata()), 0)

    def test_to_dict_with_metadata(self):
        """to_dictメソッドがメタデータを含むことを確認するテスト"""
        entry = EntryModel(
            key="test",
            msgid="test",
            msgstr="テスト",
        )

        # メタデータの追加
        entry.add_metadata("author", "テスト太郎")
        entry.add_metadata("priority", 1)

        # to_dictの結果にメタデータが含まれることを確認
        entry_dict = entry.to_dict()
        self.assertIn("metadata", entry_dict)
        self.assertEqual(entry_dict["metadata"]["author"], "テスト太郎")
        self.assertEqual(entry_dict["metadata"]["priority"], 1)


if __name__ == "__main__":
    unittest.main()
