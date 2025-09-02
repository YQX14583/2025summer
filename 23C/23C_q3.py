import pandas as pd
import numpy as np
import random
import math
import statsmodels.api as sm
import warnings
warnings.filterwarnings('ignore')
from matplotlib import rcParams

import matplotlib.pyplot as plt

# 设置中文字体
rcParams['font.sans-serif'] = ['SimHei']  # 黑体
rcParams['axes.unicode_minus'] = False    # 显示负号

# 绘制表格
def plot_results_table(df_result, total_profit):
    fig, ax = plt.subplots(figsize=(10, len(df_result) * 0.4 + 2))
    ax.axis('off')
    ax.axis('tight')

    # 添加总利润行
    df_display = df_result.copy()
    df_display.loc['合计'] = ["-", "-", "-", "-", round(df_display['收益(元)'].sum(), 2)]

    # 使用 matplotlib.table
    table = ax.table(
        cellText=df_display.reset_index().values,
        colLabels=["序号", "单品名称", "单位成本(元/kg)", "日补货量(kg)", "定价(元/kg)", "收益(元)"],
        cellLoc='center',
        loc='center'
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.2, 1.2)

    plt.title(f"2023-07-01 单品补货量与定价方案（总利润: {total_profit:.2f} 元）", fontsize=14, pad=20)
    plt.show()


# ===== 数据加载 =====
def load_data():
    df_sales = pd.read_excel('23年C题/附件2.xlsx')
    df_info = pd.read_excel('23年C题/附件1.xlsx')
    df_wholesale = pd.read_excel('23年C题/附件3.xlsx')
    df_loss = pd.read_excel('23年C题/附件4.xlsx', sheet_name=1)
    df_wholesale = df_wholesale.rename(columns={'日期': '销售日期'})
    df_sales = pd.merge(df_sales, df_info[['单品编码','单品名称','分类名称']], on='单品编码', how='left')
    df_wholesale = pd.merge(df_wholesale, df_info[['单品编码','单品名称','分类名称']], on='单品编码', how='left')
    df_loss = pd.merge(df_loss, df_info[['单品编码','单品名称','分类名称']], on='单品编码', how='left')
    return df_sales, df_wholesale, df_loss

# ===== 单位成本 =====
def calc_unit_cost(df_wholesale, df_loss):
    avg_wholesale = df_wholesale.groupby('单品编码')['批发价格(元/千克)'].mean()
    avg_loss = df_loss.groupby('单品编码')['损耗率(%)'].mean()
    return (avg_wholesale / (1 - avg_loss / 100)).to_dict()

# ===== 获取 β（按 SKU） =====
def get_price_elasticity(df_sales, df_wholesale, df_loss,
                         start_date="2023-06-24", end_date="2023-06-30"):
    df_sales['销售日期'] = pd.to_datetime(df_sales['销售日期'])
    df_wholesale['销售日期'] = pd.to_datetime(df_wholesale['销售日期'])

    sales_period = df_sales[(df_sales['销售日期'] >= start_date) & (df_sales['销售日期'] <= end_date)]

    # 全周期均值（补值用）
    avg_wholesale_all = df_wholesale.groupby('单品编码')['批发价格(元/千克)'].mean()
    avg_loss_all = df_loss.groupby('单品编码')['损耗率(%)'].mean()

    daily_sales = sales_period.groupby(['销售日期', '单品编码']).agg({
        '销量(千克)': 'sum',
        '销售单价(元/千克)': 'mean',
        '单品名称': 'first',
        '分类名称': 'first'
    }).reset_index()

    avg_wholesale_period = df_wholesale.groupby(['销售日期', '单品编码'])['批发价格(元/千克)'].mean().reset_index()
    merged = pd.merge(daily_sales, avg_wholesale_period, on=['销售日期','单品编码'], how='left')

    merged['批发价格(元/千克)'] = merged.apply(
        lambda r: avg_wholesale_all[r['单品编码']] if pd.isna(r['批发价格(元/千克)']) else r['批发价格(元/千克)'],
        axis=1
    )

    merged = pd.merge(merged, avg_loss_all.reset_index(), on='单品编码', how='left')
    merged['损耗率(%)'] = merged['损耗率(%)'].fillna(merged['单品编码'].map(avg_loss_all))
    merged['单位成本'] = merged['批发价格(元/千克)'] / (1 - merged['损耗率(%)'] / 100)

    beta_dict, avg_price_dict, name_map = {}, {}, {}
    for code, group in merged.groupby('单品编码'):
        if len(group) >= 2:
            X = sm.add_constant(group[['销售单价(元/千克)']], has_constant='add')
            y = group['销量(千克)']
            try:
                model = sm.OLS(y, X).fit()
                beta0 = model.params.get('const', y.mean())
                beta1 = model.params.get('销售单价(元/千克)', 0)
            except:
                beta0, beta1 = y.mean(), 0
        else:
            beta0, beta1 = group['销量(千克)'].mean(), 0
        beta_dict[code] = (beta0, beta1)
        avg_price_dict[code] = group['销售单价(元/千克)'].mean()
        name_map[code] = (group['单品名称'].iloc[0], group['分类名称'].iloc[0])
    return beta_dict, avg_price_dict, name_map

# ===== 约束检查 =====
def check_constraints(price_dict, beta_dict, unit_cost,
                      min_items=27, max_items=33, min_qty_per_item=2.5,
                      min_total_qty=None, max_total_qty=None):
    sel_items = list(price_dict.keys())
    if not (min_items <= len(sel_items) <= max_items):
        return False
    total_qty = 0
    for code, prices in price_dict.items():
        beta0, beta1 = beta_dict[code]
        for p in prices:
            qty = max(beta0 + beta1 * p, min_qty_per_item)
            if p < unit_cost[code] * 1:  # 成本约束
                return False
            total_qty += qty
    if min_total_qty and total_qty < min_total_qty:
        return False
    if max_total_qty and total_qty > max_total_qty:
        return False
    return True

# ===== 利润计算 =====
def profit_given_price(price_dict, beta_dict, unit_cost, min_qty_per_item=2.5):
    total_profit = 0
    for code, prices in price_dict.items():
        beta0, beta1 = beta_dict[code]
        Cu = unit_cost[code]
        for price in prices:
            qty = max(beta0 + beta1 * price, min_qty_per_item)
            total_profit += (price - Cu) * qty
    return total_profit

# ===== 模拟退火（单日） =====
def simulated_annealing(beta_dict, avg_price_dict, unit_cost,
                        min_items=27, max_items=33, min_qty_per_item=2.5,
                        min_total_qty=None, max_total_qty=None):
    all_items = list(beta_dict.keys())
    max_items = min(max_items, len(all_items))
    min_items = min(min_items, max_items)

    # 初始解
    selected_items = random.sample(all_items, random.randint(min_items, max_items))
    price_dict = {code: [max(unit_cost[code]*1.1, avg_price_dict[code]*0.9)]
                  for code in selected_items}

    best_price_dict = price_dict.copy()
    best_profit = profit_given_price(price_dict, beta_dict, unit_cost, min_qty_per_item)
    T = 100
    cool_rate = 0.95

    while T > 1:
        for _ in range(50):
            new_price_dict = {c: prices.copy() for c, prices in price_dict.items()}
            rnd_code = random.choice(list(new_price_dict.keys()))
            change = random.uniform(-0.5, 0.5)
            new_price = new_price_dict[rnd_code][0] + change
            low_limit = max(unit_cost[rnd_code]*1.1, avg_price_dict[rnd_code]*0.8)
            # high_limit = avg_price_dict[rnd_code]*2.0
            # new_price_dict[rnd_code][0] = min(max(new_price, low_limit), high_limit)

            if check_constraints(new_price_dict, beta_dict, unit_cost,
                                 min_items, max_items, min_qty_per_item,
                                 min_total_qty, max_total_qty):
                new_profit = profit_given_price(new_price_dict, beta_dict, unit_cost, min_qty_per_item)
            else:
                new_profit = -1e9

            delta = new_profit - best_profit
            if delta > 0 or math.exp(delta/T) > random.random():
                price_dict = new_price_dict
                if new_profit > best_profit:
                    best_price_dict = new_price_dict
                    best_profit = new_profit
        T *= cool_rate

    return best_price_dict, best_profit

# ===== 主程序（只输出 7/1 一天） =====
def main():
    df_sales, df_wholesale, df_loss = load_data()
    unit_cost = calc_unit_cost(df_wholesale, df_loss)
    beta_dict, avg_price_dict, name_map = get_price_elasticity(df_sales, df_wholesale, df_loss)

    # 基于6/24–6/30算总补货量区间
    total_qtys = []
    for code in beta_dict.keys():
        beta0, beta1 = beta_dict[code]
        total_qtys.append(max(beta0 + beta1 * avg_price_dict[code], 2.5))
    avg_total = np.sum(total_qtys)

    # 跑优化
    best_price_dict, best_profit = simulated_annealing(
        beta_dict, avg_price_dict, unit_cost
    )

    # 生成结果表
    results = []
    for code, price_list in best_price_dict.items():
        beta0, beta1 = beta_dict[code]
        name, _ = name_map[code]
        p = price_list[0]
        qty = max(beta0 + beta1 * p, 2.5)
        cost = unit_cost[code]
        profit = (p - cost) * qty
        results.append([name, round(cost, 2), round(qty, 2), round(p, 2), round(profit, 2)])

    # 转 DataFrame，添加序号列
    df_result = pd.DataFrame(results, columns=['单品名称','单位成本(元/kg)','日补货量(kg)','定价(元/kg)','收益(元)'])
    df_result.index += 1  # 序号从1开始
    df_result.index.name = '序号'

    # 打印
    print("\n=== 2023-07-01 单品定价与补货量方案 ===")
    print(df_result)
    print(f"\n预计单日总利润: {best_profit:.2f} 元")

    plot_results_table(df_result, best_profit)

if __name__ == "__main__":
    main()
