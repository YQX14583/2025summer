#pragma once
#ifdef __cplusplus
extern "C" {
#endif

// 打印数独棋盘
void print_board(PtrList* sudoku);
// 判断（row,col)处的数字是否有效
bool is_valid(PtrList* sudoku, int row, int col, int value);
// 回溯法解数独
bool solve_sudoku(PtrList* sudoku);
// 生成一个完整数独
PtrList* complete_sudoku(void);
// 挖洞
void dig_holes(PtrList* sudoku, int holes);
// 生成挖洞后的数独
PtrList* create_puzzle();
// 生成数独文件
void create_sudoku_txt(PtrList* my_sudoku);

#ifdef __cplusplus
}
#endif