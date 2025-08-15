#pragma once

#include "list.h"

void print_board(PtrList* sudoku);

bool is_valid(PtrList* sudoku, int row, int col, int value);

bool solve_sudoku(PtrList* sudoku);

PtrList* complete_sudoku(void);

void dig_holes(PtrList* sudoku, int holes);

PtrList* create_puzzle();

void create_sudoku_txt(PtrList* my_sudoku);
