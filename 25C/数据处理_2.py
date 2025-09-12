import pandas as pd

# 读取原始表
data = pd.read_excel("第四问.xlsx")

# 保存「染色体的非整倍体为空的行」到一个表
non_abnormal_data = data[data['染色体的非整倍体'].isna()]
non_abnormal_data.to_excel("normal_data.xlsx", index=False)
print(f"成功保存 非异常 数据至 normal_data.xlsx")

# 定义要筛选的异常类型列表
abnormal_types = ["T13", "T18", "T21"]

# 遍历每种异常类型
for abnormal in abnormal_types:
    # 筛选包含当前异常类型的行（注意使用字符串匹配方法）
    abnormal_data = data[data['染色体的非整倍体'].str.contains(abnormal, na=False)]

    # 保存到对应的表中
    filename = f"{abnormal}_data.xlsx"
    abnormal_data.to_excel(filename, index=False)
    print(f"成功保存 {abnormal} 数据至 {filename}")
