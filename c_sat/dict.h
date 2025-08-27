#pragma once

#include <stdbool.h>
#include "list.h"

// 键值对结构体
typedef struct
{
    int key;
    int value;
} KV;
// 字典结构体
typedef struct
{
    PtrList** buckets;
    int bucket_cnt;
} Dict;

// 简单的整数哈希函数
int hash(int x);
// 带嵌套销毁的KV对
Dict* dict_create(int bucket_cnt);
// 销毁字典
void dict_destroy(Dict* dict);
// 获取键对应的桶
PtrList* dict_get_bucket(const Dict* dict, int key);
// 通过键查找键值对
KV* dict_find_kv(const Dict* dict, int key);
// 设置键值对
bool dict_set(const Dict* dict, int key, int value);
// 获取键对应的值
bool dict_get(const Dict* dict, int key, int* value);
// 比较函数类型定义
typedef int (*kv_comparer)(const KV* a, const KV* b);
// 字典排序
PtrList* dict_sorted(const Dict* dict, kv_comparer comp);