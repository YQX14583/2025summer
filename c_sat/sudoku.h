#pragma once

#include "list.h"

typedef struct
{
    int row;
    int col;
} Coordinate;

//DeclareList(SudokuRow, int)
//DeclareList(Sudoku, SudokuRow*)

PtrList* get_box(int r, int c);

PtrList* read_lines(const char* filename);

void append_coordiante(PtrList* coordinates, int row, int col);

bool sudoku_get_int(PtrList* sudoku, int i, int j, int* ret);

bool sudoku_set_int(PtrList* sudoku, int i, int j, int value);
