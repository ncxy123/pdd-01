# -*- coding: utf-8 -*-

import csv
import os
import random

random.seed(20261004)

FIELDS = ["姓名", "学号", "邮箱", "志愿1", "志愿2", "推荐人"]

SURNAME = "王李张刘陈杨黄赵吴周徐孙马朱胡林郭何高罗郑梁谢宋唐许韩冯邓曹彭曾肖田董潘袁蔡蒋余杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾夏韦付方白邹孟熊秦邱"
GIVEN = "伟芳娜敏静丽强磊军洋勇艳杰娟涛明超霞平刚英华丽玉兰春小林鑫佳怡然宇轩泽睿琪欣雨涵博文远宁康笑晨阳雪菲子思"

DEPT = ["机械组", "电控组", "视觉组", "算法组", "运营组", "宣传组", "硬件组"]

BASE_ROWS = 280


def random_name():
    name = random.choice(SURNAME)
    for _ in range(random.randint(1, 2)):
        name += random.choice(GIVEN)
    return name


def student_id(year_digit, seq):
    return "11202%s%04d" % (year_digit, seq)


def dirty_id(sid):
    return random.choice([
        sid.replace(sid[5], "O", 1),
        sid[:6] + "a" + sid[7:],
        sid + "x",
        sid[:5] + "-" + sid[5:],
        sid[:6] + " " + sid[6:],
    ])


def dirty_email(sid):
    return random.choice([
        sid + "@qq.com",
        sid + "@163.com",
        sid + "@smbu.edu.com",
        sid + "@smbu.cn",
        sid + "@SMbU.edu.cn",
        sid[:-1] + "@smbu.edu.cn",
    ])


def build_row(seq):
    year = 6 if random.random() < 0.85 else 5
    sid = student_id(year, seq)

    if random.random() < 0.03:
        sid = dirty_id(sid)
        email = sid + "@smbu.edu.cn"
    else:
        email = sid + "@smbu.edu.cn"
        if random.random() < 0.04:
            email = dirty_email(sid)

    name = random_name()
    if random.random() < 0.02:
        name = " " + name + " "

    zs1 = random.choice(DEPT)
    zs2 = ""
    if random.random() < 0.55:
        zs2 = random.choice([d for d in DEPT if d != zs1])
    ref = random_name() if random.random() < 0.4 else ""

    return [name, sid, email, zs1, zs2, ref]


def main():
    rows = [build_row(i + 1) for i in range(BASE_ROWS)]

    for row in random.sample(rows, 10):
        again = list(row)
        other = [d for d in DEPT if d != again[3]]
        again[4] = random.choice(other)
        again[5] = again[5] or random_name()
        rows.append(again)

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
