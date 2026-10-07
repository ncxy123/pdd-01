#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用法：
    python main.py overview
    python main.py overview -i data/raw/recruit_raw.csv
"""

import argparse
import csv
import os
import re
from collections import Counter

FIELDS = ["姓名", "学号", "邮箱", "志愿1", "志愿2", "推荐人"]
DEFAULT_INPUT = "data/raw/recruit_raw.csv"
EMAIL_DOMAIN = "smbu.edu.cn"


def read_rows(path):
    """读报名表

    :return: 表头, 数据行
    """
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        rows = [row for row in reader if row]   # 末尾的空行不算数据
    return header, rows


def is_blank(value):
    return value.strip() == ""


def cmd_overview(args):
    header, rows = read_rows(args.input)

    print("文件：%s" % args.input)
    print("总行数：%d（不含表头）" % len(rows))
    print()

    print("各列空值：")
    for col, name in enumerate(header):
        blank = sum(1 for row in rows if col < len(row) and is_blank(row[col]))
        print("  %s: %d" % (name, blank))
    print()

    groups = {}
    for offset, row in enumerate(rows):
        groups.setdefault(tuple(row), []).append(offset + 2)

    same = [lines for lines in groups.values() if len(lines) > 1]
    if not same:
        print("完全重复的行：没有")
    else:
        print("完全重复的行：%d 组" % len(same))
        for lines in same:
            where = "、".join("第 %d 行" % n for n in lines)
            print("  %s 一模一样（%s）" % (where, rows[lines[0] - 2][0]))


def validate(rows):
    lines_of = {}
    for offset, row in enumerate(rows):
        lines_of.setdefault(row[1].strip(), []).append(offset + 2)

    problems = []
    for offset, row in enumerate(rows):
        lineno = offset + 2
        sid = row[1].strip()
        email = row[2].strip()
        hit = []

        if not re.fullmatch(r"[0-9]+", sid):
            hit.append(("学号非纯数字", "学号「%s」不是纯数字" % row[1]))

        if email != sid + "@" + EMAIL_DOMAIN:
            hit.append(("邮箱不匹配",
                        "邮箱应为 %s@%s，实际填的是「%s」"
                        % (sid, EMAIL_DOMAIN, row[2])))

        same = lines_of[sid]
        if len(same) > 1:
            if lineno == same[0]:
                hit.append(("重复报名",
                            "学号 %s 一共出现 %d 次（第 %s 行），本行保留"
                            % (sid, len(same),
                               "、".join(str(n) for n in same[1:]))))
            else:
                hit.append(("重复报名",
                            "学号 %s 在第 %d 行已经报过，重复提交"
                            % (sid, same[0])))

        if hit:
            problems.append((lineno, row, hit))

    return problems


def clean(rows):
    problems = validate(rows)

    spoiled = set()
    for lineno, _, hit in problems:
        if any(kind != "重复报名" for kind, _ in hit):
            spoiled.add(lineno)

    good = []
    seen = set()
    for offset, row in enumerate(rows):
        if offset + 2 in spoiled:
            continue
        sid = row[1].strip()
        if sid in seen:
            continue
        seen.add(sid)
        good.append(row)

    return good, problems


def cmd_clean(args):
    header, rows = read_rows(args.input)
    _, problems = clean(rows)

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

    # 按问题类型汇总一下，一行有多个毛病会分别计入
    kinds = Counter(k for _, _, hit in problems for k, _ in hit)
    print("按类型统计：")
    for kind, n in kinds.most_common():
        print("  %s: %d 行" % (kind, n))


def cmd_stats(args):
    header, rows = read_rows(args.input)
    good, _ = clean(rows)

    os.makedirs(args.outdir, exist_ok=True)

    # 第一志愿分组，志愿空着的归到「(未填)」，免得统计里少人
    by_first = Counter()
    for row in good:
        by_first[row[3].strip() or "(未填)"] += 1

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

    both = one = none = 0
    for row in good:
        has1 = bool(row[3].strip())
        has2 = bool(row[4].strip())
        if has1 and has2:
            both += 1
        elif has1 or has2:
            one += 1
        else:
            none += 1

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

    return parser


def main():
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
