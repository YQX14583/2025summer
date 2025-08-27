#pragma once

// 将字符串按空格分割成指针列表
PtrList* str_split(const char* s);
// 读取cnf文件
PtrList* read_cnf_file(const char* filename);
// 销毁子句
void destroy_clause(void* element);
// 比较KV
int comp_by_v(const KV* a, const KV* b);
// 复制子句
PtrList* clone_clause(PtrList* clause);
// 复制子句列表
PtrList* clone_clauses(PtrList* clauses);
// 处理赋值的文字
PtrList* assign(int x, PtrList* _clauses);
// 找到出现次数最多的文字
int find_literal(PtrList* clauses);
// DPLL算法主函数
PtrList* dpll_reduce(PtrList* cur_literals, PtrList* cur_clauses);
// 嵌套PtrList销毁（用于子句列表）
void destroy_clause(void* element);