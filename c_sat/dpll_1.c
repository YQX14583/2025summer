#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <math.h>

#include "dict.h"
#include "list.h"
#include "sudoku.h"
#include "dpll.h"
#include "dpll_1.h"


// ===== 改进后的 Jeroslow–Wang 变量选择 =====
int find_literal_1(PtrList* clauses)
{
    Dict* score = dict_create(16);

    // 遍历所有子句
    for (int i = 0; i < clauses->size; i++)
    {
        PtrList* c;
        list_get(clauses, i, &c);

        int clause_len = c->size;
        if (clause_len == 0) continue; // 跳过空子句（冲突检测由外层处理）

        double weight = pow(2.0, -clause_len); // 短子句权重大

        for (int j = 0; j < c->size; j++)
        {
            int lit;
            list_get_int(c, j, &lit);
            int var = abs(lit);

            double cur_score;
            if (!dict_get(score, var, &cur_score))
                cur_score = 0.0;
            dict_set(score, var, cur_score + weight);
        }
    }

    // 找分数最高的变量
    int best_var = 0;
    double best_score = -1.0;

    for (int b = 0; b < score->bucket_cnt; b++)
    {
        PtrList* bucket = score->buckets[b];
        for (int k = 0; k < bucket->size; k++)
        {
            KV* kv = bucket->ptrArray[k];
            double var_score = kv->value;
            if (var_score > best_score)
            {
                best_score = var_score;
                best_var = kv->key;
            }
        }
    }

    dict_destroy(score);
    return best_var == 0 ? 1 : best_var;
}


//dpll函数
PtrList* dpll_reduce_1(PtrList* _cur_literals, PtrList* _cur_clauses)
{

    PtrList* cur_literals = clone_clause(_cur_literals);
    PtrList* cur_clauses = clone_clauses(_cur_clauses);

    //通过单子句规则化简
    while (true)
    {
        bool found = false;

        for (int i = 0; i < cur_clauses->size; i++)
        {
            PtrList* c;
            list_get(cur_clauses, i, &c);
            if (c->size == 1)
            {
                found = true;
                break;
            }
        }
        if (!found)
            break;

        PtrList* single_litral_clauses = list_create(cur_clauses->capacity);
        for (int i = 0; i < cur_clauses->size; i++)
        {
            PtrList* c;
            list_get(cur_clauses, i, &c);
            if (c->size == 1)
                list_append(single_litral_clauses, c);
        }

        PtrList* first_clause;
        list_get(single_litral_clauses, 0, &first_clause);
        int single_literal;
        list_get_int(first_clause, 0, &single_literal);
        list_destroy(single_litral_clauses, NULL);

        list_append_int(cur_literals, single_literal);
        PtrList* new_clauses = assign(single_literal, cur_clauses);
        list_destroy(cur_clauses, destroy_clause); // 通过函数指针指定销毁方式
        cur_clauses = new_clauses;

        //判断是否结束
        if (cur_clauses->size == 0)
        {
            list_destroy(cur_clauses, destroy_clause);
            return cur_literals;
        }

        bool found_empty_clause = false;
        for (int i = 0; i < cur_clauses->size; i++)
        {
            PtrList* c;
            list_get(cur_clauses, i, &c);
            if (c->size == 0)
            {
                found_empty_clause = true;
                break;
            }
        }
        if (found_empty_clause)
        {
            list_destroy(cur_clauses, destroy_clause);
            list_destroy(cur_literals, NULL);
            return NULL;
        }
    }

    //判断是否结束
    if (cur_clauses->size == 0)
    {
        list_destroy(cur_clauses, destroy_clause);
        return cur_literals;
    }

    bool found_empty_clause = false;
    for (int i = 0; i < cur_clauses->size; i++)
    {
        PtrList* c;
        list_get(cur_clauses, i, &c);
        if (c->size == 0)
        {
            found_empty_clause = true;
            break;
        }
    }
    if (found_empty_clause)
    {
        list_destroy(cur_clauses, destroy_clause);
        list_destroy(cur_literals, NULL);
        return NULL;
    }

    //选择文字赋值
    int next_lit = find_literal_1(cur_clauses);

    //尝试赋值为true
    PtrList* reduced_clauses_true = assign(next_lit, cur_clauses);
    PtrList* new_literals_true = clone_clause(cur_literals);
    list_append_int(new_literals_true, next_lit);
    PtrList* result = dpll_reduce_1(new_literals_true, reduced_clauses_true);
    if (result != NULL)
    {
        list_destroy(new_literals_true, NULL);
        list_destroy(reduced_clauses_true, destroy_clause);
        list_destroy(cur_literals, NULL);
        return result;
    }
    list_destroy(new_literals_true, NULL);
    list_destroy(reduced_clauses_true, destroy_clause);

    //尝试赋值为false
    PtrList* reduced_clauses_false = assign(-next_lit, cur_clauses);
    PtrList* new_literals_false = clone_clause(cur_literals);
    list_append_int(new_literals_false, -next_lit);
    result = dpll_reduce_1(new_literals_false, reduced_clauses_false);
    list_destroy(new_literals_false, NULL);
    list_destroy(reduced_clauses_false, destroy_clause);

    list_destroy(cur_literals, NULL);
    return result;
}