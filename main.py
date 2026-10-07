#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import csv
import datetime
import io
import os
import re
from collections import Counter

FIELDS = ["姓名", "学号", "邮箱", "志愿1", "志愿2", "推荐人"]
REQUIRED = ["姓名", "学号", "邮箱", "志愿1"]
HARD_KINDS = {"列数不足", "学号非纯数字", "邮箱不匹配"}
DEFAULT_INPUT = "data/raw/recruit_raw.csv"
EMAIL_DOMAIN = "smbu.edu.cn"


def col_index(header):
    for name in FIELDS:
        if name not in header:
            raise SystemExit("报名表里找不到「%s」这一列，确认一下选的文件对不对" % name)
    return {name: header.index(name) for name in FIELDS}


def read_rows(path):
    text = None
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            with open(path, newline="", encoding=encoding) as f:
                text = f.read()
            break
        except UnicodeDecodeError:
            continue
        except OSError as e:
            raise SystemExit("打不开 %s：%s" % (path, e))

    if text is None:
        raise SystemExit("读不了 %s：既不是 utf-8 也不是 GBK" % path)

    reader = csv.reader(io.StringIO(text, newline=""))
    header = next(reader, None)
    rows = [row for row in reader if row]
    return header, rows


def is_blank(value):
    return value.strip() == ""


def cell(row, i):
    return row[i] if i < len(row) else ""


def scan(rows, header):
    blanks = {}
    for col, name in enumerate(header):
        blanks[name] = sum(1 for row in rows
                           if col < len(row) and is_blank(row[col]))

    groups = {}
    for offset, row in enumerate(rows):
        groups.setdefault(tuple(row), []).append(offset + 2)

    same = [lines for lines in groups.values() if len(lines) > 1]
    return blanks, same


def cmd_overview(args):
    header, rows = read_rows(args.input)
    idx = col_index(header)
    blanks, same = scan(rows, header)

    print("文件：%s" % args.input)
    print("总行数：%d（不含表头）" % len(rows))
    print()

    print("各列空值：")
    for name, n in blanks.items():
        print("  %s: %d" % (name, n))
    print()

    if not same:
        print("完全重复的行：没有")
    else:
        print("完全重复的行：%d 组" % len(same))
        for lines in same:
            where = "、".join("第 %d 行" % n for n in lines)
            name = cell(rows[lines[0] - 2], idx["姓名"])
            print("  %s 一模一样（%s）" % (where, name))


def validate(rows, idx):
    seen = {}
    for offset, row in enumerate(rows):
        sid = cell(row, idx["学号"]).strip()
        if sid:
            seen.setdefault(sid, []).append(
                (offset + 2, cell(row, idx["姓名"]).strip()))

    problems = []
    for offset, row in enumerate(rows):
        lineno = offset + 2
        sid = cell(row, idx["学号"]).strip()
        email = cell(row, idx["邮箱"]).strip()
        hit = []

        missing = [name for name in REQUIRED if len(row) <= idx[name]]
        if missing:
            hit.append(("列数不足",
                        "这行只有 %d 列，缺了「%s」，可能是漏填或者少打了个逗号"
                        % (len(row), "、".join(missing))))
        else:
            if not re.fullmatch(r"[0-9]+", sid):
                hit.append(("学号非纯数字",
                            "学号「%s」不是纯数字" % cell(row, idx["学号"])))

            if email != sid + "@" + EMAIL_DOMAIN:
                hit.append(("邮箱不匹配",
                            "邮箱应为 %s@%s，实际填的是「%s」"
                            % (sid, EMAIL_DOMAIN, cell(row, idx["邮箱"]))))

            group = seen.get(sid, [])
            lines = [n for n, _ in group]
            if len(group) > 1:
                if len({name for _, name in group}) == 1:
                    if lineno == lines[0]:
                        hit.append(("重复报名",
                                    "学号 %s 一共出现 %d 次（第 %s 行），本行保留"
                                    % (sid, len(lines),
                                       "、".join(str(n) for n in lines[1:]))))
                    else:
                        hit.append(("重复报名",
                                    "学号 %s 在第 %d 行已经报过，重复提交"
                                    % (sid, lines[0])))
                elif lineno == lines[0]:
                    others = "、".join("第 %d 行（%s）" % (n, name)
                                       for n, name in group[1:])
                    hit.append(("学号疑似填错",
                                "学号 %s 还出现在 %s，姓名对不上，本行保留，"
                                "建议人工核对" % (sid, others)))
                else:
                    hit.append(("学号疑似填错",
                                "学号 %s 在第 %d 行出现过，那边姓名是「%s」，"
                                "两行姓名对不上，可能是学号填错"
                                % (sid, lines[0], group[0][1])))

        if hit:
            problems.append((lineno, row, hit))

    return problems


def clean(rows, idx):
    problems = validate(rows, idx)

    spoiled = set()
    for lineno, _, hit in problems:
        if any(kind in HARD_KINDS for kind, _ in hit):
            spoiled.add(lineno)

    good = []
    seen = set()
    for offset, row in enumerate(rows):
        if offset + 2 in spoiled:
            continue
        sid = cell(row, idx["学号"]).strip()
        if sid in seen:
            continue
        seen.add(sid)
        good.append(row)

    return good, problems


def cmd_clean(args):
    header, rows = read_rows(args.input)
    idx = col_index(header)
    _, problems = clean(rows, idx)

    os.makedirs(args.outdir, exist_ok=True)
    out = os.path.join(args.outdir, "problem_list.csv")
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["行号"] + header + ["问题类型", "问题说明"])
        for lineno, row, hit in problems:
            writer.writerow([lineno] + row
                            + ["；".join(k for k, _ in hit),
                               "；".join(why for _, why in hit)])

    print("检查 %d 行，其中 %d 行有问题" % (len(rows), len(problems)))
    print("问题清单已导出 -> %s" % out)
    print()

    kinds = Counter(k for _, _, hit in problems for k, _ in hit)
    print("按类型统计：")
    for kind, n in kinds.most_common():
        print("  %s: %d 行" % (kind, n))


def summarize(good, idx):
    by_first = Counter()
    for row in good:
        by_first[cell(row, idx["志愿1"]).strip() or "(未填)"] += 1

    both = one = none = 0
    for row in good:
        has1 = bool(cell(row, idx["志愿1"]).strip())
        has2 = bool(cell(row, idx["志愿2"]).strip())
        if has1 and has2:
            both += 1
        elif has1 or has2:
            one += 1
        else:
            none += 1

    return by_first, both, one, none


def cmd_stats(args):
    header, rows = read_rows(args.input)
    idx = col_index(header)
    good, _ = clean(rows, idx)

    os.makedirs(args.outdir, exist_ok=True)

    by_first, both, one, none = summarize(good, idx)
    total = len(good)
    summary_path = os.path.join(args.outdir, "first_choice_summary.csv")
    with open(summary_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["志愿1", "人数"])
        for dept, n in by_first.most_common():
            writer.writerow([dept, n])

    print("清洗后 %d 人，按第一志愿分组：" % total)
    for dept, n in by_first.most_common():
        print("  %s: %d 人（%.1f%%）" % (dept, n, 100.0 * n / total))
    print()

    print("志愿填写情况：")
    print("  两个都填了: %d 人" % both)
    print("  只填了一个: %d 人" % one)
    if none:
        print("  两个都没填: %d 人" % none)
    print()

    cleaned_path = os.path.join(args.outdir, "cleaned.csv")
    with open(cleaned_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for row in good:
            writer.writerow([cell.strip() for cell in row])

    print("汇总表 -> %s" % summary_path)
    print("干净数据 -> %s（%d 行）" % (cleaned_path, len(good)))


def cmd_report(args):
    header, rows = read_rows(args.input)
    idx = col_index(header)
    good, problems = clean(rows, idx)
    blanks, same = scan(rows, header)
    by_first, both, one, none = summarize(good, idx)

    kinds = Counter(k for _, _, hit in problems for k, _ in hit)
    hard = [ln for ln, _, hit in problems if any(k in HARD_KINDS for k, _ in hit)]
    dropped = len(rows) - len(good)
    total = len(good)

    out = []
    out.append("# 招新报名数据检查报告")
    out.append("")
    out.append("数据文件：`%s`，生成时间：%s"
               % (args.input, datetime.datetime.now().strftime("%Y-%m-%d %H:%M")))
    out.append("")
    out.append("## 一、概览")
    out.append("")
    out.append("- 报名总行数：%d" % len(rows))
    out.append("- 各列空值：%s"
               % "、".join("%s %d" % (name, n) for name, n in blanks.items()))
    if same:
        detail = "；".join("第 %s 行" % "、".join(str(n) for n in lines)
                          for lines in same)
        out.append("- 完全重复的行：%d 组（%s）" % (len(same), detail))
    else:
        out.append("- 完全重复的行：没有")
    out.append("")
    out.append("## 二、有问题的行")
    out.append("")
    out.append("一共 %d 行有问题：" % len(problems))
    out.append("")
    out.append("| 问题类型 | 行数 |")
    out.append("| --- | --- |")
    for kind, n in kinds.most_common():
        out.append("| %s | %d |" % (kind, n))
    out.append("")
    out.append("明细（最多列 10 条，完整清单见 `output/problem_list.csv`）：")
    out.append("")
    out.append("| 行号 | 姓名 | 学号 | 问题类型 | 问题说明 |")
    out.append("| --- | --- | --- | --- | --- |")
    for lineno, row, hit in problems[:10]:
        out.append("| %d | %s | %s | %s | %s |"
                   % (lineno, cell(row, idx["姓名"]), cell(row, idx["学号"]),
                      "；".join(k for k, _ in hit),
                      "；".join(why for _, why in hit)))
    out.append("")
    out.append("## 三、清洗结果")
    out.append("")
    out.append("%d 行原始数据 → %d 行干净数据，剔掉 %d 行（%d 行是填错或缺列，"
               "另外 %d 行是重复提交，同一学号只留最早报的那份）。"
               % (len(rows), total, dropped, len(hard), dropped - len(hard)))
    out.append("")
    out.append("干净数据见 `output/cleaned.csv`。")
    out.append("")
    out.append("## 四、第一志愿分布")
    out.append("")
    out.append("| 志愿 | 人数 | 占比 |")
    out.append("| --- | --- | --- |")
    for dept, n in by_first.most_common():
        out.append("| %s | %d | %.1f%% |"
                   % (dept, n, 100.0 * n / total if total else 0.0))
    out.append("")
    out.append("志愿填写情况：两个都填了 %d 人，只填了一个 %d 人，两个都没填 %d 人。"
               % (both, one, none))
    out.append("")
    out.append("## 五、判定口径")
    out.append("")
    out.append("- 学号必须是纯数字，位数和前缀不校验")
    out.append("- 邮箱必须等于「学号@smbu.edu.cn」，区分大小写")
    out.append("- 同一学号出现两次以上算重复报名；两行姓名也对不上的，会标成"
               "「学号疑似填错」，多半是学号打错一位，建议人工核对")
    out.append("- 行号是文件里的实际行号（表头算第 1 行），对着 Excel 直接能找到人")
    out.append("")

    os.makedirs(args.outdir, exist_ok=True)
    path = os.path.join(args.outdir, "report.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")

    print("报告已导出 -> %s" % path)


def build_parser():
    parser = argparse.ArgumentParser(
        description="招新报名数据处理小工具")
    sub = parser.add_subparsers(dest="command", required=True)

    overview = sub.add_parser("overview", help="打印数据概览")
    overview.add_argument("-i", "--input", default=DEFAULT_INPUT,
                          help="报名表路径，默认 %s" % DEFAULT_INPUT)
    overview.set_defaults(func=cmd_overview)

    clean_cmd = sub.add_parser("clean", help="校验数据，导出问题清单")
    clean_cmd.add_argument("-i", "--input", default=DEFAULT_INPUT,
                           help="报名表路径，默认 %s" % DEFAULT_INPUT)
    clean_cmd.add_argument("-o", "--outdir", default="output",
                           help="结果输出目录，默认 output")
    clean_cmd.set_defaults(func=cmd_clean)

    stats = sub.add_parser("stats", help="按志愿统计并导出干净数据")
    stats.add_argument("-i", "--input", default=DEFAULT_INPUT,
                       help="报名表路径，默认 %s" % DEFAULT_INPUT)
    stats.add_argument("-o", "--outdir", default="output",
                       help="结果输出目录，默认 output")
    stats.set_defaults(func=cmd_stats)

    report = sub.add_parser("report", help="把整体情况写成一份报告")
    report.add_argument("-i", "--input", default=DEFAULT_INPUT,
                        help="报名表路径，默认 %s" % DEFAULT_INPUT)
    report.add_argument("-o", "--outdir", default="output",
                        help="结果输出目录，默认 output")
    report.set_defaults(func=cmd_report)

    return parser


def main():
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
