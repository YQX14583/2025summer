#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>

#include "dict.h"


int hash(int x)
{
    x = ((x >> 16) ^ x) * 0x45d9f3b;
    x = ((x >> 16) ^ x) * 0x45d9f3b;
    x = (x >> 16) ^ x;
    if (x < 0) x = -x;
    return x;
}

//带嵌套销毁的KV对
void destroy_kv_pair(void* element)
{
    if (!element) return;
    KV* kv = element;
    // 如果KV.value需要特殊处理：
    // if (kv->value_needs_free) free(kv->value);
    free(kv);
}

Dict* dict_create(int bucket_cnt)
{
    Dict* dict = malloc(sizeof(Dict));
    if (!dict)
        return NULL;

    dict->buckets = (PtrList**)malloc(sizeof(PtrList*) * bucket_cnt);
    if (!dict->buckets)
    {
        free(dict);
        return NULL;
    }

    for (int i = 0; i < bucket_cnt; ++i)
    {
        dict->buckets[i] = list_create(32);
    }
    dict->bucket_cnt = bucket_cnt;

    return dict;
}

void dict_destory(Dict* dict)
{
    for (int i = 0; i < dict->bucket_cnt; ++i)
    {
        PtrList* bucket = dict->buckets[i];
        list_destroy(bucket, destroy_kv_pair);
    }

    free(dict->buckets);
    free(dict);
}

PtrList* dict_get_bucket(const Dict* dict, const int key)
{
    // get bucket by hash of key
    const int bucket_idx = hash(key) % dict->bucket_cnt;
    PtrList* bucket = dict->buckets[bucket_idx];
    return bucket;
}

KV* dict_find_kv(const Dict* dict, const int key)
{
    PtrList* bucket = dict_get_bucket(dict, key);

    // search key in bucket
    KV* kv = NULL;
    for (int i = 0; i < bucket->size; ++i)
    {
        KV* kv2 = bucket->ptrArray[i];
        if (kv2->key == key)
        {
            kv = kv2;
            break;
        }
    }

    return kv;
}

bool dict_set(const Dict* dict, const int key, const int value)
{
    KV* kv = dict_find_kv(dict, key);
    if (kv == NULL)
    {
        // insert new kv into bucket
        kv = malloc(sizeof(KV));
        if (kv)
        {
            kv->key = key;
            kv->value = value;

            PtrList* bucket = dict_get_bucket(dict, key);
            list_append(bucket, kv);
            return true;
        }
        return false;
    }
    kv->value = value;
    return true;
}

bool dict_get(const Dict* dict, const int key, int* value)
{
    KV* kv = dict_find_kv(dict, key);
    if (kv == NULL)
    {
        return false;
    }
    *value = kv->value;
    return true;
}

// 排序
PtrList* dict_sorted(const Dict* dict, kv_comparer comp)
{
    //取出所有键值对
    PtrList* kvs = list_create(dict->bucket_cnt * 32);
    for (int i = 0; i < dict->bucket_cnt; i++)
    {
        PtrList* bucket = dict->buckets[i];
        for (int j = 0; j < bucket->size; j++)
        {
            KV* kv = bucket->ptrArray[j];
            list_append(kvs, kv);
        }
    }
    qsort(kvs->ptrArray, kvs->size, sizeof(KV*), comp);
    return kvs;
}
