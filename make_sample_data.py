# -*- coding: utf-8 -*-
"""造一份模拟的招新报名数据，用来测试清洗脚本。

真实报名表是问卷导出的，里面什么错都有：学号手滑打错、邮箱留了自己
常用的 QQ 邮箱、同一个人提交了两遍、整行复制粘贴等等。这里就照着这些
错来造，保证清洗脚本的每条规则都有对应的数据能验证。

直接 `python make_sample_data.py` 重新生成 data/raw/recruit_raw.csv。
随机种子是固定的，所以每次生成的结果完全一样，方便对照。
"""

import csv
import os
import random

random.seed(20261004)

FIELDS = ["姓名", "学号", "邮箱", "志愿1", "志愿2", "推荐人"]

SURNAME = "王李张刘陈杨黄赵吴周徐孙马朱胡林郭何高罗郑梁谢宋唐许韩冯邓曹彭曾肖田董潘袁蔡蒋余杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾夏韦付方白邹孟熊秦邱"
GIVEN = "伟芳娜敏静丽强磊军洋勇艳杰娟涛明超霞平刚英华丽玉兰春小林鑫佳怡然宇轩泽睿琪欣雨涵博文远宁康笑晨阳雪菲子思"

# 社团下设的几个方向，用来填志愿
DEPT = ["机械组", "电控组", "视觉组", "算法组", "运营组", "宣传组", "硬件组"]

BASE_ROWS = 280  # 先造这么多条，之后再往里掺重复提交


def random_name():
    name = random.choice(SURNAME)
    for _ in range(random.randint(1, 2)):
        name += random.choice(GIVEN)
    return name


def student_id(year_digit, seq):
    """11202 + 入学年份末位 + 4 位序号，凑够 10 位。

    比如 2026 级第 1 号 -> 1120260001
    """
    return "11202%s%04d" % (year_digit, seq)


def dirty_id(sid):
    """几种常见的学号手滑写法。"""
    return random.choice([
        sid.replace(sid[5], "O", 1),        # 数字打成了字母 O
        sid[:6] + "a" + sid[7:],            # 中间混进个 a
        sid + "x",                          # 后面多敲了一个字符
        sid[:5] + "-" + sid[5:],            # 多打了个横杠
        sid[:6] + " " + sid[6:],            # 中间带了空格
    ])


def dirty_email(sid):
    """邮箱填错的情况。"""
    return random.choice([
        sid + "@qq.com",                    # 留了自己常用的邮箱
        sid + "@163.com",
        sid + "@smbu.edu.com",              # 域名多打了个 .edu
        sid + "@smbu.cn",                   # 域名写短了
        sid + "@SMbU.edu.cn",               # 大小写没对上
        sid[:-1] + "@smbu.edu.cn",          # 学号少写一位
    ])


def build_row(seq):
    year = 6 if random.random() < 0.85 else 5   # 以 2026 级新生为主
    sid = student_id(year, seq)

    if random.random() < 0.03:
        sid = dirty_id(sid)
        email = sid + "@smbu.edu.cn"            # 邮箱是照学号复制的，一起错
    else:
        email = sid + "@smbu.edu.cn"
        if random.random() < 0.04:
            email = dirty_email(sid)

    name = random_name()
    if random.random() < 0.02:
        name = " " + name + " "                 # 问卷里手抖带上的空格

    zs1 = random.choice(DEPT)
    zs2 = ""
    if random.random() < 0.55:
        zs2 = random.choice([d for d in DEPT if d != zs1])
    ref = random_name() if random.random() < 0.4 else ""

    return [name, sid, email, zs1, zs2, ref]


def main():
    rows = [build_row(i + 1) for i in range(BASE_ROWS)]

    # 同一个学号又报了一次（改了志愿，人是同一个人）
    for row in random.sample(rows, 10):
        again = list(row)
        other = [d for d in DEPT if d != again[3]]
        again[4] = random.choice(other)
        again[5] = again[5] or random_name()
        rows.append(again)

    # 有些人是直接复制上一行改名字，结果整行原封不动交上来了
    for row in random.sample(rows[:BASE_ROWS], 3):
        rows.append(list(row))

    random.shuffle(rows)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "data", "raw", "recruit_raw.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(FIELDS)
        writer.writerows(rows)

    print("已生成 %d 行 -> %s" % (len(rows), out))


if __name__ == "__main__":
    main()
