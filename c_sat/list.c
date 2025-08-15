#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>
#include "list.h"

int compare_int32(int a, int b)
{
    if (a < b) return -1;
    if (a == b) return 0;
    return 1;
}

int compare_clause(Clause* a, Clause* b)
{
    if (a == NULL || b == NULL) return false;

    const int compare_size = min(a->size, b->size);
    for (int i = 0; i < compare_size; i++)
    {
        const int va = a->data[i];
        const int vb = b->data[i];
        if (va > vb) return 1;
        if (va < vb) return -1;
    }

    if (a->size > b->size) return 1;
    if (a->size < b->size) return -1;
    return 0;
}

DefineList(Clause, int, NULL, compare_int32)
DefineList(ClauseList, Clause*, Clause_destroy, compare_clause)


// 创建新的 PtrList
PtrList* list_create(int capacity)
{
    PtrList* list = malloc(sizeof(PtrList));
    if (!list) return NULL;
    list->ptrArray = malloc(sizeof(void*) * capacity);
    if (!list->ptrArray)
    {
        free(list);
        return NULL;
    }

    list->capacity = capacity;
    list->size = 0;
    return list;
}


// 销毁 PtrList
void list_destroy(PtrList* list, destroyer func)
{
    if (list)
    {
        if (list->ptrArray)
        {
            if (func != NULL)
            {
                for (size_t i = 0; i < list->size; i++)
                {
                    //printf("ptrArray[%zu] = %p\n", i, list->ptrArray[i]);
                    func(list->ptrArray[i]);
                }
            }

            free(list->ptrArray);
        }
        free(list);
    }
}


// 追加元素
void list_append(PtrList* list, void* ptr)
{
    if (!list)
        return;

    // 需要扩容
    if (list->size >= list->capacity)
    {
        int new_capacity = list->capacity * 12 / 10 + 10;
        void** new_array = realloc(list->ptrArray, sizeof(void*) * new_capacity);
        if (!new_array) return; // 扩容失败

        list->ptrArray = new_array;
        list->capacity = new_capacity;
    }

    list->ptrArray[list->size] = ptr;
    list->size++;
}


// 获取元素
bool list_get(PtrList* list, int index, void** ret)
{
    if (!list || index < 0 || index >= list->size)
    {
        return false; // 失败
    }

    if (ret)
    {
        *ret = list->ptrArray[index];
    }

    return true; // 成功
}


// 追加整型值
void list_append_int(PtrList* list, int value)
{
    list_append(list, (void*)(int64_t)value);
}


// 获取整型值
bool list_get_int(PtrList* list, int index, int* ret)
{
    void* ptr;
    if (!list_get(list, index, &ptr))
    {
        return false; // 失败
    }

    if (ret)
    {
        *ret = (int)(int64_t)ptr;
    }

    return true; // 成功
}

// 设置整型元素
bool list_set_int(PtrList* list, int index, int value)
{
    if (!list || index < 0 || index >= list->size)
        return false;
    list->ptrArray[index] = (void*)(int64_t)value;
    return true;
}

// 排序
void list_sort(PtrList* list, comparer comp)
{
    if (!list || list->size <= 1) return;
    qsort(list->ptrArray, list->size, sizeof(void*), comp);
}


// 判断元素是否在表内
bool list_element_in_list(PtrList* list, const void* element, comparer comp)
{
    if (!list || !element) return false;

    for (int j = 0; j < list->size; j++)
    {
        void* val;
        list_get(list, j, &val);
        if (comp(element, val) == 0)
        {
            return true;
        }
    }

    return false;
}

bool list_int_in_list(PtrList* list, int val)
{
    if (!list) return false;

    for (int j = 0; j < list->size; j++)
    {
        if ((int)(int64_t)list->ptrArray[j] == val)
            return true;
    }

    return false;
}

// 随机调换顺序
void list_random_shuffle(PtrList* list)
{
    if (!list || list->size <= 1) return;

    for (int i = 0; i < list->size * 10; i++)
    {
        int x = rand() % list->size;
        int y = rand() % list->size;
        void* temp = list->ptrArray[x];
        list->ptrArray[x] = list->ptrArray[y];
        list->ptrArray[y] = temp;
    }
}
