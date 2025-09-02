#include <stdlib.h>
#include <crtdbg.h>
#include <stdio.h>
#include <stdint.h>
#include <time.h>

#include "list.h"
#include "dict.h"
#include "sudoku.h"
#include "sudoku_to_sat.h"
#include "create_sudoku.h"
#include "dpll.h"
#include "dpll_1.h"

#include <graphics.h>
#include <fstream>
#include <iostream>
#include <conio.h>
using namespace std;

#define CELL_SIZE 50

char sudoku[9][9];

// 从文件加载数独
bool loadSudoku(const char* filename) {
    ifstream fin(filename);
    if (!fin) return false;
    char ch;
    for (int i = 0; i < 9; i++)
        for (int j = 0; j < 9; j++)
            fin >> ch, sudoku[i][j] = ch;
    return true;
}

// 绘制数独网格线
void drawBoard() {
    setlinecolor(BLACK);
    for (int i = 0; i <= 9; i++) {
        if (i % 3 == 0) setlinestyle(PS_SOLID, 3);
        else setlinestyle(PS_SOLID, 1);
        line(0, i * CELL_SIZE, 9 * CELL_SIZE, i * CELL_SIZE);
        if (i % 3 == 0) setlinestyle(PS_SOLID, 3);
        else setlinestyle(PS_SOLID, 1);
        line(i * CELL_SIZE, 0, i * CELL_SIZE, 9 * CELL_SIZE);
    }
}


// 绘制数独中的数字
void drawNumbers()
{
    settextstyle(24, 0, L"Consolas");
    setbkmode(TRANSPARENT);
    settextcolor(BLACK);

    static wchar_t str[2]; // 静态缓冲区，避免局部变量在 closegraph 后失效

    for (int i = 0; i < 9; i++)
        for (int j = 0; j < 9; j++)
            if (sudoku[i][j] != '.') {
                str[0] = (wchar_t)sudoku[i][j];
                str[1] = L'\0';
                outtextxy(j * CELL_SIZE + 15, i * CELL_SIZE + 12, str);
            }
}


// 绘制数独界面
void drawSudoku() {
    setfillcolor(RGB(240, 248, 255));
    solidrectangle(0, 0, 9 * CELL_SIZE, 9 * CELL_SIZE);

    // 百分号区域高亮
    for (int i = 0; i < 9; i++) {
        for (int j = 0; j < 9; j++) {

            bool inFirstBlock = (i >= 1 && i <= 3 && j >= 1 && j <= 3);
            bool inSecondBlock = (i >= 5 && i <= 7 && j >= 5 && j <= 7);
            bool onAntiDiagonal = (i + j == 8);

            if (inFirstBlock || inSecondBlock || onAntiDiagonal) {
                setfillcolor(RGB(255, 255, 224)); // 浅黄色
                solidrectangle(
                    j * CELL_SIZE,
                    i * CELL_SIZE,
                    (j + 1) * CELL_SIZE,
                    (i + 1) * CELL_SIZE
                );
            }
        }
    }

    drawBoard();

    drawNumbers();
}


int compare_abs(const void* a, const void* b)
{
    int ia = abs(*(const int*)a);
    int ib = abs(*(const int*)b);
    return (ia > ib) - (ia < ib);
}


int main()
{
    srand((unsigned)time(NULL));

    init_sudoku_structures();

    printf("Welcome!\n");

    while (1)
    {
        printf("\nSAT -- 1, Percent-Sudoku -- 2, exit -- 0\n");
        printf("Please choose a number: ");
        int op;
        scanf_s("%d", &op);
        printf("\n");

        if (op == 1) {
            char filename[1024];
            printf("Please input a filename: ");
            scanf_s("%s", filename, (unsigned)_countof(filename));
            PtrList* cnf_clauses = read_cnf_file(filename);
            if (!cnf_clauses) continue;

            // 计算用时
            clock_t start_time = clock();
            PtrList* cur_literals = list_create(10240);
            PtrList* result = dpll_reduce_1(cur_literals, cnf_clauses);
            clock_t end_time = clock();
            double elapsed = (double)(end_time - start_time) / CLOCKS_PER_SEC;

            // 输出结果
            if (result) {
                list_sort(result, compare_abs);
                printf("The solution is: ");
                for (int i = 0; i < result->size; i++) {
                    int v;
                    list_get_int(result, i, &v);
                    printf("%d ", v);
                }
                printf("\n");
                // 输出到文件
                dpll_output_result(filename, DPLL_SAT, result, elapsed);
            }
            else {
                printf("No solution found!\n");
                // 输出到文件
                dpll_output_result(filename, DPLL_UNSAT, NULL, elapsed);
            }

            printf("(time cost: %.4f s)\n", elapsed);

            list_destroy(cur_literals, NULL);
            list_destroy(cnf_clauses, destroy_clause);
        }

        else if (op == 2)
        {
            //输入2——随机生成百分号数独并求解
            //随机初始化数独游戏格局
            clock_t start_time = clock();
            PtrList* my_sudoku = create_puzzle();
            clock_t end_time = clock();
            double elapsed = (double)(end_time - start_time) / CLOCKS_PER_SEC;
            printf("\n(time cost: %.4f s)\n", elapsed);

            //将数独转化为sat并写入txt文件
            create_sudoku_txt(my_sudoku);

            // GUI显示初始数独
            if (!loadSudoku("my_sudoku.txt")) {
                cout << "读取数独文件失败！" << endl;
                return 1;
            }
            initgraph(9 * CELL_SIZE, 9 * CELL_SIZE);
            drawSudoku();
            list_destroy(my_sudoku, destroy_clause);

            getchar(); getchar();

            char filename[] = "my_sudoku.txt";
            create_cnf(filename);
            printf("sudoku has been written in: my_sudoku.cnf\n");

            //计算用时
            char filename2[] = "my_sudoku.cnf";
            PtrList* cnf_clauses = read_cnf_file(filename2);
            clock_t start_time2 = clock();
            PtrList* cur_literals = list_create(10240);
            PtrList* result = dpll_reduce(cur_literals, cnf_clauses);
            clock_t end_time2 = clock();
            double elapsed2 = (double)(end_time2 - start_time2) / CLOCKS_PER_SEC;

            //输出结果
            if (result)
            {
                //输出数独的解
                list_sort(result, compare_abs);
                PtrList* new_result = list_create(10240);
                printf("The solution is : ");
                for (int i = 0; i < result->size; i++)
                {
                    int x;
                    list_get_int(result, i, &x);
                    if (x >= 0)
                    {
                        printf("%d ", x);
                        list_append_int(new_result, x);
                    }
                }
                printf("\n\n");

                //初始化数独矩阵
                PtrList* matrix = list_create(9);
                for (int i = 0; i < 9; i++)
                {
                    PtrList* matrix_row = list_create(9);
                    for (int j = 0; j < 9; j++)
                        list_append_int(matrix_row, 0);
                    list_append(matrix, matrix_row);
                }

                //输出数独解的棋盘
                for (int i = 0; i < new_result->size; i++)
                {
                    int num;
                    list_get_int(new_result, i, &num);
                    int row = num / 100 - 1;
                    int col = (num / 10) % 10 - 1;
                    int value = num % 10;
                    sudoku_set_int(matrix, row, col, value);
                }
                print_board(matrix);
                printf("\n");

                create_sudoku_txt(matrix);

                // GUI显示初始数独
                if (!loadSudoku("my_sudoku.txt")) {
                    cout << "读取数独文件失败！" << endl;
                    return 1;
                }
                initgraph(9 * CELL_SIZE, 9 * CELL_SIZE);
                drawSudoku();

                list_destroy(matrix, destroy_clause);
                list_destroy(result, NULL);
            }
            else
                printf("No solution found!\n");

            printf("(time cost: %.4f s)\n", elapsed2);

            list_destroy(cur_literals, NULL);
            list_destroy(cnf_clauses, destroy_clause);
        }
        else if (op == 0)
        {
            //输入0——退出程序
            printf("Thank you!\n");
            break;
        }
        else
        {
            //其他不合法输入
            printf("Invalid input!\n");
        }
    }
}