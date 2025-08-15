#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "dict.h"
#include "sudoku.h"
#include "dpll.h"

//按照空格分割字符串
PtrList* str_split(const char* s)
{
    PtrList* result = list_create(5);
    if (!s) return result;

    //分割字符串
    char* str = strdup(s);
    char* next_token = NULL;
    char* token = strtok_s(str, " \t\n\r", &next_token);
    while (token)
    {
        char* elem = strdup(token);
        list_append(result, elem);
        token = strtok_s(NULL, " \t\n\r", &next_token);
    }
    free(str);
    return result;
}


//读cnf文件
PtrList* read_cnf_file(const char* filename)
{
    //逐行读取cnf文件
    PtrList* lines = read_lines(filename);
    PtrList* clauses = list_create(100);
    for (int i = 0; i < lines->size; i++)
    {
        char* s;
        list_get(lines, i, &s);

        char ch = s[0];
        if (ch == 'c')
        {
            //跳过注释
            continue;
        }
        if (ch == 'p')
        {
            //读取文件头
            PtrList* ss = str_split(s);
            char* ss2;
            list_get(ss, 2, &ss2);
            int literal_cnt = atoi(ss2);
            char* ss3;
            list_get(ss, 3, &ss3);
            int clause_cnt = atoi(ss3);
            printf("literals count: %d, clauses count: %d\n\n", literal_cnt, clause_cnt);
            list_destroy(ss, free);
        }
        else
        {
            //处理cnf文件
            PtrList* ss = str_split(s);
            if (ss->size > 0)
            {
                PtrList* clause = list_create(100);
                for (int j = 0; j < ss->size - 1; j++)
                {
                    char* v;
                    list_get(ss, j, &v);
                    int literal = atoi(v);
                    list_append_int(clause, literal);
                }
                list_append(clauses, clause);
            }
            list_destroy(ss, free);
        }
    }

    list_destroy(lines, free);
    return clauses;
}


//嵌套PtrList销毁（用于子句列表）
void destroy_clause(void* element)
{
    PtrList* clause = element;
    list_destroy(clause, NULL);
}


// 比较KV
int comp_by_v(const KV* a, const KV* b)
{
    return a->value - b->value;
}


//复制子句
PtrList* clone_clause(PtrList* clause)
{
    PtrList* new_clause = list_create(clause->size + 1);
    for (int i = 0; i < clause->size; i++)
    {
        int lit;
        list_get_int(clause, i, &lit);
        list_append_int(new_clause, lit);
    }
    return new_clause;
}


//复制子句列表
PtrList* clone_clauses(PtrList* clauses)
{
    PtrList* new_clauses = list_create(clauses->size + 1);
    for (int i = 0; i < clauses->size; i++)
    {
        PtrList* c;
        list_get(clauses, i, &c);
        list_append(new_clauses, clone_clause(c));
    }
    return new_clauses;
}


//处理赋值的文字
PtrList* assign(int x, PtrList* clauses)
{
    PtrList* new_clauses = list_create(clauses->capacity);
    for (int i = 0; i < clauses->size; i++)
    {
        PtrList* clause;
        list_get(clauses, i, &clause);

        if (list_int_in_list(clause, x))
            continue;

        PtrList* new_clause = list_create(clause->capacity);
        for (int j = 0; j < clause->size; j++)
        {
            int l;
            list_get_int(clause, j, &l);
            if (l != -x)
                list_append_int(new_clause, l);
        }
        list_append(new_clauses, new_clause);
    }
    return new_clauses;
}


//找到出现次数最多的文字
int find_literal(PtrList* clauses)
{
    Dict* freq = dict_create(16);
    for (int i = 0; i < clauses->size; i++)
    {
        PtrList* c;
        list_get(clauses, i, &c);
        for (int j = 0; j < c->size; j++)
        {
            int lit;
            list_get_int(c, j, &lit);
            int cur_cnt;
            if (!dict_get(freq, lit, &cur_cnt))
                cur_cnt = 0;
            dict_set(freq, lit, cur_cnt + 1);
        }
    }

    PtrList* sorted_kv = dict_sorted(freq, comp_by_v);
    KV* first_kv = NULL;
    list_get(sorted_kv, 0, &first_kv);
    int max_lit = first_kv->key;

    list_destroy(sorted_kv, NULL);
    dict_destory(freq);

    return max_lit;
}


//dpll函数
PtrList* dpll_reduce(PtrList* _cur_literals, PtrList* _cur_clauses)
{
    PtrList* cur_literals = clone_clause(_cur_literals);
    PtrList* cur_clauses = clone_clauses(_cur_clauses);

    //通过单子句规则化简
    //int loop_counter = 0;
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
    int next_lit = find_literal(cur_clauses);

    //尝试赋值为true
    PtrList* reduced_clauses_true = assign(next_lit, cur_clauses);
    PtrList* new_literals_true = clone_clause(cur_literals);
    list_append_int(new_literals_true, next_lit);
    PtrList* result = dpll_reduce(new_literals_true, reduced_clauses_true);
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
    result = dpll_reduce(new_literals_false, reduced_clauses_false);
    list_destroy(new_literals_false, NULL);
    list_destroy(reduced_clauses_false, destroy_clause);

    list_destroy(cur_literals, NULL);
    return result;
}
