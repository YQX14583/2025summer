#pragma once
#ifdef __cplusplus
extern "C" {
#endif

#include "list.h"

// 将字符串按空格分割成指针列表
PtrList* str_split_1(const char* s);
// 读取cnf文件
PtrList* read_cnf_file_1(const char* filename);
// 销毁子句
void destroy_clause_1(void* element);
// 比较KV
int comp_by_v_1(const KV* a, const KV* b);
// 复制子句
PtrList* clone_clause_1(PtrList* clause);
// 复制子句列表
PtrList* clone_clauses_1(PtrList* clauses);
// 处理赋值的文字
PtrList* assign_1(int x, PtrList* clauses);
// 找到出现次数最多的文字
int find_literal_1(PtrList* clauses);
// DPLL算法主函数（优化版）
PtrList* dpll_reduce_1(PtrList* cur_literals, PtrList* cur_clauses);
// 输出结果到文件
void dpll_output_result_1(const char* filename, int status, PtrList* solution, double time_ms);

#ifdef __cplusplus
}
#endif