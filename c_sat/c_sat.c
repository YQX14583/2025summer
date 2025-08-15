#define _CRTDBG_MAP_ALLOC

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

/*
void test1()
{
	while (1)
	{
		PtrList* list = list_create(1000000);
		for (int i = 0; i < 1000000; i++)
		{
			Coordinate* c = malloc(sizeof(Coordinate));
			if (c)
			{
				c->row = 1;
				c->col = 2;
				list_append(list, c);
			}
		}
		list_destroy(list, free);
	}
}

void test2()
{
	PtrList* list = list_create(10);
	int a = 10, b = 4;
	list_append_int(list, a);
	list_append_int(list, b);
	list_append_int(list, 8);
	for (int i=0; i < list->size; i++)
	{
		printf("%lld ", (int64_t)list->ptrArray[i]);
	}
	printf("\n");
	list_sort(list, compare_int);
	for (int i=0; i < list->size; i++)
	{
		printf("%lld ", (int64_t)list->ptrArray[i]);
	}
	list_destroy(list, NULL);
}

void test3()
{
	Dict* dict = dict_create(5);
	dict_set(dict, 1, 100);
	dict_set(dict, 2, 200);
	int val;
	dict_get(dict, 2, &val);
	printf("%d\n", val);
	dict_set(dict, 2, 222);
	dict_set(dict, 3, 300);
	dict_set(dict, 4, 400);
	for (int i = 0; i < dict->bucket_cnt; i++)
	{
		PtrList* bucket = dict->buckets[i];
		for (int j = 0; j < bucket->size; j++)
		{

			KV* kv = bucket->ptrArray[j];
			printf("%d,%d ", kv->key, kv->value);
		}
	}
	printf("\n");
	PtrList* kvs = list_create(4);
	//kvs = dict_sorted(dict);
	//for (int i = 0; i < kvs->size; i++) {
	//	KV* kv = kvs->ptrArray[i];
	//	printf("%d,%d ", kv->key, kv->value);
	//}
	dict_destory(dict);
}

void test4()
{
	while (1)
	{
		Dict* dict = dict_create(1000);
		for (int i = 0; i < 1000000; i++)
		{
			dict_set(dict, i, i*i);
		}
		dict_destory(dict);
	}
}

int main(void)
{
	init_sudoku_structures();

	printf("");
	return 0;
}
*/

int compare_abs(const void* a, const void* b)
{
    int ia = abs(*(const int*)a);
    int ib = abs(*(const int*)b);
    return (ia > ib) - (ia < ib);
}


int main2()
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

        if (op == 1)
        {
            //输入1——读取cnf文件并计算结果
            char filename[1024];
            printf("Please input a filename : ");
            scanf_s("%s", filename, (unsigned)_countof(filename));
            PtrList* cnf_clauses = read_cnf_file(filename);

            //计算用时
            clock_t start_time = clock();
            PtrList* cur_literals = list_create(10240);
            PtrList* result = dpll_reduce(cur_literals, cnf_clauses);
            clock_t end_time = clock();
            double elapsed = (double)(end_time - start_time) / CLOCKS_PER_SEC;

            //输出结果
            if (result)
            {
                list_sort(result, compare_abs);
                printf("The solution is: ");
                for (int i = 0; i < result->size; i++)
                {
                    int v;
                    list_get_int(result, i, &v);
                    printf("%d ", v);
                }
                printf("\n");
            }
            else
                printf("No solution found!\n");

            printf("(time cost: %.4f s)", elapsed);

            list_destroy(cur_literals, NULL);
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

            //将数独转化为sat并写入cnf文件
            create_sudoku_txt(my_sudoku);
            list_destroy(my_sudoku, destroy_clause);

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

    _CrtDumpMemoryLeaks();
    return 0;
}

void dump_clause(Clause* c)
{
    for (int i = 0; i < c->size; ++i)
    {
        int v;
        Clause_get(c, i, &v);
        printf("%d ", v);
    }
    printf("\n");
}

int main(void)
{
    Clause* c = Clause_create(1);
    for (int i = 0; i < 1000; ++i)
    {
        Clause_append(c, i);
    }
    dump_clause(c);
    return 0;
}
