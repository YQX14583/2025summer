#pragma once

#include <stdbool.h>
#include "list.h"

typedef struct
{
    int key;
    int value;
} KV;

int hash(int x);

typedef struct
{
    PtrList** buckets;
    int bucket_cnt;
} Dict;

Dict* dict_create(int bucket_cnt);

void dict_destory(Dict* dict);

PtrList* dict_get_bucket(const Dict* dict, int key);

KV* dict_find_kv(const Dict* dict, int key);

bool dict_set(const Dict* dict, int key, int value);

bool dict_get(const Dict* dict, int key, int* value);

typedef int (*kv_comparer)(const KV* a, const KV* b);

PtrList* dict_sorted(const Dict* dict, kv_comparer comp);