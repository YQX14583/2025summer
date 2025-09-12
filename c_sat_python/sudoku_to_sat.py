from create_sudoku import *


def create_cnf(filename):
    with open(filename, "r", encoding="utf-8") as f:
        lines = f.readlines()

    n = 0
    line_n = lines[n]
    list_cnf = []

    ranges = rows + cols + boxes + pcf_boxes + cross_line  # ranges: list[list[tuple[int, int]]]
    for rng in ranges:  # rng: list[tuple[int, int]]
        # 每个格子可以是1到9
        for x_y in rng:
            x=x_y[0]
            y=x_y[1]
            temp=[]
            for v in range(1,10):
                temp.append(x * 100 + y * 10 + v)
            list_cnf.append(temp)


        # 1到9只能出现1次
        for v in range(1, 10):
            for i in range(9):
                for j in range(i + 1, 9):
                    (r1, c1), (r2, c2) = rng[i], rng[j]
                    list_cnf.append([-r1 * 100 - c1 * 10 - v, -r2 * 100 - c2 * 10 - v])

    # 读入已有的数字
    cur_numbers = []
    for i in range(9):
        for j in range(9):
            c = line_n[9 * i + j]
            if c != '.':
                cur_numbers.append([i, j, int(c)])

    # 已填入的数字转为cnf
    for x, y, v in cur_numbers:
        list_cnf.append([100 * (x + 1) + 10 * (y + 1) + v])

    # 文字去重，存入literals中
    literals = []
    for cnf in list_cnf:
        for v in cnf:
            abs_v = abs(v)
            if abs_v not in literals:
                literals.append(abs_v)

    # 语句去重，存入sorted_clauses中
    temp_clauses = []
    for clause in list_cnf:
        sorted_clause = sorted(clause)
        if sorted_clause not in temp_clauses:
            temp_clauses.append(sorted_clause)

    # 生成cnf文件
    fout = open("my_sudoku.cnf", "wt")
    fout.write("c sudoku output\n")
    fout.write(f"p cnf {len(literals)} {len(temp_clauses)}\n")
    for clause in temp_clauses:
        for l in clause:
            print(l, end=' ', file=fout)
        print(0, file=fout)

    fout.close()
