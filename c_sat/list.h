#pragma once
#ifdef __cplusplus
extern "C" {
#endif

#include <stdbool.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

// 指针列表结构体
typedef struct
{
    void** ptrArray;
    int capacity;
    int size;
} PtrList;

// 函数指针类型定义
typedef void (*destroyer)(void*);
typedef int (*comparer)(const void* a, const void* b);
// 创建新的 PtrList
PtrList* list_create(int capacity);
// 销毁 PtrList
void list_destroy(PtrList* list, destroyer func);
// 追加元素
void list_append(PtrList* list, void* ptr);
// 追加整型值
void list_append_int(PtrList* list, int value);
// 获取元素
bool list_get(PtrList* list, int index, void** ret);
// 获取整型值
bool list_get_int(PtrList* list, int index, int* ret);
// 设置整型元素
bool list_set_int(PtrList* list, int index, int value);
// 列表排序
void list_sort(PtrList* list, comparer comp);
// 判断元素是否在列表中
bool list_element_in_list(PtrList* list, const void* element, comparer comp);
// 判断整数是否在列表中
bool list_int_in_list(PtrList* list, int val);
// 随机打乱列表
void list_random_shuffle(PtrList* list);
// 比较两个整数
int compare_int(const void* a, const void* b);
// 比较两个整数的绝对值
int compare_int_list(const PtrList* a, const PtrList* b);
// qsort用的比较函数
int compare_int_list_qsort(const void* a, const void* b);

#ifdef __cplusplus
}
#endif