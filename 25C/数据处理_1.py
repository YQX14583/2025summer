import pandas as pd

# 假设读取表格数据
data = pd.read_excel("附件1.xlsx")

non_empty_abnormality = data[data['染色体的非整倍体'].notna()]
print(f"保留染色体的非整倍体非空数据：{len(non_empty_abnormality)} 行。")

# 过滤掉`priority_data`外的其余数据，进行IQR筛选
columns_to_filter = [
    '孕妇BMI',
    '原始读段数',
    '在参考基因组上比对的比例',
    '重复读段的比例',
    '唯一比对的读段数',
    'GC含量',
    '13号染色体的Z值',
    '18号染色体的Z值',
    '21号染色体的Z值',
    'X染色体的Z值',
    'X染色体浓度',
    '13号染色体的GC含量',
    '18号染色体的GC含量',
    '21号染色体的GC含量',
    '被过滤掉读段数的比例'
]

# 剔除未在优先保留数据集的部分，应用IQR筛选
remaining_data = data[~data['孕妇代码'].isin(non_empty_abnormality)]

# 筛选函数：基于IQR剔除离群值
def filter_by_iqr(df, column):
    Q1 = df[column].quantile(0.25)  # 25%分位数
    Q3 = df[column].quantile(0.75)  # 75%分位数
    IQR = Q3 - Q1  # 四分位距
    lower_bound = Q1 - 1.5 * IQR  # 下界
    upper_bound = Q3 + 1.5 * IQR  # 上界
    filtered_df = df[(df[column] >= lower_bound) & (df[column] <= upper_bound)]
    return filtered_df

# 对剩余数据应用IQR筛选
for column in columns_to_filter:
    remaining_data = filter_by_iqr(remaining_data, column)

# 合并优先保留数据和通过IQR筛选的数据
final_data = pd.concat([non_empty_abnormality, remaining_data])

final_data = final_data.sort_values(by='孕妇代码', ascending=True)
# 打印最终数据的行数
print(f"筛选完成后的数据共有 {len(final_data)} 行。")

final_data.to_excel('第四问.xlsx', index=False)