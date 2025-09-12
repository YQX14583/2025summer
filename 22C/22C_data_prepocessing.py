import pandas as pd

# ==== 配置文件名 ====
file = '22年C题/附件.xlsx'

# ==== 1. 处理表单1（保持空白） ====
df1 = pd.read_excel(file,sheet_name="表单1", keep_default_na=True)

# ==== 2. 处理表单2 ====
df2 = pd.read_excel(file,sheet_name="表单2", keep_default_na=True)
df2.fillna(0, inplace=True)

# 自动识别成分列（数值型列）
component_cols_2 = df2.select_dtypes(include=['number']).columns.tolist()

# 计算总和
df2['成分和'] = df2[component_cols_2].sum(axis=1)

# 筛选有效数据
df2_clean = df2[(df2['成分和'] >= 85) & (df2['成分和'] <= 105)]

# ==== 3. 处理表单3 ====
df3 = pd.read_excel(file,sheet_name="表单3", keep_default_na=True)
df3.fillna(0, inplace=True)

# 自动识别成分列（数值型列）
component_cols_3 = df3.select_dtypes(include=['number']).columns.tolist()

# 计算总和
df3['成分和'] = df3[component_cols_3].sum(axis=1)

# 筛选有效数据
df3_clean = df3[(df3['成分和'] >= 85) & (df3['成分和'] <= 105)]

# ==== 4. 导出到一个Excel文件，三个sheet ====
with pd.ExcelWriter('处理后数据.xlsx') as writer:
    df1.to_excel(writer, sheet_name='表单1_clean', index=False)
    df2_clean.to_excel(writer, sheet_name='表单2_clean', index=False)
    df3_clean.to_excel(writer, sheet_name='表单3_clean', index=False)