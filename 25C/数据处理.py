import pandas as pd

# 读取Excel
df = pd.read_excel('25年C题/附件.xlsx')


# 自定义转换函数
def week_to_float(week_str):
    if pd.isnull(week_str):
        return None
    week_str = str(week_str).lower().strip()
    if 'w' not in week_str:
        return None
    if '+' in week_str:
        weeks, days = week_str.split('w+')
        return float(weeks) + float(days) / 7
    else:
        weeks = week_str.replace('w', '')
        return float(weeks)


# 新增一列
df['检测孕周'] = df['检测孕周'].apply(week_to_float)

# 删除转换失败的行（如果有）
df = df.dropna(subset=['检测孕周'])


# 使用IQR方法筛选异常值（针对数值列）
def remove_outliers_iqr(df, columns):
    """
    使用IQR方法移除异常值
    """
    clean_df = df.copy()
    outliers_indices = set()

    for col in columns:
        if col in clean_df.columns:
            # 计算Q1, Q3和IQR
            Q1 = clean_df[col].quantile(0.25)
            Q3 = clean_df[col].quantile(0.75)
            IQR = Q3 - Q1

            # 定义异常值边界
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR

            print(f"列 '{col}': Q1={Q1:.4f}, Q3={Q3:.4f}, IQR={IQR:.4f}")
            print(f"  正常值范围: [{lower_bound:.4f}, {upper_bound:.4f}]")

            # 找出异常值的索引
            col_outliers = clean_df[(clean_df[col] < lower_bound) | (clean_df[col] > upper_bound)].index
            outliers_indices.update(col_outliers)

            print(f"  发现 {len(col_outliers)} 个异常值")

    # 移除所有包含异常值的行
    clean_df = clean_df.drop(index=outliers_indices)
    print(f"\n总共移除 {len(outliers_indices)} 行包含异常值的数据")
    print(f"剩余数据行数: {len(clean_df)}")

    return clean_df


# 指定要检查异常值的数值列
numeric_columns = ['检测孕周', '孕妇BMI', 'Y染色体浓度', ]

# 移除异常值
df_clean = remove_outliers_iqr(df, numeric_columns)

# 保存处理后的数据
df_clean.to_excel('第一问_孕周小数_去除异常值.xlsx', index=False)
print("处理完成，数据已保存!")
