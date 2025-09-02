import pandas as pd
import numpy as np
import itertools
import random
import math
import statsmodels.api as sm
from statsmodels.tsa.statespace.sarimax import SARIMAX
from matplotlib import rcParams
import matplotlib.pyplot as plt
import warnings

warnings.filterwarnings('ignore')

# 设置中文字体
rcParams['font.sans-serif'] = ['SimHei']  # 黑体
rcParams['axes.unicode_minus'] = False    # 显示负号

def df_show_table(df, title=None, fontsize=10):
    fig, ax = plt.subplots(figsize=(len(df.columns) * 1.2, len(df) * 0.5 + 1))
    ax.axis('off')
    if title:
        plt.title(title, fontsize=14, fontweight="bold", pad=20)
    table = ax.table(cellText=df.values,
                     colLabels=df.columns,
                     cellLoc='center',
                     loc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(fontsize)
    table.scale(1.2, 1.2)
    plt.show()

def plot_forecast_lines(ts_dict, forecast_dict):
    """
    ts_dict: {品类: 历史销量 Series}（index 是日期）
    forecast_dict: {品类: 预测销量 Series}（index 是日期）
    """

    for cat in ts_dict.keys():
        ts = ts_dict[cat]
        forecast = forecast_dict[cat]

        plt.figure(figsize=(8, 4))
        # 实测历史数据（红）
        plt.plot(ts.index, ts.values, color='red', label='实测')
        # 预测未来数据（蓝）
        plt.plot(forecast.index, forecast.values, color='blue', label='预测')

        # 历史与预测分割线
        plt.axvline(ts.index[-1], color='black')

        plt.ylabel("Number")
        plt.xlabel("日期")
        plt.title(f"{cat} 销量预测折线图", fontsize=12, fontweight='bold')
        plt.legend()
        plt.tight_layout()
        plt.show()  # 直接显示，不保存

# ===== 数据加载 =====
def load_data():
    df_sales = pd.read_excel('23年C题/附件2.xlsx')
    df_info = pd.read_excel('23年C题/附件1.xlsx')
    df_wholesale = pd.read_excel('23年C题/附件3.xlsx')
    df_loss = pd.read_excel('23年C题/附件4.xlsx', sheet_name=1)
    df_wholesale = df_wholesale.rename(columns={'日期': '销售日期'})
    df_sales = pd.merge(df_sales, df_info[['单品编码','分类名称']], on='单品编码', how='left')
    df_wholesale = pd.merge(df_wholesale, df_info[['单品编码','分类名称']], on='单品编码', how='left')
    df_loss = pd.merge(df_loss, df_info[['单品编码','分类名称']], on='单品编码', how='left')
    return df_sales, df_wholesale, df_loss

# ===== 时间序列准备 =====
def prepare_time_series(df_sales):
    df_sales['销售日期'] = pd.to_datetime(df_sales['销售日期'])
    ts_dict = {}
    for cat, group in df_sales.groupby('分类名称'):
        ts = group.groupby('销售日期')['销量(千克)'].sum().asfreq('D').fillna(0)
        ts_dict[cat] = ts
    return ts_dict

# ===== SARIMA预测（小范围遍历） =====
def sarima_forecast(ts, steps=7, seasonal_period=7):
    best_aic = np.inf
    best_model = None
    for p,d,q in itertools.product(range(2), range(2), range(2)):
        for P,D,Q in itertools.product(range(2), range(2), range(2)):
            try:
                model = SARIMAX(ts, order=(p,d,q),
                                seasonal_order=(P,D,Q,seasonal_period),
                                enforce_stationarity=False,
                                enforce_invertibility=False)
                res = model.fit(disp=False)
                if res.aic < best_aic:
                    best_aic = res.aic
                    best_model = res
            except:
                continue
    return best_model.forecast(steps=steps)

# ===== 单位成本计算 =====
def calc_unit_cost(df_wholesale, df_loss):
    avg_wholesale = df_wholesale.groupby('分类名称')['批发价格(元/千克)'].mean()
    avg_loss = df_loss.groupby('分类名称')['损耗率(%)'].mean()
    return (avg_wholesale / (1 - avg_loss / 100)).to_dict()

# ===== 价格弹性回归系数 =====
def get_price_elasticity(df_sales, df_wholesale, df_loss):
    daily_sales = df_sales.groupby(['销售日期','分类名称']).agg({
        '销量(千克)':'sum',
        '销售单价(元/千克)':'mean'
    }).reset_index()
    avg_loss = df_loss.groupby('分类名称')['损耗率(%)'].mean().reset_index()
    avg_wholesale = df_wholesale.groupby(['销售日期','分类名称'])['批发价格(元/千克)'].mean().reset_index()
    merged = pd.merge(daily_sales, avg_wholesale, on=['销售日期','分类名称'], how='left')
    merged = pd.merge(merged, avg_loss, on='分类名称', how='left')
    merged['单位成本'] = merged['批发价格(元/千克)'] / (1 - merged['损耗率(%)']/100)
    beta_dict = {}
    for cat, group in merged.groupby('分类名称'):
        X = sm.add_constant(group[['销售单价(元/千克)']])
        y = group['销量(千克)']
        model = sm.OLS(y, X).fit()
        beta0 = model.params['const']
        beta1 = model.params['销售单价(元/千克)']
        beta_dict[cat] = (beta0, beta1)
    return beta_dict

# ===== 利润计算 =====
def profit_given_price(price_dict, beta_dict, unit_cost):
    total_profit = 0
    for cat, prices in price_dict.items():
        beta0, beta1 = beta_dict[cat]
        Cu = unit_cost[cat]
        for price in prices:
            qty = max(0, beta0 + beta1 * price)
            total_profit += (price - Cu) * qty
    return total_profit

# ===== 模拟退火 =====
def simulated_annealing(beta_dict, unit_cost, days=7, init_temp=1000, cool_rate=0.95, iter_per_temp=30):
    price_dict = {cat: [unit_cost[cat] * 1.3] * days for cat in beta_dict.keys()}
    best_price_dict = price_dict.copy()
    best_profit = profit_given_price(price_dict, beta_dict, unit_cost)
    T = init_temp
    while T > 1:
        for _ in range(iter_per_temp):
            new_price_dict = {cat: prices.copy() for cat, prices in price_dict.items()}
            rnd_cat = random.choice(list(new_price_dict.keys()))
            day_idx = random.randint(0, days-1)
            change = random.uniform(-0.5,0.5)
            new_price_dict[rnd_cat][day_idx] = max(unit_cost[rnd_cat]*1.05, price_dict[rnd_cat][day_idx] + change)
            new_profit = profit_given_price(new_price_dict, beta_dict, unit_cost)
            delta = new_profit - best_profit
            if delta > 0 or math.exp(delta/T) > random.random():
                price_dict = new_price_dict
                if new_profit > best_profit:
                    best_price_dict = new_price_dict
                    best_profit = new_profit
        T *= cool_rate
    return best_price_dict

# ===== 主流程 =====
def main():
    df_sales, df_wholesale, df_loss = load_data()
    ts_dict = prepare_time_series(df_sales)
    unit_cost = calc_unit_cost(df_wholesale, df_loss)
    beta_dict = get_price_elasticity(df_sales, df_wholesale, df_loss)

    # ---- 预测未来一周销量 ----
    forecast_dict = {}
    for cat, ts in ts_dict.items():
        forecast = sarima_forecast(ts, steps=7, seasonal_period=7)
        forecast_dict[cat] = pd.Series(forecast.values,
                                       index=pd.date_range(ts.index[-1] + pd.Timedelta(days=1), periods=7))
    # plot_forecast_lines(ts_dict, forecast_dict)

    # ---- 表1：未来一周销量预测 ----
    dates = pd.date_range(start="2023-07-01", periods=7)
    forecast_table = pd.DataFrame({"日期": dates.date})
    for cat, ts in ts_dict.items():
        forecast = sarima_forecast(ts, steps=7, seasonal_period=7)
        forecast_table[cat] = forecast.values
    forecast_table = forecast_table.round(2)
    print("\n=== 表1: 未来一周各蔬菜品类日销量预测(kg) ===")
    print(forecast_table.to_string(index=False))

    # ---- 价格优化 ----
    best_price_dict = simulated_annealing(beta_dict, unit_cost)

    # ---- 表2：日补货量与定价 ----
    result_rows = {"日期": dates.date}
    for cat in best_price_dict.keys():
        beta0, beta1 = beta_dict[cat]
        prices = []
        qtys = []
        for p in best_price_dict[cat]:
            qty = max(0, beta0 + beta1 * p)
            prices.append(round(p,2))
            qtys.append(round(qty,3))
        result_rows[f"{cat}_补货量"] = qtys
        result_rows[f"{cat}_定价"] = prices
    result_df = pd.DataFrame(result_rows)
    print("\n=== 表2: 未来一周各蔬菜品类日补货量(kg)与定价策略(元/kg) ===")
    print(result_df.to_string(index=False))

    # 保留两位小数
    result_df = result_df.round(2)

    # 拆成两部分
    first_group = ['日期',
                   '花菜类_补货量', '花菜类_定价',
                   '食用菌_补货量', '食用菌_定价',
                   '花叶类_补货量', '花叶类_定价']

    second_group = ['日期',
                    '辣椒类_补货量', '辣椒类_定价',
                    '茄类_补货量', '茄类_定价',
                    '水生根茎类_补货量', '水生根茎类_定价']

    df_first = result_df[first_group]
    df_second = result_df[second_group]

    df_show_table(forecast_table, title="表1: 未来一周各蔬菜品类日销量预测(kg)", fontsize=9)

    # 显示第一个大表
    df_show_table(df_first, title="表2-上：未来一周各蔬菜品类日补货量(kg)与定价策略（第一部分）", fontsize=9)

    # 显示第二个大表
    df_show_table(df_second, title="表2-下：未来一周各蔬菜品类日补货量(kg)与定价策略（第二部分）", fontsize=9)

    # ===== 计算一周最大收益 =====
    total_profit = 0
    for cat in best_price_dict.keys():
        beta0, beta1 = beta_dict[cat]
        Cu = unit_cost[cat]
        for p in best_price_dict[cat]:
            qty = max(0, beta0 + beta1 * p)
            total_profit += (p - Cu) * qty

    print(f"\n一周最大收益：{total_profit:.2f} 元")

if __name__ == "__main__":
    main()
