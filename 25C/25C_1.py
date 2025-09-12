import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from statsmodels.formula.api import mixedlm
from statsmodels.nonparametric.smoothers_lowess import lowess
import warnings

warnings.filterwarnings('ignore')

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False


# 画BMI和Y关系的平滑曲线图（单线）
def draw_bmi_smooth_curve(data_frame, model_result, smooth_frac=0.12):
    temp_df = data_frame[['BMI', 'y_chromosome']].copy()
    temp_df['predicted_y'] = model_result.fittedvalues
    temp_df = temp_df.dropna().sort_values('BMI')

    smoothed_data = lowess(endog=temp_df['predicted_y'], exog=temp_df['BMI'],
                           frac=smooth_frac, it=0, return_sorted=True)
    x_vals, y_vals = smoothed_data[:, 0], smoothed_data[:, 1]

    plt.figure(figsize=(8, 6))
    plt.scatter(temp_df['BMI'], temp_df['y_chromosome'], s=18, alpha=0.25,
                color='steelblue', label='实际观测点')
    plt.plot(x_vals, y_vals, color='crimson', lw=2.2,
             label='模型拟合线（平滑后）')
    plt.xlabel("身体质量指数(BMI)")
    plt.ylabel("Y染色体含量（比例值）")
    plt.title("BMI与Y染色体含量关系图")
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.show()


# 读取数据并做预处理
FILE_PATH = r"第一问.xlsx"
raw_data = pd.read_excel(FILE_PATH)
# 重命名列
raw_data = raw_data.rename(columns={
    '孕妇代码': 'subject_id',
    '检测孕周': 'gestation_week',
    '孕妇BMI': 'BMI',
    'Y染色体浓度': 'y_chromosome'
})
raw_data = raw_data.dropna(subset=['subject_id', 'gestation_week', 'BMI', 'y_chromosome'])

# 转换为小数
if raw_data['y_chromosome'].max() > 1.5:
    print("注意：y值看起来是百分比格式，正在转换为小数...")
    raw_data['y_chromosome'] = raw_data['y_chromosome'] / 100

# 过滤掉异常数据点
raw_data = raw_data[(raw_data['gestation_week'] > 0) &
                    (raw_data['gestation_week'] < 45) &
                    (raw_data['BMI'] > 10) &
                    (raw_data['BMI'] < 60)]
# 对BMI做中心化处理
raw_data['BMI_centered'] = raw_data['BMI'] - raw_data['BMI'].mean()
print(f"处理后数据：总共{len(raw_data)}条记录，来自{raw_data['subject_id'].nunique()}名孕妇")

# 构建混合效应模型（带随机截距）
mixed_model = mixedlm("y_chromosome ~ gestation_week + BMI_centered + gestation_week:BMI_centered",
                      data=raw_data, groups=raw_data["subject_id"])
fitted_model = mixed_model.fit()
print("=== 模型拟合完毕 ===")

# 计算方差组分和ICC
random_intercept_var = fitted_model.cov_re.iloc[0, 0]
residual_var = fitted_model.scale
icc_value = random_intercept_var / (random_intercept_var + residual_var)

print("--- 方差分析结果 ---")
print(f"个体间差异 (τ²): {random_intercept_var:.6f}")
print(f"个体内差异 (σ²): {residual_var:.6f}")
print(f"组内相关性 (ICC): {icc_value:.3f}")
print("-------------------")

# 展示主要结果
coeffs = fitted_model.params
conf_intervals = fitted_model.conf_int()
p_vals = fitted_model.pvalues

# 计算变量间相关性
corr_data = raw_data[['y_chromosome', 'gestation_week', 'BMI']].copy()
corr_data.rename(columns={
    'y_chromosome': 'Y含量',
    'gestation_week': '孕周',
    'BMI': 'BMI指数'
}, inplace=True)
corr_result = corr_data.corr()

print("变量间相关系数:")
print(corr_result)

print("=== 混合模型详细结果 ===")
for var_name in coeffs.index:
    estimate = coeffs[var_name]
    ci_lower, ci_upper = conf_intervals.loc[var_name]
    p_val = p_vals[var_name]
    significance = "显著" if p_val < 0.05 else "不显著"
    print(f"变量: {var_name}")
    print(f"  系数值: {estimate:.4f}")
    print(f"  p值: {p_val:.4f} → {significance}")
    print(f"  95%置信范围: ({ci_lower:.4f}, {ci_upper:.4f})")

# 写出拟合的方程
intercept = coeffs["Intercept"]
coeff_t = coeffs["gestation_week"]
coeff_bmi = coeffs["BMI_centered"]
coeff_interaction = coeffs["gestation_week:BMI_centered"]
model_equation = f"y = {intercept:.4f} + {coeff_t:.4f}*周数 + {coeff_bmi:.4f}*BMI中心化 + {coeff_interaction:.4f}*周数*BMI中心化 + 个体效应 + 随机误差"
print("拟合方程（含随机截距）：")
print(model_equation)

# 可视化模型拟合情况
raw_data["fitted_values"] = fitted_model.fittedvalues
plot_data = raw_data[["gestation_week", "y_chromosome", "fitted_values"]].dropna().sort_values("gestation_week")
smoothed_fit = lowess(endog=plot_data["fitted_values"], exog=plot_data["gestation_week"],
                      frac=0.15, it=0, return_sorted=True)
weeks_smoothed, y_smoothed = smoothed_fit[:, 0], smoothed_fit[:, 1]

# 画图
plt.figure(figsize=(8, 6))
sns.scatterplot(x="gestation_week", y="y_chromosome", data=plot_data,
                alpha=0.4, label="实际值", color="mediumblue")
plt.plot(weeks_smoothed, y_smoothed, color="darkred", lw=2, label="模型拟合线")
plt.xlabel("孕周（周）")
plt.ylabel("Y染色体含量")
plt.title("孕周与Y染色体含量关系拟合图")
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
plt.show()
draw_bmi_smooth_curve(raw_data, fitted_model, smooth_frac=0.12)

# 检查残差
raw_data["residuals"] = raw_data["y_chromosome"] - raw_data["fitted_values"]

# 残差散点图
plt.figure(figsize=(7, 5))
sns.scatterplot(x="fitted_values", y="residuals", data=raw_data, alpha=0.5)
plt.axhline(0, color="red", linestyle="--")
plt.xlabel("拟合值")
plt.ylabel("残差")
plt.title("残差分布散点图")
plt.grid(alpha=0.3)
plt.tight_layout()
plt.show()

# 残差直方图
plt.figure(figsize=(7, 5))
sns.histplot(raw_data["residuals"], kde=True)
plt.xlabel("残差")
plt.title("残差分布直方图")
plt.grid(alpha=0.3)
plt.tight_layout()
plt.show()

# 计算模型评价指标
actual_y = raw_data["y_chromosome"]
predicted_y = fitted_model.fittedvalues
residual_sum_sq = ((actual_y - predicted_y) ** 2).sum()
total_sum_sq = ((actual_y - actual_y.mean()) ** 2).sum()
r_squared = 1 - residual_sum_sq / total_sum_sq
rmse_val = np.sqrt(((actual_y - predicted_y) ** 2).mean())
print(f"=== 模型评价 ===")
print(f"决定系数 R²: {r_squared:.4f} → 模型解释了 {r_squared * 100:.2f}% 的变异")
print(f"均方根误差 RMSE: {rmse_val:.4f} → 平均误差约为 {rmse_val * 100:.2f}%")

# 画相关性热力图
plt.figure(figsize=(8, 6))
sns.heatmap(corr_result,
            annot=True,
            fmt='.3f',
            cmap='Reds',
            linewidths=0.5,
            vmax=1.2,
            cbar_kws={"orientation": "horizontal", "pad": 0.2})
plt.title('变量间相关性热力图', fontsize=16, pad=20)
plt.xticks(rotation=0, ha='center')
plt.yticks(rotation=0)
plt.tight_layout()
plt.show()
