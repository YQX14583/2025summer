import pandas as pd
import gurobipy as gp
from gurobipy import GRB

# 读取数据
file1 = '附件1.xlsx'
data1 = pd.read_excel(file1, sheet_name='乡村的现有耕地')
data2 = pd.read_excel(file1, sheet_name='乡村种植的农作物')

file2 = '附件2.xlsx'
data3 = pd.read_excel(file2, sheet_name='2023年的农作物种植情况')
data4 = pd.read_excel(file2, sheet_name='2023年统计的相关数据')

# 大M常数
M = 100000

# 地块面积
S = data1['地块面积/亩'].tolist()
J = len(S)  # 地块数量

# 时间范围和季节
T = 7  # 2024-2030年
K = 2  # 季节数量（第一季、第二季）

# 作物类型标识（豆类作物为1，其他为0）
I_k = data2['作物类型'].apply(lambda x: 1 if '豆类' in str(x) else 0).tolist()
I = len(I_k)  # 作物数量

# 价格数据（根据图片中的价格范围整理）
Price = [
    3.25, 7.5, 8.25, 7, 6.75, 3.5, 3, 6.75, 6, 7.5, 40, 1.5, 3.25, 8.5, 3.5, 7, 8, 6.75, 6.5,
    3.75, 6.25, 5.5, 5.75, 5.25, 5.5, 6.5, 5, 5.75, 7, 5.25, 7.25, 4.5, 4.5, 4, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 9.6, 8.1, 7.8, 4.5, 7.5, 6.6, 6.9, 6.8, 6.6, 7.8, 6, 6.9,
    8.4, 6.3, 8.7, 5.4, 5.4, 4.8, 2.5, 2.5, 3.25, 57.5, 19, 16, 100
]

# 预期销售量
Request = [
    [57000, 21850, 22400, 33040, 9875, 170840, 132750, 71400, 30000, 12500, 1500, 35100, 36000, 14000, 10000, 21000,
     36480, 26880, 6480, 30000, 35400, 43200, 0, 1800, 3600, 4050, 4500, 34400, 9000, 1500, 1200, 3600, 1800, 0, 0, 0,
     0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 810, 2160, 900, 810, 0, 0, 0, 1080, 4050, 1350, 0,
     0, 0, 1800, 150000, 100000, 36000, 9000, 7200, 18000, 4200]
]

# 读取成本和产量数据（假设有这些文件）
df1 = pd.read_excel('cost.xlsx', sheet_name='第一季')
df2 = pd.read_excel('cost.xlsx', sheet_name='第二季')
Cost1 = df1.values.transpose()
Cost2 = df2.values.transpose()
Cost = (Cost1, Cost2)

df3 = pd.read_excel('Produce.xlsx', sheet_name='第一季')
df4 = pd.read_excel('Produce.xlsx', sheet_name='第二季')
Produce1 = df3.values.transpose()
Produce2 = df4.values.transpose()
Produce = (Produce1, Produce2)

# 创建模型
model = gp.Model("Crop_Planting")

# 决策变量
X = model.addVars(T, I, J, K, vtype=GRB.CONTINUOUS, name="X")  # 种植面积
Y = model.addVars(T, I, J, K, vtype=GRB.BINARY, name="Y")  # 是否种植
Z = model.addVars(T, I, K, vtype=GRB.CONTINUOUS, name="Z")  # 销售量
Z_rice = model.addVars(T, range(27, 35), vtype=GRB.BINARY, name="Z_Rice")  # 水稻种植指示

# 目标函数：最大化利润
model.setObjective(
    gp.quicksum(Price[i] * Z[t, i, k] - gp.quicksum(Cost[i][j][k] * X[t, i, j, k] for j in range(J))
                for t in range(T) for i in range(I) for k in range(K)),
    GRB.MAXIMIZE
)

# 约束1: 销量不超过作物总产量
model.addConstrs(
    (Z[t, i, k] <= gp.quicksum(Produce[i][j][k] * X[t, i, j, k] for j in range(J))
     for t in range(T) for i in range(I) for k in range(K)),
    name="Production_Limit"
)

# 约束2: 销量不超过预期需求量
model.addConstrs(
    (Z[t, i, k] <= Request[i][k] for t in range(T) for i in range(I) for k in range(K)),
    name="Demand_Limit"
)

# 约束3: 是否种植该作物的关联约束
model.addConstrs(
    (X[t, i, j, k] <= M * Y[t, i, j, k]
     for t in range(T) for i in range(I) for j in range(J) for k in range(K)),
    name="X_UpperBound_Y"
)

model.addConstrs(
    (X[t, i, j, k] >= 0.01 * Y[t, i, j, k]
     for t in range(T) for i in range(I) for j in range(J) for k in range(K)),
    name="X_LowerBound_Y"
)

# 约束4: 每个地块每季种植总面积不超过地块面积
for t in range(T):
    for i in range(I):
        for j in range(J):
            model.addConstr(
                gp.quicksum(X[t, i, j, k] for k in range(K)) <= S[j],
                name=f"Area_{t}_{i}_{j}"
            )

# 约束5: 豆类种植约束（前两年）
model.addConstrs(
    (gp.quicksum(X[t, i, j, k] * I_k[k] for t in range(2) for i in range(I) for k in range(K)) >= S[j]
     for j in range(J)),
    name="Legume_First_Two_Years"
)

# 约束6: 每三年至少种植一次豆类
for j in range(J):
    for t in range(T - 2):
        model.addConstr(
            gp.quicksum(X[tt, i, j, k] * I_k[k] for tt in range(t, t + 3) for i in range(I) for k in range(K)) >= S[j],
            name=f"Legume_{j}_{t}"
        )

# 约束7: 不能连续种植同种作物
model.addConstrs(
    (X[t, i, j, k] * X[t, i + 1, j, k] <= S[j]
     for t in range(T) for j in range(J) for k in range(K) for i in range(I - 1)),
    name="No_Consecutive_Planting"
)

model.addConstrs(
    (X[t, i + 1, j, k] * X[t + 1, i, j, k] <= S[j]
     for t in range(T - 1) for j in range(J) for k in range(K) for i in range(I - 1)),
    name="No_Consecutive_Planting_Cross"
)

# 约束8: 每个地块每季最多种植3种作物
p = 3
model.addConstrs(
    (gp.quicksum(Y[t, i, j, k] for k in range(K)) <= p
     for t in range(T) for i in range(I) for j in range(J)),
    name="Max_Three_Crops"
)

# 约束9: 每种作物最多种在9块地上
q = 9
model.addConstrs(
    (gp.quicksum(Y[t, i, j, k] for j in range(J)) <= q
     for t in range(T) for i in range(I) for k in range(K)),
    name="Max_Nine_Plots_Per_Crop"
)

# 约束10: 粮食作物不能连续种植
model.addConstrs(
    (X[t, 0, j, k] + X[t + 1, 0, j, k] <= S[j]
     for t in range(T - 1) for j in range(J) for k in range(1, 16)),
    name="No_Consecutive_Years_For_Grain"
)

# 约束11: 编号为1-26的地块在第二季不种植任何作物
model.addConstrs(
    (X[t, i, j, k] == 0
     for t in range(T) for j in range(26) for k in range(K)),
    name="No_Planting_Second_Season_For_Lands_1_26"
)

# 约束12: 编号为1-26的地块不能种植编号为16-41的作物
model.addConstrs(
    (X[t, i, j, k] == 0
     for t in range(T) for i in range(I) for j in range(26) for k in range(15, 41)),
    name="No_Planting_Crops_16_41_On_Lands_1_26"
)

# 约束13: 编号为1-15的作物只能种植在编号为1-26的地块上
model.addConstrs(
    (X[t, i, j, k] == 0
     for t in range(T) for i in range(I) for j in range(26, J) for k in range(18)),
    name="No_Planting_Crops_1_15_On_Lands_27_54"
)

# 约束14: 水稻种植约束
model.addConstrs(
    (gp.quicksum(X[t, i, j, k] for i in range(I) for k in range(K) if k == 15) <= M * Z_rice[t, j]
     for t in range(T) for j in range(27, 35)),
    name="Rice_Planting_Only_Once"
)

# 约束15: 确保水稻只种植在单季
model.addConstrs(
    (gp.quicksum(X[t, i, j, 15] for i in range(I)) <= S[j]
     for t in range(T) for j in range(27, 35)),
    name="Single_Season_Rice"
)

# 约束16: 如果种植水稻，就不能种植第二季作物
model.addConstrs(
    (gp.quicksum(X[t, i, j, k] for k in range(K)) <= M * (1 - Z_rice[t, j])
     for t in range(T) for j in range(27, 35)),
    name="No_Second_Season_If_Rice"
)

# 约束17: 第一季作物17-34的种植约束
model.addConstrs(
    (gp.quicksum(X[t, 0, j, k] for k in range(16, 35)) == gp.quicksum(X[t, 0, j, k] for k in range(16, 35))
     for t in range(T) for j in range(27, 35)),
    name="First_Season_Crops_17_34"
)

# 约束18: 第二季作物35-37的种植约束
model.addConstrs(
    (gp.quicksum(X[t, 1, j, k] for k in range(34, 38)) == gp.quicksum(X[t, 1, j, k] for k in range(34, 38))
     for t in range(T) for j in range(27, 36)),
    name="Second_Season_Crops_35_37"
)

# 约束19: 作物35-37只能种植在编号为27-34的地块上
model.addConstrs(
    (X[t, i, j, k] == 0
     for t in range(T) for i in range(I) for j in range(26) for k in range(34, 38)),
    name="No_Planting_Crops_35_37_On_Lands_1_26"
)

# 约束20: 作物38-41只能种植在35-50号地块的第二季
model.addConstrs(
    (X[t, i, j, k] == 0
     for t in range(T) for j in range(35) for k in range(37, 41)),
    name="No_Planting_Crops_38_41_On_Lands_1_34"
)

model.addConstrs(
    (X[t, 0, j, k] == 0
     for t in range(T) for j in range(35, 51) for k in range(37, 41)),
    name="No_Planting_Crops_38_41_First_Season"
)

# 设置求解参数
model.setParam('MIPGap', 0.01)
model.setParam('TimeLimit', 3600)  # 1小时时间限制

# 求解模型
model.optimize()

# 输出结果
if model.status == GRB.OPTIMAL:
    print(f"最优解找到，目标函数值: {model.objVal}")

    # 收集种植方案
    results = []
    for t in range(T):
        for i in range(I):
            for j in range(J):
                for k in range(K):
                    if X[t, i, j, k].X > 0.001:  # 只输出种植面积大于0.001亩的
                        results.append({
                            '年份': 2024 + t,
                            '地块': j + 1,
                            '作物': i + 1,
                            '季节': '第一季' if k == 0 else '第二季',
                            '种植面积': X[t, i, j, k].X
                        })

    # 保存到Excel
    results_df = pd.DataFrame(results)
    results_df.to_excel('result_1.xlsx', index=False)
    print("结果已保存到 result_1.xlsx")

else:
    print("未找到最优解")
    print(f"求解状态: {model.status}")