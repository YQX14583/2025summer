#pragma once

#include "list.h"

// 数独元素坐标
typedef struct
{
    int row;
    int col;
} Coordinate;

// 获取宫格的坐标列表
PtrList* get_box(int r, int c);
// 逐行读取文件
PtrList* read_lines(const char* filename);
// 追加Coordinate元素
void append_coordiante(PtrList* coordinates, int row, int col);
// 获取数独矩阵中的整数
bool sudoku_get_int(PtrList* sudoku, int i, int j, int* ret);
// 设置数独矩阵中的整数
bool sudoku_set_int(PtrList* sudoku, int i, int j, int value);