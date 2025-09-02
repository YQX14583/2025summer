#pragma once
#ifdef __cplusplus
extern "C" {
#endif

#include <stdlib.h>
#include "list.h"

// 数独结构
extern PtrList* rows;
extern PtrList* cols;
extern PtrList* boxes;
extern PtrList* pcf_centers;
extern PtrList* pcf_boxes;
extern PtrList* cross_line;

// 初始化数独结构
void init_sudoku_structures();
// 将数独文件转为cnf文件 
void create_cnf(char* filename);

#ifdef __cplusplus
}
#endif