#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "sudoku.h"

PtrList* get_box(int r, int c)
{
    PtrList* ret = list_create(9);
    for (int i = r; i < r + 3; i++)
    {
        for (int j = c; j < c + 3; j++)
        {
            Coordinate* coord = malloc(sizeof(Coordinate));
            if (coord)
            {
                coord->row = i;
                coord->col = j;
                list_append(ret, coord);
            }
        }
    }

    return ret;
}

PtrList* read_lines(const char* filename)
{
    FILE* file = fopen(filename, "r");
    if (!file)
    {
        printf("文件打开失败");
        return NULL;
    }

    PtrList* lines = list_create(100);
    if (!lines) return NULL;

    char content[10240];
    while (fgets(content, sizeof(content), file))
    {
        char* line_copy = strdup(content);
        list_append(lines, line_copy);
    }
    if (ferror(file))
    {
        printf("文件读取错误");
        list_destroy(lines, free);
        lines = NULL;
    }
    fclose(file);
    return lines;
}

//使用后要list_destroy(lines,free)


void append_coordiante(PtrList* coordinates, int row, int col)
{
    if (!coordinates) return;
    Coordinate* c = malloc(sizeof(Coordinate));
    if (!c) return;
    c->row = row;
    c->col = col;
    list_append(coordinates, c);
}


//获取数独矩阵中的元素
bool sudoku_get_int(PtrList* sudoku, int i, int j, int* ret)
{
    if (!sudoku || i < 0 || i >= sudoku->size || j < 0 || j >= sudoku->size)
        return false;
    if (ret)
    {
        PtrList* temp;
        list_get(sudoku, i, &temp);
        list_get_int(temp, j, ret);
        return true;
    }
    return false;
}


//给数独矩阵赋值
bool sudoku_set_int(PtrList* sudoku, int i, int j, int value)
{
    if (!sudoku || i < 0 || i >= sudoku->size || j < 0 || j >= sudoku->size)
        return false;
    PtrList* row;
    if (!list_get(sudoku, i, &row))
        return false;
    return list_set_int(row, j, value);
}
