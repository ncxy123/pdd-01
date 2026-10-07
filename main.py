#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import csv

FIELDS = ["姓名", "学号", "邮箱", "志愿1", "志愿2", "推荐人"]
DEFAULT_INPUT = "data/raw/recruit_raw.csv"


def read_rows(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        rows = [row for row in reader if row]
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


def build_parser():
    parser = argparse.ArgumentParser(
        description="招新报名数据处理小工具")
    sub = parser.add_subparsers(dest="command", required=True)

    overview = sub.add_parser("overview", help="打印数据概览")
    overview.add_argument("-i", "--input", default=DEFAULT_INPUT,
                          help="报名表路径，默认 %s" % DEFAULT_INPUT)
    overview.set_defaults(func=cmd_overview)

    return parser


def main():
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
