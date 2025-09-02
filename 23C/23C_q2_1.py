import pandas as pd
import numpy as np
import statsmodels.api as sm
import matplotlib.pyplot as plt
from matplotlib import rcParams


# 设置中文字体
rcParams['font.sans-serif'] = ['SimHei']  # 黑体
rcParams['axes.unicode_minus'] = False    # 显示负号

def prepare_pricing_data_correct(df_merged, df_wholesale, df_loss, df_info):
    """
    准备定价分析数据（计算成本加成定价）
    """
    # 按日期和品类聚合销量和售价
    daily_data = df_merged.groupby(['销售日期', '分类名称']).agg({
        '销量(千克)': 'sum',
        '销售单价(元/千克)': 'mean'
    }).reset_index()

    # 读取附件4第二个工作表（单品损耗率）
    df_loss = pd.read_excel('23年C题/附件4.xlsx', sheet_name=1)
    loss_with_category = pd.merge(df_loss, df_info[['单品编码', '分类名称']],
                                  on='单品编码', how='left')
    loss_agg = loss_with_category.groupby('分类名称')['损耗率(%)'].mean().reset_index()

    # 批发数据与商品信息合并，获取分类名称
    df_wholesale = df_wholesale.rename(columns={'日期': '销售日期'})
    wholesale_with_category = pd.merge(df_wholesale, df_info[['单品编码', '分类名称']],
                                       on='单品编码', how='left')

    # 按日期和分类计算平均批发价
    wholesale_agg = wholesale_with_category.groupby(['销售日期', '分类名称'])['批发价格(元/千克)'].mean().reset_index()

    # 合并数据
    merged_data = pd.merge(daily_data, wholesale_agg, on=['销售日期', '分类名称'], how='left')
    merged_data = pd.merge(merged_data, loss_agg, on='分类名称', how='left')

    # 单位成本
    merged_data['单位成本'] = merged_data['批发价格(元/千克)'] / (1 - merged_data['损耗率(%)'] / 100)

    # 加成率(%) = (销售单价 / 单位成本 - 1) * 100
    merged_data['加成率(%)'] = (merged_data['销售单价(元/千克)'] / merged_data['单位成本'] - 1) * 100

    # 成本加成定价（单位成本 × (1 + 加成率)）
    merged_data['成本加成定价'] = merged_data['单位成本'] * (1 + merged_data['加成率(%)'] / 100)

    return merged_data


def build_pricing_model_simple(data, category):
    """
    一元线性回归：销量 ~ 成本加成定价
    """
    cat_data = data[data['分类名称'] == category].copy()
    if len(cat_data) < 5:
        return None, None

    X = cat_data[['成本加成定价']]
    X = sm.add_constant(X)  # 截距
    y = cat_data['销量(千克)']

    mask = ~(X.isna().any(axis=1) | y.isna())
    X, y = X[mask], y[mask]
    if len(X) < 5:
        return None, None

    model = sm.OLS(y, X).fit()
    return model, cat_data


def analyze_pricing_simple(data):
    """
    分析每个品类的 成本加成定价 对销量的影响
    """
    for category in data['分类名称'].unique():
        model, cat_data = build_pricing_model_simple(data, category)
        if model is None:
            continue

        coef_price = model.params['成本加成定价']
        pval_price = model.pvalues['成本加成定价']
        r2 = model.rsquared

        # 输出线性表达式
        print(f"\n品类: {category}")
        print(f"线性表达式: 销量 = {model.params['const']:.4f} "
              f"+ {coef_price:.4f} × 成本加成定价")
        print(f"成本加成定价系数: {coef_price:.4f}, p值={pval_price:.4f}, R²={r2:.4f}")

        # 关键发现
        if pval_price < 0.05:
            if coef_price > 0:
                print("- 结论: 成本加成定价↑ → 销量↑ → 可溢价")
            else:
                print("- 结论: 成本加成定价↑ → 销量↓ → 价格敏感，应薄利多销")
        else:
            print("- 结论: 成本加成定价对销量无显著影响 → 稳定定价")

        # 可选绘图
        plot_price_vs_sales(cat_data, category, coef_price, model.params['const'])


def plot_price_vs_sales(data, category, coef, intercept):
    """
    绘制 成本加成定价 vs 销量 散点+回归线
    """
    plt.figure(figsize=(10, 6))
    plt.scatter(data['成本加成定价'], data['销量(千克)'],
                alpha=0.6, s=50, label='实际数据', color='steelblue')

    x_range = np.linspace(data['成本加成定价'].min(),
                          data['成本加成定价'].max(), 100)
    y_pred = intercept + coef * x_range
    plt.plot(x_range, y_pred, 'r-', linewidth=2, label='回归线')

    plt.xlabel('成本加成定价 (元/千克)', fontsize=12, fontweight='bold')
    plt.ylabel('销量 (千克)', fontsize=12, fontweight='bold')
    plt.title(f'{category}', fontsize=14, fontweight='bold')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()


def main_correct():
    """
    主函数：成本加成定价 vs 销量 分析
    """
    print("开始进行销量-成本加成定价分析...")

    # 加载数据
    df_sales = pd.read_excel('23年C题/附件2.xlsx')
    df_info = pd.read_excel('23年C题/附件1.xlsx')
    df_wholesale = pd.read_excel('23年C题/附件3.xlsx')

    # 合并销售数据和商品信息
    df_merged = pd.merge(df_sales, df_info, on='单品编码', how='left')

    # 准备数据
    pricing_data = prepare_pricing_data_correct(df_merged, df_wholesale, None, df_info)

    print("数据准备完成，开始分析...")
    analyze_pricing_simple(pricing_data)


if __name__ == "__main__":
    main_correct()
