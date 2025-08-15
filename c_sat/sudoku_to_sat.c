#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <math.h>

#include "dpll.h"
#include "sudoku.h"
#include "sudoku_to_sat.h"

PtrList* rows = NULL;
PtrList* cols = NULL;
PtrList* boxes = NULL;
PtrList* pcf_centers = NULL;
PtrList* pcf_boxes = NULL;
PtrList* cross_line = NULL;


//初始化数独结构
void init_sudoku_structures()
{
    rows = list_create(9);
    for (int i = 1; i < 10; i++)
    {
        PtrList* s_rows = list_create(9);
        for (int j = 1; j < 10; j++)
            append_coordiante(s_rows, j, i);
        list_append(rows, s_rows);
    }

    cols = list_create(9);
    for (int i = 1; i < 10; i++)
    {
        PtrList* s_cols = list_create(9);
        for (int j = 1; j < 10; j++)
            append_coordiante(s_cols, i, j);
        list_append(cols, s_cols);
    }

    boxes = list_create(9);
    int box_rows[] = {1, 4, 7};
    int box_cols[] = {1, 4, 7};
    for (int i = 0; i < 3; i++)
    {
        for (int j = 0; j < 3; j++)
        {
            PtrList* box = get_box(box_rows[i], box_cols[j]);
            list_append(boxes, box);
        }
    }

    pcf_boxes = list_create(2);
    list_append(pcf_boxes, get_box(2, 2));
    list_append(pcf_boxes, get_box(6, 6));

    pcf_centers = list_create(2);
    append_coordiante(pcf_centers, 3, 3);
    append_coordiante(pcf_centers, 7, 7);

    cross_line = list_create(1);
    PtrList* s_cross_line = list_create(9);
    for (int r = 1; r <= 9; r++)
        append_coordiante(s_cross_line, r, 10 - r);
    list_append(cross_line, s_cross_line);
}


// 将数独文件转为cnf文件
void create_cnf(char* filename)
{
    //逐行读取数独文件
    PtrList* lines = read_lines(filename);
    char* line;
    list_get(lines, 0, &line);
    PtrList* list_cnf = list_create(1000);

    //生成完整的数独结构
    int total_size = rows->size + cols->size + boxes->size + pcf_boxes->size + cross_line->size;
    PtrList* ranges = list_create(total_size);
    for (int i = 0; i < rows->size; i++)
        list_append(ranges, rows->ptrArray[i]);
    for (int i = 0; i < cols->size; i++)
        list_append(ranges, cols->ptrArray[i]);
    for (int i = 0; i < boxes->size; i++)
        list_append(ranges, boxes->ptrArray[i]);
    for (int i = 0; i < pcf_boxes->size; i++)
        list_append(ranges, pcf_boxes->ptrArray[i]);
    for (int i = 0; i < cross_line->size; i++)
        list_append(ranges, cross_line->ptrArray[i]);

    //约束规则
    for (int k = 0; k < ranges->size; k++)
    {
        PtrList* rng;
        list_get(ranges, k, &rng);

        //每个格子可以是1到9
        for (int j = 0; j < rng->size; j++)
        {
            Coordinate* c;
            list_get(rng, j, &c);
            int x = c->row;
            int y = c->col;
            PtrList* temp;
            temp = list_create(10);
            for (int v = 1; v < 10; v++)
                list_append_int(temp, x * 100 + y * 10 + v);
            list_append(list_cnf, temp);
        }

        //1到9只能出现一次
        for (int v = 1; v < 10; v++)
        {
            for (int i = 0; i < 9; i++)
            {
                for (int j = i + 1; j < 9; j++)
                {
                    Coordinate *c1, *c2;
                    list_get(rng, i, &c1);
                    list_get(rng, j, &c2);
                    int x1 = c1->row;
                    int y1 = c1->col;
                    int x2 = c2->row;
                    int y2 = c2->col;
                    PtrList* temp2 = list_create(2);
                    list_append_int(temp2, -x1 * 100 - y1 * 10 - v);
                    list_append_int(temp2, -x2 * 100 - y2 * 10 - v);
                    list_append(list_cnf, temp2);
                }
            }
        }
    }

    //读入已有的数字
    PtrList* cur_numbers = list_create(81);
    for (int i = 0; i < 9; i++)
    {
        for (int j = 0; j < 9; j++)
        {
            char c = line[9 * i + j];
            if (c != '.')
            {
                PtrList* temp3 = list_create(3);
                list_append_int(temp3, i);
                list_append_int(temp3, j);
                list_append_int(temp3, c - '0');
                list_append(cur_numbers, temp3);
            }
        }
    }

    //将已填入的数字转为cnf
    for (int i = 0; i < cur_numbers->size; i++)
    {
        PtrList* temp4 = list_create(3);
        list_get(cur_numbers, i, &temp4);
        int x, y, v;
        list_get_int(temp4, 0, &x);
        list_get_int(temp4, 1, &y);
        list_get_int(temp4, 2, &v);
        PtrList* temp5 = list_create(1);
        list_append_int(temp5, 100 * (x + 1) + 10 * (y + 1) + v);
        list_append(list_cnf, temp5);
    }

    // debug: output list_cnf
    //FILE* tempf = fopen("E:\\Workspace\\2025summer\\c_sat\\list_cnf.txt", "wt");
    //for (int i = 0; i < list_cnf->size; i++)
    //{
    //	PtrList* cnf;
    //	list_get(list_cnf, i, &cnf);
    //	for (int j = 0; j < cnf->size; j++)
    //	{
    //		int v;
    //		list_get_int(cnf, j, &v);
    //		fprintf(tempf, "%d ", v);
    //	}
    //	fprintf(tempf, "\n");
    //}
    //
    //fclose(tempf);

    //文字去重，存入literals中
    PtrList* literals = list_create(100);
    for (int i = 0; i < list_cnf->size; i++)
    {
        PtrList* cnf;
        list_get(list_cnf, i, &cnf);
        for (int j = 0; j < cnf->size; j++)
        {
            int v;
            list_get_int(cnf, j, &v);
            int abs_v = abs(v);
            bool exist = list_int_in_list(literals, abs_v);
            if (!exist)
                list_append_int(literals, abs_v);
        }
    }

    //语句去重，存入sorted_clauses中
    PtrList* sorted_clauses = list_create(list_cnf->capacity);
    for (int i = 0; i < list_cnf->size; i++)
    {
        PtrList* clause;
        list_get(list_cnf, i, &clause);
        list_sort(clause, compare_int);
        bool exist = list_element_in_list(sorted_clauses, clause, compare_int_list);
        if (!exist)
            list_append(sorted_clauses, clause);
    }
    list_sort(sorted_clauses, compare_int_list_qsort);

    list_destroy(lines, free);

    //生成cnf文件
    FILE* fout = fopen("my_sudoku.cnf", "wt");
    if (!fout)
    {
        printf("无法打开文件");
        return;
    }
    fprintf(fout, "c sudoku output\n");
    fprintf(fout, "p cnf %d %d\n", literals->size, sorted_clauses->size); //注释和文件头
    for (int i = 0; i < sorted_clauses->size; i++)
    {
        PtrList* clause;
        list_get(sorted_clauses, i, &clause);
        for (int j = 0; j < clause->size; j++)
        {
            int l;
            list_get_int(clause, j, &l);
            fprintf(fout, "%d ", l);
        }
        fprintf(fout, "0\n");
    }
    fclose(fout);

    list_destroy(literals, NULL);
    list_destroy(list_cnf, destroy_clause);
    list_destroy(sorted_clauses, NULL);
}
