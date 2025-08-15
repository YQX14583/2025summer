#pragma once

#include <stdbool.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#define DeclareList(typename, element_type) \
typedef void (*typename##_destroyer)(element_type element);\
typedef int (*typename##_comparer)(element_type a, element_type b);\
typedef struct {\
    element_type* data;\
    int capacity;\
    int size;\
    typename##_destroyer destroyer;\
    typename##_comparer comparer;\
}typename;\
typename* typename##_create(int capacity);\
void typename##_destroy(typename* list);\
void typename##_append(typename* list, element_type val);\
bool typename##_get(typename* list, int index, element_type* ret);\
bool typename##_set(typename* list, int index, element_type val);\
void typename##_sort(typename* list);\
bool typename##_find(typename* list, element_type element);\
void typename##_random_shuffle(typename* list);\


#define DefineList(typename, element_type, destroyer_func, compare_func) \
typename* typename##_create(int capacity)\
{\
    if(capacity <= 0) capacity = 10;\
    typename* list = malloc(sizeof(typename));\
    if (!list) return NULL;\
    list->data = malloc(sizeof(element_type) * capacity);\
    if (!list->data)\
    {\
        free(list);\
        return NULL;\
    }\
    list->capacity = capacity;\
    list->size = 0;\
    list->destroyer = destroyer_func;\
    list->comparer = compare_func;\
    return list;\
}\
void typename##_destroy(typename* list)\
{\
    if (!list) return;\
    if (list->destroyer != NULL)\
    {\
        for (size_t i = 0; i < list->size; i++)\
            list->destroyer(list->data[i]);\
    }\
    free(list->data);\
    free(list);\
}\
void typename##_append(typename* list, element_type val)\
{\
    if (!list) return;\
    if (list->size >= list->capacity)\
    {\
        int new_capacity = list->capacity * 12 / 10 + 10;\
        element_type* new_array = realloc(list->data, sizeof(element_type) * new_capacity);\
        if (!new_array) return;\
        list->data = new_array;\
        list->capacity = new_capacity;\
    }\
    list->data[list->size] = val;\
    list->size++;\
}\
bool typename##_get(typename* list, int index, element_type* ret)\
{\
    if (!list || index < 0 || index >= list->size) return false;\
    if (ret) *ret = list->data[index];\
    return true;\
}\
bool typename##_set(typename* list, int index, element_type val)\
{\
    if (!list || index < 0 || index >= list->size) return false;\
    list->data[index] = val;\
    return true;\
}\
int typename##_comparer_qsort(void const* a, void const* b)\
{\
    return compare_func(*(element_type*)a, *(element_type*)b);\
}\
void typename##_sort(typename* list)\
{\
    if (!list || list->size <= 1) return;\
    qsort(list->data, list->size, sizeof(element_type), typename##_comparer_qsort);\
}\
bool typename##_find(typename* list, element_type val)\
{\
    if (!list) return false;\
    for (int i = 0; i < list->size; i++)\
    {\
        if (list->comparer(val, list->data[i]) == 0) return true;\
    }\
    return false;\
}\
void typename##_random_shuffle(typename* list)\
{\
    if (!list || list->size <= 1) return;\
    for (int i = 0; i < list->size * 10; i++)\
    {\
        int x = rand() % list->size;\
        int y = rand() % list->size;\
        element_type temp = list->data[x];\
        list->data[x] = list->data[y];\
        list->data[y] = temp;\
    }\
}\


DeclareList(Clause, int)
DeclareList(ClauseList, Clause*)


typedef void (*destroyer)(void*);
typedef int (*comparer)(const void* a, const void* b);

typedef struct
{
    void** ptrArray;
    int capacity;
    int size;
} PtrList;

PtrList* list_create(int capacity);

void list_destroy(PtrList* list, destroyer func);

void list_append(PtrList* list, void* ptr);

void list_append_int(PtrList* list, int value);

bool list_get(PtrList* list, int index, void** ret);

bool list_get_int(PtrList* list, int index, int* ret);

bool list_set_int(PtrList* list, int index, int value);

void list_sort(PtrList* list, comparer comp);

bool list_element_in_list(PtrList* list, const void* element, comparer comp);

bool list_int_in_list(PtrList* list, int val);

void list_random_shuffle(PtrList* list);

inline int compare_int(const void* a, const void* b)
{
    int ia = (int)(int64_t)*(void**)a; // 直接转换指针值为整数
    int ib = (int)(int64_t)*(void**)b;
    if (ia < ib) return -1;
    if (ia == ib) return 0;
    return 1;
}

inline int compare_int_list(const PtrList* a, const PtrList* b)
{
    if (a == NULL || b == NULL) return false;

    const int compare_size = min(a->size, b->size);
    for (int i = 0; i < compare_size; i++)
    {
        const int va = (int)(int64_t)a->ptrArray[i];
        const int vb = (int)(int64_t)b->ptrArray[i];
        if (va > vb) return 1;
        if (va < vb) return -1;
    }

    if (a->size > b->size) return 1;
    if (a->size < b->size) return -1;
    return 0;
}

inline int compare_int_list_qsort(const void* a, const void* b)
{
    return compare_int_list(*(PtrList**)a, *(PtrList**)b);
}
