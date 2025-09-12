import copy
import logging
import random

# 目标生成一个百分号数独，打印出来并生成数独文件

def get_box(r:int, c:int):
    ret = []
    for i in range(r, r + 3):  # for(int i=r;i<r+3;i++)
        for j in range(c, c + 3):
            ret.append((i, j))

    return ret


rows = []
for c in range(1, 10):
    s_rows=[]
    for r in range(1, 10):
        s_rows.append((r,c))
    rows.append(s_rows)
cols = []
for r in range(1, 10):
    s_cols=[]
    for c in range(1, 10):
        s_cols.append((r, c))
    cols.append(s_cols)
boxes = []
for r in [1, 4, 7]:
    for c in [1, 4, 7]:
        boxes.append(get_box(r, c))
pcf_boxes = [get_box(2, 2), get_box(6, 6)]
pcf_centers = [(3, 3), (7, 7)]
cross_line = []
s_cross_line = []
for r in range(1, 10):
    s_cross_line.append((r, 10 - r))
cross_line.append(s_cross_line)


# 打印棋盘
def print_board(sudoku: list[list[int]]):
    print("=" * 21)
    for i in range(9):
        if i % 3 == 0 and i != 0:
            print("---------------------")
        for j in range(9):
            if j % 3 == 0 and j != 0:
                print("| ", end="")
            if j == 8:
                if sudoku[i][j] == 0:
                    print(".")
                else:
                    print(sudoku[i][j])
            else:
                if sudoku[i][j] == 0:
                    print(".",end=" ")
                else:
                    print(sudoku[i][j],end=" ")

    print("=" * 21)


# 判断（row,col)处的数字是否有效,对应矩阵位置sudoku[row-1][col-1]
def is_valid(sudoku: list[list[int]], row, col, value):
    # 检查行约束
    for i in range(9):
        if sudoku[row - 1][i] == value:
            return False

    # 检查列约束
    for j in range(9):
        if sudoku[j][col - 1] == value:
            return False

    # 检查九宫格约束
    x, y = 3 * ((row - 1) // 3), 3 * ((col - 1) // 3)
    for i in range(3):
        for j in range(3):
            if sudoku[x + i][y + j] == value:
                return False

    # 检查百分号约束
    for center_r, center_c in pcf_centers:
        if abs(row - center_r) <= 1 and abs(col - center_c) <= 1:
            for i in range(center_r - 1, center_r + 2):
                for j in range(center_c - 1, center_c + 2):
                    if sudoku[i - 1][j - 1] == value:
                        return False

    # 检查对角线约束
    if row + col == 10:  # 副对角线
        for i in range(9):
            if sudoku[i][8 - i] == value:
                return False

    return True


# 回溯法解数独
def solve_sudoku(sudoku: list[list[int]]) -> bool:
    for row in range(1, 10):
        for col in range(1, 10):
            if sudoku[row - 1][col - 1] == 0:
                numbers = list(range(1, 10))
                random.shuffle(numbers)
                for value in numbers:  # 随机尝试数字
                    if is_valid(sudoku, row, col, value):  # 满足约束
                        sudoku[row - 1][col - 1] = value
                        if solve_sudoku(sudoku):  # 若合法，递归处理填好该格子后的数独
                            return True  # 递归返回真，找到解，直接返回
                        else:
                            sudoku[row - 1][col - 1] = 0  # 无解，重置当前格子为0，尝试下一个数字
                return False
    return True


# 生成一个完整数独
def complete_sudoku() -> list[list[int]]:
    sudoku = [[0] * 9 for i in range(9)]
    solve_sudoku(sudoku)
    return sudoku


# 挖洞
def dig_holes(sudoku: list[list[int]], holes):
    cells = []
    for i in range(9):
        for j in range(9):
            cells.append((i,j))
    random.shuffle(cells)
    for i in range(holes):
        row = cells[i][0]
        col = cells[i][1]
        sudoku[row][col] = 0


# 生成挖洞后的数独
def create_puzzle():
    my_sudoku = complete_sudoku()
    holes_num = random.randint(30, 50)
    dig_holes(my_sudoku, holes_num)
    print("Randomly initialize the Sudoku game layout:")
    print_board(my_sudoku)
    return my_sudoku


# 生成数独文件
def create_sudoku_txt(my_sudoku):
    sudoku_list = []
    for row in my_sudoku:
        for num in row:
            sudoku_list.append('.' if num == 0 else str(num))
    result = ''.join(sudoku_list)
    fout = open("my_sudoku.txt", "wt")
    fout.write(result)
    fout.close()
