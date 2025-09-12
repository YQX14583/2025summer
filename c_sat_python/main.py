import logging

import read_cnf
import dpll
import create_sudoku
import sudoku_to_sat
import time

logging.basicConfig(level=logging.INFO)

print("Welcome!")
while True:
    print("\nSAT -- 1, %-Sudoku -- 2, exit -- 0")
    op = input("Please choose a number: ")
    if op == "1":
        filename = input("Please input a filename: ")
        cnf_clauses = read_cnf.read_file(filename)
        start_time = time.time()  # 记录开始时间
        result = dpll.dpll_reduce([], cnf_clauses)
        end_time = time.time()  # 记录结束时间l
        elapsed = end_time - start_time  # 计算耗时
        if result is not None:
            print("The solution is: ", sorted(result, key=abs))
        else:
            print("No solution found!")
        print(f"(time cost: {elapsed:.4f}s)")

    elif op == "2":
        # 随机初始化数独游戏格局
        start_time = time.time()
        my_sudoku = create_sudoku.create_puzzle()
        end_time = time.time()
        elapsed = end_time - start_time
        print(f"(time cost: {elapsed:.4f}s)")

        # 将数独转化为sat并写入cnf文件
        create_sudoku.create_sudoku_txt(my_sudoku)
        filename = "my_sudoku.txt"
        sudoku_to_sat.create_cnf(filename)
        print("sudoku has been written in: my_sudoku.cnf")

        # 输出结果
        filename = "my_sudoku.cnf"
        cnf_clauses = read_cnf.read_file(filename)
        start_time = time.time()  # 记录开始时间
        result = dpll.dpll_reduce([], cnf_clauses)
        end_time = time.time()  # 记录结束时间
        elapsed = end_time - start_time  # 计算耗时
        if result is not None:
            result = sorted(result, key=abs)
            new_result = [x for x in result if x >= 0]
            print("The solution is: ", new_result)

            # 输出数独的解
            matrix = [[0] * 9 for _ in range(9)]
            for num in new_result:
                row = num // 100 - 1
                col = (num // 10) % 10 - 1
                value = num % 10

                # 检查行列是否有效
                if 0 <= row < 9 and 0 <= col < 9:
                    matrix[row][col] = value

            create_sudoku.print_board(matrix)
        else:
            print("No solution found!")

        print(f"(time cost: {elapsed:.4f}s)")

    elif op == "0":
        print("Thank you!")
        break

    else:
        print("Invalid input!")
