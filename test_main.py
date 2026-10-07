# -*- coding: utf-8 -*-

import argparse
import contextlib
import csv
import io
import os
import shutil
import tempfile
import unittest

import main

HEADER = ["姓名", "学号", "邮箱", "志愿1", "志愿2", "推荐人"]
IDX = {name: i for i, name in enumerate(HEADER)}


def row(name, sid, email=None, first="宣传组", second="", ref=""):
    if email is None:
        email = sid + "@smbu.edu.cn"
    return [name, sid, email, first, second, ref]


class TempFileTest(unittest.TestCase):

    def write_csv(self, text, encoding="utf-8-sig"):
        fd, path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        with open(path, "w", newline="", encoding=encoding) as f:
            f.write(text)
        self.addCleanup(os.remove, path)
        return path


class ReadRowsTest(TempFileTest):
    def test_bom_is_eaten(self):
        path = self.write_csv("姓名,学号\n张三,1120260001\n")
        header, rows = main.read_rows(path)
        self.assertEqual(header, ["姓名", "学号"])
        self.assertEqual(rows, [["张三", "1120260001"]])

    def test_gbk_file_also_reads(self):
        path = self.write_csv("姓名,学号\n张三,1120260001\n", encoding="gb18030")
        header, rows = main.read_rows(path)
        self.assertEqual(header[0], "姓名")
        self.assertEqual(rows[0][0], "张三")

    def test_blank_lines_are_not_rows(self):
        path = self.write_csv("姓名,学号\n张三,1120260001\n\n\n")
        _, rows = main.read_rows(path)
        self.assertEqual(len(rows), 1)

    def test_missing_file_exits_with_message(self):
        with self.assertRaises(SystemExit):
            main.read_rows("这个文件不存在.csv")


class ColIndexTest(unittest.TestCase):
    def test_works_when_columns_are_reordered(self):
        idx = main.col_index(["推荐人", "姓名", "学号", "邮箱", "志愿2", "志愿1"])
        self.assertEqual(idx["姓名"], 1)
        self.assertEqual(idx["志愿1"], 5)

    def test_exits_when_column_missing(self):
        with self.assertRaises(SystemExit):
            main.col_index(["姓名", "学号", "邮箱", "志愿1", "志愿2"])


class ValidateTest(unittest.TestCase):
    def kinds(self, rows):
        return {ln: [k for k, _ in hit] for ln, _, hit in main.validate(rows, IDX)}

    def test_clean_rows_have_no_problem(self):
        rows = [row("张三", "1120260001"), row("李四", "1120260002")]
        self.assertEqual(self.kinds(rows), {})

    def test_sid_must_be_digits(self):
        self.assertIn("学号非纯数字", self.kinds([row("张三", "112026 0001")])[2])

    def test_email_must_match_sid(self):
        rows = [row("张三", "1120260001", email="zhangsan@qq.com")]
        self.assertIn("邮箱不匹配", self.kinds(rows)[2])

    def test_email_compare_is_case_sensitive(self):
        rows = [row("张三", "1120260001", email="1120260001@SMBU.edu.cn")]
        self.assertIn("邮箱不匹配", self.kinds(rows)[2])

    def test_duplicate_with_same_name(self):
        rows = [row("张三", "1120260001"), row("张三", "1120260001")]
        self.assertEqual(self.kinds(rows), {2: ["重复报名"], 3: ["重复报名"]})

    def test_duplicate_with_different_name(self):
        rows = [row("张三", "1120260001"), row("李四", "1120260001")]
        self.assertEqual(self.kinds(rows),
                         {2: ["学号疑似填错"], 3: ["学号疑似填错"]})

    def test_short_row_reported_instead_of_crashing(self):
        rows = [row("张三", "1120260001")[:3]]
        self.assertEqual(self.kinds(rows), {2: ["列数不足"]})

    def test_missing_optional_column_is_not_a_problem(self):
        rows = [row("张三", "1120260001")[:5]]
        self.assertEqual(self.kinds(rows), {})

    def test_blank_sid_does_not_count_as_duplicate(self):
        rows = [["张三", "", "", "宣传组"], ["李四", "", "", "算法组"]]
        self.assertNotIn("重复报名", self.kinds(rows)[2])


class CleanTest(unittest.TestCase):
    def test_wrong_first_submission_does_not_lose_the_person(self):
        rows = [row("张三", "1120260001", email="zhangsan@qq.com"),
                row("张三", "1120260001")]
        good, _ = main.clean(rows, IDX)
        self.assertEqual(len(good), 1)
        self.assertEqual(good[0][2], "1120260001@smbu.edu.cn")

    def test_keeps_the_earliest_duplicate(self):
        rows = [row("张三", "1120260001", first="宣传组"),
                row("张三", "1120260001", first="算法组")]
        good, _ = main.clean(rows, IDX)
        self.assertEqual([r[3] for r in good], ["宣传组"])

    def test_result_is_actually_clean(self):
        rows = [row("张三", "1120260001"),
                row("张三", "1120260001"),
                row("李四", "1120260002", email="lisi@qq.com")]
        good, _ = main.clean(rows, IDX)
        sids = [r[1] for r in good]
        self.assertEqual(len(sids), len(set(sids)))
        self.assertTrue(all(r[2] == r[1] + "@smbu.edu.cn" for r in good))


class SummarizeTest(unittest.TestCase):
    def test_first_choice_and_how_many_wishes_filled(self):
        good = [row("张三", "1120260001", first="宣传组", second="算法组"),
                row("李四", "1120260002", first="宣传组"),
                row("王五", "1120260003", first="", second="视觉组")]
        by_first, both, one, none = main.summarize(good, IDX)
        self.assertEqual(by_first["宣传组"], 2)
        self.assertEqual(by_first["(未填)"], 1)
        self.assertEqual((both, one, none), (1, 2, 0))


class CommandTest(TempFileTest):

    def setUp(self):
        self.outdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.outdir)
        self.path = self.write_csv(
            "姓名,学号,邮箱,志愿1,志愿2,推荐人\n"
            "张三,1120260001,1120260001@smbu.edu.cn,宣传组,算法组,\n"
            "张三,1120260001,1120260001@smbu.edu.cn,宣传组,算法组,\n"
            "李四,1120260002,lisi@qq.com,视觉组,,\n")

    def run_cmd(self, name):
        args = argparse.Namespace(input=self.path, outdir=self.outdir)
        with contextlib.redirect_stdout(io.StringIO()):
            getattr(main, "cmd_" + name)(args)

    def test_all_commands_run_and_write_files(self):
        for name in ("overview", "clean", "stats", "report"):
            self.run_cmd(name)
        for name in ("problem_list.csv", "first_choice_summary.csv",
                     "cleaned.csv", "report.md"):
            self.assertTrue(os.path.exists(os.path.join(self.outdir, name)), name)

    def test_problem_list_explains_every_row(self):
        self.run_cmd("clean")
        with open(os.path.join(self.outdir, "problem_list.csv"),
                  encoding="utf-8-sig") as f:
            data = list(csv.reader(f))
        self.assertEqual(data[0][0], "行号")
        self.assertEqual(data[0][-2:], ["问题类型", "问题说明"])
        self.assertEqual(len(data) - 1, 3)
        self.assertTrue(all(r[-1].strip() for r in data[1:]))

    def test_original_file_is_not_touched(self):
        with open(self.path, encoding="utf-8-sig") as f:
            before = f.read()
        for name in ("overview", "clean", "stats", "report"):
            self.run_cmd(name)
        with open(self.path, encoding="utf-8-sig") as f:
            self.assertEqual(f.read(), before)

    def test_repo_sample_data_clean_up_properly(self):
        if not os.path.exists(main.DEFAULT_INPUT):
            self.skipTest("没有样例数据")
        header, rows = main.read_rows(main.DEFAULT_INPUT)
        idx = main.col_index(header)
        good, _ = main.clean(rows, idx)

        sids = [r[idx["学号"]] for r in good]
        self.assertTrue(good)
        self.assertEqual(len(sids), len(set(sids)))
        self.assertTrue(all(r[idx["邮箱"]] == r[idx["学号"]] + "@smbu.edu.cn"
                            for r in good))


if __name__ == "__main__":
    unittest.main()
