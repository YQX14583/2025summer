import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import chi2_contingency
import os

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'SimSun']
plt.rcParams['axes.unicode_minus'] = False

INPUT_FILE = '处理后数据.xlsx'
SHEET_NAME = '表单1_clean'
WEATHER_COL = '表面风化'
OUT_EXCEL = '问题1第一部分分析结果.xlsx'
OUT_DIR = '图表输出'
os.makedirs(OUT_DIR, exist_ok=True)

def find_positive_weather_col(columns):
    cols_str = [str(c) for c in columns]
    if '风化' in cols_str:
        return columns[cols_str.index('风化')]
    for key in ['是', '有风化', '有', 'Yes', 'yes', 'Y', '1', 'True', 'true']:
        if key in cols_str:
            return columns[cols_str.index(key)]
    if any('无' in c for c in cols_str) and len(columns) >= 1:
        for c in columns:
            if '无' not in str(c):
                return c
    return columns[-1]

def compute_tables(df, group_col, weather_col):
    sub = df[[group_col, weather_col]].dropna()
    counts_df = pd.crosstab(sub[group_col], sub[weather_col])
    rate_df = pd.crosstab(sub[group_col], sub[weather_col], normalize='index') * 100
    cols = list(counts_df.columns)
    ordered = []
    for name in ['无风化', '风化', '否', '是']:
        if name in cols:
            ordered.append(name)
    ordered += [c for c in cols if c not in ordered]
    counts_df = counts_df.reindex(columns=ordered)
    rate_df = rate_df.reindex(columns=ordered)
    return counts_df, rate_df

def chi2_test(counts_df):
    chi2, p, dof, expected = chi2_contingency(counts_df)
    expected_df = pd.DataFrame(expected, index=counts_df.index, columns=counts_df.columns)
    warning = (expected_df.values < 5).any()
    return chi2, p, dof, expected_df, warning


def dual_axis_plot(counts_df, rate_df, title, xlabel, outfile):
    """
    双轴图：
    左轴 柱状图(无风化/风化数量) + 右轴 折线图(风化率)
    """
    if counts_df.empty or rate_df.empty:
        print(f"[警告] {title} 数据为空，跳过绘图。")
        return

    pos_col = find_positive_weather_col(rate_df.columns)

    fig, ax1 = plt.subplots(figsize=(9, 5))

    # ====== 柱状图颜色设置 ======
    palette_colors = []
    for col in counts_df.columns:
        if "无风化" in str(col) or "否" in str(col):
            palette_colors.append('#5e90b8')  # 天蓝
        else:
            palette_colors.append('#eeb8c3')  # 橙色

    counts_df.plot(kind='bar', ax=ax1, color=palette_colors, edgecolor='black')
    ax1.set_ylabel('数量')
    ax1.set_xlabel(xlabel)
    ax1.set_title(title)
    ax1.legend(title='风化情况', bbox_to_anchor=(1.02, 1), loc='upper left')

    # ====== 风化率折线 ======
    ax2 = ax1.twinx()
    ax2.plot(counts_df.index, rate_df[pos_col].values,
             color='#E77C8E', marker='o', linewidth=2, label='风化率')
    ax2.set_ylabel('风化率(%)', color='black')
    ax2.tick_params(axis='y', colors='black')

    # 数值标注
    for i, val in enumerate(rate_df[pos_col].values):
        ax2.text(i, val + 1, f"{val:.1f}%", color='black', ha='center')

    fig.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, outfile), dpi=300, bbox_inches='tight')
    plt.close(fig)


def generate_conclusion(dim_name, counts_df, rate_df, chi2, p, pos_col):
    conclusion = f"【{dim_name} 与风化关系分析】\n"
    if p < 0.05:
        conclusion += f"- 卡方检验显著 (χ²={chi2:.3f}, p={p:.4f})，说明 {dim_name} 与风化情况显著相关。\n"
        max_cat = rate_df[pos_col].idxmax()
        min_cat = rate_df[pos_col].idxmin()
        conclusion += f"- 风化率最高的 {dim_name} 是 {max_cat}，风化率为 {rate_df[pos_col].max():.1f}%。\n"
        conclusion += f"- 风化率最低的 {dim_name} 是 {min_cat}，风化率为 {rate_df[pos_col].min():.1f}%。\n"
    else:
        conclusion += f"- 卡方检验不显著 (χ²={chi2:.3f}, p={p:.4f})，数据未能显著证明 {dim_name} 与风化情况相关。\n"
    return conclusion

if __name__ == '__main__':
    df1 = pd.read_excel(INPUT_FILE, sheet_name=SHEET_NAME)
    needed_cols = ['类型', '纹饰', '颜色', WEATHER_COL]
    for col in needed_cols:
        if col not in df1.columns:
            raise ValueError(f"缺少必要列: {col}")

    dimensions = [
        ('类型', '不同类型的风化情况与风化率', '类型', '类型_双轴图.png'),
        ('纹饰', '不同纹饰的风化情况与风化率', '纹饰', '纹饰_双轴图.png'),
        ('颜色', '不同颜色的风化情况与风化率', '颜色', '颜色_双轴图.png'),
    ]

    conclusions = []
    with pd.ExcelWriter(OUT_EXCEL) as writer:
        for dim_col, title, xlabel, png_name in dimensions:
            counts_df, rate_df = compute_tables(df1, dim_col, WEATHER_COL)
            counts_df.to_excel(writer, sheet_name=f'{dim_col}_数量')
            rate_df.to_excel(writer, sheet_name=f'{dim_col}_风化率')
            chi2, p, dof, expected_df, warn = chi2_test(counts_df)
            expected_df.to_excel(writer, sheet_name=f'{dim_col}_期望频数')
            pos_col = find_positive_weather_col(rate_df.columns)
            dual_axis_plot(counts_df, rate_df, title, xlabel, png_name)
            conc = generate_conclusion(dim_col, counts_df, rate_df, chi2, p, pos_col)
            conclusions.append(conc)

        pd.DataFrame({
            '变量': [c.split("与")[0].replace("【","") for c in conclusions],
            '结论': conclusions
        }).to_excel(writer, sheet_name='关系分析结论', index=False)

    print("统计表、风化率、卡方检验、结论均已生成")
    print("\n".join(conclusions))
