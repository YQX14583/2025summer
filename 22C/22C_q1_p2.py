import pandas as pd
import os
import seaborn as sns
import matplotlib.pyplot as plt
from scipy.stats import ttest_ind
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# 输出目录
OUT_DIR = os.path.join("图表输出", "第一问第二部分")
os.makedirs(OUT_DIR, exist_ok=True)

# ------------ 数据读取 ------------
f = '处理后数据.xlsx'
df1 = pd.read_excel(f, sheet_name='表单1_clean')
df2 = pd.read_excel(f, sheet_name='表单2_clean')
df3 = pd.read_excel(f, sheet_name='表单3_clean')

# 统一文物编号为字符串并去除空格
df1['文物编号'] = df1['文物编号'].astype(str).str.strip()
df2['文物编号'] = df2['文物编号'].astype(str).str.strip()
df3['文物编号'] = df3['文物编号'].astype(str).str.strip()

# 合并成分表
df_all_comp = pd.concat([df2, df3], ignore_index=True)

# 打印交集情况
ids1 = set(df1['文物编号'])
ids2 = set(df_all_comp['文物编号'])
print(f"表单1编号数: {len(ids1)} | 表单2+3编号数: {len(ids2)} | 交集: {len(ids1 & ids2)}")
if len(ids1 & ids2) == 0:
    raise ValueError("合并失败，文物编号没有交集，请检查。")

# 合并类型信息
df_all = pd.merge(df_all_comp, df1[['文物编号', '类型']], on='文物编号', how='inner')
print(f"合并成功，样本数: {len(df_all)}")

# 成分列
comp_cols = [c for c in df_all.columns if c not in ['文物编号', '类型']]

# 将成分列转为数值
for col in comp_cols:
    df_all[col] = pd.to_numeric(df_all[col], errors='coerce')

# ------------ 显著性分析（t检验） ------------
results = []
for col in comp_cols:
    data_h = df_all[df_all['类型'] == '高钾'][col].dropna()
    data_l = df_all[df_all['类型'] == '铅钡'][col].dropna()
    if len(data_h) > 1 and len(data_l) > 1:
        t_val, p_val = ttest_ind(data_h, data_l, equal_var=False)
        results.append((col, t_val, p_val))

if results:
    sig_results = [(c, t, p) for c, t, p in results if p < 0.05]
    if sig_results:
        print("\n显著差异成分 (p < 0.05):")
        for c, t, p in sig_results:
            print(f"  {c}: t={t:.3f}, p={p:.4f}")
    else:
        print("\n没有显著差异成分")
else:
    print("\n没有可做t检验的成分列")

# 可视化显著差异成分箱线图
if results and sig_results:
    sig_cols = [c for c, _, _ in sig_results]
    plt.figure(figsize=(12, 6))
    melt_df = df_all.melt(id_vars=['类型'], value_vars=sig_cols,
                          var_name='成分', value_name='含量')
    sns.boxplot(data=melt_df, x='成分', y='含量', hue='类型')
    plt.title('显著差异成分的箱线图')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, '显著差异成分_箱线图.png'), dpi=300)
    plt.close()

# ------------ 建模（随机森林） ------------
X = df_all[comp_cols].fillna(0)
y = df_all['类型']
if y.nunique() >= 2:
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y)
    clf = RandomForestClassifier(n_estimators=200, random_state=42)
    clf.fit(X_train, y_train)
    y_pred = clf.predict(X_test)
    print("\n=== 分类模型评估 ===")
    print(classification_report(y_test, y_pred))
    print("混淆矩阵:")
    print(confusion_matrix(y_test, y_pred))

    # 特征重要性
    feat_imp = pd.DataFrame({'成分': comp_cols, '重要性': clf.feature_importances_})
    feat_imp.sort_values(by='重要性', ascending=False, inplace=True)
    print("\nTop10 重要成分:")
    print(feat_imp.head(10))

    # 绘制Top10重要性图
    plt.figure(figsize=(8, 5))
    sns.barplot(data=feat_imp.head(10), x='重要性', y='成分', palette='viridis')
    plt.title('Top10 成分的重要性')
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, 'Top10_特征重要性.png'), dpi=300)
    plt.close()
else:
    print("\n只有一种类型，无法建模")

# ------------ 相关性热力图 ------------
corr_df = df_all[comp_cols + ['类型']].copy()
corr_df['类型'] = corr_df['类型'].map({'高钾': 1, '铅钡': 0})
plt.figure(figsize=(10, 8))
sns.heatmap(corr_df.corr(), cmap='coolwarm', center=0)
plt.title('成分与类型的相关性热力图')
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, '成分_类型_相关性热力图.png'), dpi=300)
plt.close()

print(f"\n✅ 分析完成，所有图已保存到：{OUT_DIR}")
