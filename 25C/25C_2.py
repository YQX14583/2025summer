import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.svm import SVR
from sklearn.metrics import r2_score
from sklearn.model_selection import KFold
from sklearn.base import clone
import seaborn as sns

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False


# 提取每个孕妇最早达标的时间点
def get_first_reach_time(data):
    reach_records = []
    for pid, group in data.groupby('孕妇代码'):
        group = group.sort_values('检测孕周')
        weeks = group['检测孕周'].values
        concs = group['Y染色体浓度'].values
        bmi_val = group['孕妇BMI'].mean()
        first_reach = None
        for i, conc in enumerate(concs):
            if conc >= 0.04:
                first_reach = weeks[i]
                break
        if first_reach is not None and pd.notna(bmi_val):
            reach_records.append({
                'pid': pid,
                'bmi': bmi_val,
                'first_reach_week': first_reach
            })
    return pd.DataFrame(reach_records)


# 去除异常值
def remove_weird_values(reach_data, col='first_reach_week', min_week=8, max_week=25):
    Q1 = reach_data[col].quantile(0.25)
    Q3 = reach_data[col].quantile(0.75)
    IQR = Q3 - Q1
    lower = Q1 - 1.5 * IQR
    upper = Q3 + 1.5 * IQR
    cleaned = reach_data[
        (reach_data[col] >= max(lower, min_week)) &
        (reach_data[col] <= min(upper, max_week))
        ].copy()
    print(f"数据清理：原{len(reach_data)}人，剔除{len(reach_data) - len(cleaned)}人，剩余{len(cleaned)}人")
    return cleaned


# 用SVM建模并计算残差分布
def build_svm_model(reach_data, n_folds=5, svr_params=None, seed=42):
    if svr_params is None:
        svr_params = {'kernel': 'rbf', 'C': 100, 'gamma': 0.1, 'epsilon': 0.1}

    X = reach_data[['bmi']].values
    y = reach_data['first_reach_week'].values
    base_model = SVR(**svr_params)

    # 交叉验证获取残差
    kf = KFold(n_splits=n_folds, shuffle=True, random_state=seed)
    oof_preds = np.zeros_like(y, dtype=float)
    for train_idx, val_idx in kf.split(X):
        model_temp = clone(base_model)
        model_temp.fit(X[train_idx], y[train_idx])
        oof_preds[val_idx] = model_temp.predict(X[val_idx])

    # 全量训练最终模型
    final_model = clone(base_model)
    final_model.fit(X, y)
    full_preds = final_model.predict(X)

    r2_full = r2_score(y, full_preds)
    r2_cv = r2_score(y, oof_preds)
    print(f"SVM模型效果：全量R²={r2_full:.3f}，交叉验证R²={r2_cv:.3f}")

    # 计算残差的经验分布
    residuals = y - oof_preds
    sorted_resid = np.sort(residuals)

    def resid_cdf(x):
        x_arr = np.atleast_1d(x)
        idx = np.searchsorted(sorted_resid, x_arr, side='right')
        return idx / sorted_resid.size

    return final_model, resid_cdf


# 寻找曲线拐点
def find_curve_bends(reach_data, model):
    bmi_min, bmi_max = reach_data['bmi'].min(), reach_data['bmi'].max()
    bmi_test = np.linspace(bmi_min, bmi_max, 500)
    preds = model.predict(bmi_test.reshape(-1, 1))
    first_deriv = np.gradient(preds, bmi_test)
    second_deriv = np.gradient(first_deriv, bmi_test)

    bend_points = []
    for i in range(1, len(second_deriv)):
        if second_deriv[i - 1] * second_deriv[i] < 0:
            bend_points.append(i)

    bend_bmis = [bmi_test[i] for i in bend_points]
    print(f"找到拐点BMI值: {', '.join(f'{b:.2f}' for b in bend_bmis)}")
    return bend_bmis, bmi_test, preds


# 按拐点分组，合并过小组
def make_bmi_groups(reach_data, bend_points, min_size=5):
    bend_points = sorted(bend_points)
    bmi_min, bmi_max = reach_data['bmi'].min(), reach_data['bmi'].max()
    splits = [bmi_min] + bend_points + [bmi_max]

    groups = []
    for i in range(len(splits) - 1):
        group_data = reach_data[(reach_data['bmi'] >= splits[i]) &
                                (reach_data['bmi'] < splits[i + 1])]
        groups.append({
            'group_num': i + 1,
            'bmi_range': (splits[i], splits[i + 1]),
            'data': group_data
        })

    # 合并样本量太小的组
    merged = []
    i = 0
    while i < len(groups):
        current = groups[i]
        if len(current['data']) < min_size:
            if i == 0 and len(groups) > 1:
                combined_data = pd.concat([current['data'], groups[i + 1]['data']])
                merged.append({
                    'group_num': len(merged) + 1,
                    'bmi_range': (current['bmi_range'][0], groups[i + 1]['bmi_range'][1]),
                    'data': combined_data
                })
                i += 2
            elif merged:
                last_group = merged[-1]
                last_group['data'] = pd.concat([last_group['data'], current['data']])
                last_group['bmi_range'] = (last_group['bmi_range'][0], current['bmi_range'][1])
                i += 1
            else:
                merged.append(current)
                i += 1
        else:
            merged.append(current)
            i += 1

    # 输出分组信息
    summary = []
    for g in merged:
        g_data = g['data']
        summary.append({
            '组号': g['group_num'],
            'BMI范围': f"{g['bmi_range'][0]:.2f}–{g['bmi_range'][1]:.2f}",
            '人数': len(g_data),
            '中位达标周数': round(g_data['first_reach_week'].median(), 2)
        })
    return merged, summary


# 风险计算相关函数
def calc_avg_reach_prob(pred_vals, resid_cdf, target_week):
    return float(np.mean(resid_cdf(target_week - pred_vals)))


# 计算未达标风险和延误风险
def calc_risks(target_week, pred_vals, resid_cdf, upper_bound=14.0, delay_cost=0.05):
    prob = calc_avg_reach_prob(pred_vals, resid_cdf, target_week)
    risk_not_done = 1.0 - prob
    risk_delay = max(0.0, target_week - upper_bound) * delay_cost
    return risk_not_done, risk_delay


# 计算总风险分数
def total_risk_score(target_week, pred_vals, resid_cdf, w1=1.0, w2=0.2,
                     upper_bound=14.0, delay_cost=0.05,
                     error_handling='worst', error_margin=0.5):
    if error_handling == 'none':
        r_nd, r_delay = calc_risks(target_week, pred_vals, resid_cdf, upper_bound, delay_cost)
        return w1 * r_nd + w2 * r_delay
    elif error_handling == 'worst':
        risks = []
        for offset in (-error_margin, +error_margin):
            r_nd, r_delay = calc_risks(target_week + offset, pred_vals, resid_cdf, upper_bound, delay_cost)
            risks.append(w1 * r_nd + w2 * r_delay)
        return max(risks)
    elif error_handling == 'gauss':
        sigma = error_margin
        offsets = np.linspace(-3 * sigma, 3 * sigma, 9)
        weights = np.exp(-0.5 * (offsets / sigma) ** 2)
        weights /= weights.sum()
        total_risk = 0.0
        for offset, weight in zip(offsets, weights):
            r_nd, r_delay = calc_risks(target_week + offset, pred_vals, resid_cdf, upper_bound, delay_cost)
            total_risk += weight * (w1 * r_nd + w2 * r_delay)
        return float(total_risk)
    else:
        raise ValueError("误差处理方式只能是'none'、'worst'或'gauss'")


# 寻找单个组的最佳检测周
def find_best_test_week(group, model, resid_cdf, week_range=(10.0, 20.0), step=0.05,
                        w1=1.0, w2=0.2, upper_bound=14.0, delay_cost=0.05,
                        error_handling='worst', error_margin=0.5):
    X_group = group['data'][['bmi']].values
    preds = model.predict(X_group)
    weeks = np.arange(week_range[0], week_range[1] + 1e-9, step)
    risks = [total_risk_score(w, preds, resid_cdf, w1, w2, upper_bound, delay_cost, error_handling, error_margin)
             for w in weeks]
    best_idx = np.argmin(risks)
    return float(weeks[best_idx]), float(risks[best_idx]), weeks, risks


# 优化所有组的检测时间
def optimize_all_groups(groups, model, resid_cdf, week_range=(10.0, 20.0), step=0.05,
                        w1=1.0, w2=0.2, upper_bound=14.0, delay_cost=0.05,
                        error_handling='worst', error_margin=0.5, plot_curves=True):
    results = []
    for g in groups:
        best_week, min_risk, week_grid, risk_vals = find_best_test_week(
            g, model, resid_cdf, week_range, step, w1, w2, upper_bound, delay_cost, error_handling, error_margin
        )
        g['best_week'] = round(best_week, 2)
        g['min_risk'] = min_risk
        results.append({
            '组号': g['group_num'],
            'BMI范围': f"{g['bmi_range'][0]:.2f}–{g['bmi_range'][1]:.2f}",
            '人数': len(g['data']),
            '最佳检测周': round(best_week, 2),
            '最小风险': round(min_risk, 4)
        })
        if plot_curves:
            plt.figure(figsize=(7, 4))
            plt.plot(week_grid, risk_vals, label=f"第{g['group_num']}组")
            plt.axvline(upper_bound, color='r', ls='--', label='目标上限')
            plt.axvline(best_week, color='g', ls=':', label=f'最优{best_week:.2f}周')
            plt.xlabel("检测孕周");
            plt.ylabel("总风险");
            plt.title(f"第{g['group_num']}组风险曲线")
            plt.legend();
            plt.grid(alpha=0.3);
            plt.tight_layout();
            plt.show()
    return pd.DataFrame(results)


# 误差敏感性分析
def check_error_sensitivity(groups, model, resid_cdf, offsets=[-1, 0, +1],
                            w1=1.0, w2=0.2, upper_bound=14.0, delay_cost=0.05):
    print("\n误差敏感性分析：")
    for g in groups:
        optimal_week = g.get('best_week', None)
        if optimal_week is None:
            continue
        Xg = g['data'][['bmi']].values
        preds = model.predict(Xg)
        print(f"\n第{g['group_num']}组 (最优{optimal_week}周):")
        for offset in offsets:
            test_week = optimal_week + offset
            prob = calc_avg_reach_prob(preds, resid_cdf, test_week)
            r_nd, r_delay = calc_risks(test_week, preds, resid_cdf, upper_bound, delay_cost)
            total_r = w1 * r_nd + w2 * r_delay
            print(
                f"  偏差{offset:+}周 → 达标概率: {prob:.2%} | 未达标风险: {r_nd:.2%} | 延误风险: {r_delay:.4f} | 总风险: {total_r:.4f}")


# 打印各组详细风险分析
def print_group_details(groups, model, resid_cdf, w1=1.0, w2=0.2, upper_bound=14.0, delay_cost=0.05, error_margin=0.5):
    print("\n各组详细风险分析：")
    for g in groups:
        best_w = g.get('best_week', None)
        if best_w is None:
            continue
        Xg = g['data'][['bmi']].values
        preds = model.predict(Xg)
        prob = calc_avg_reach_prob(preds, resid_cdf, best_w)
        r_nd, r_delay = calc_risks(best_w, preds, resid_cdf, upper_bound, delay_cost)
        total_risk_val = w1 * r_nd + w2 * r_delay

        # 计算最坏情况
        worst_risk = max(
            w1 * calc_risks(best_w - error_margin, preds, resid_cdf, upper_bound, delay_cost)[0] +
            w2 * calc_risks(best_w - error_margin, preds, resid_cdf, upper_bound, delay_cost)[1],
            w1 * calc_risks(best_w + error_margin, preds, resid_cdf, upper_bound, delay_cost)[0] +
            w2 * calc_risks(best_w + error_margin, preds, resid_cdf, upper_bound, delay_cost)[1]
        )

        print(f"\n第{g['group_num']}组 | BMI范围: {g['bmi_range'][0]:.2f}–{g['bmi_range'][1]:.2f}")
        print(f"  最佳检测周: {best_w:.2f}周")
        print(f"  平均达标概率: {prob:.2%}")
        print(f"  未达标风险: {r_nd:.4f}")
        print(f"  延误风险: {r_delay:.4f}")
        print(f"  总风险: {total_risk_val:.4f}")
        print(f"  最坏情况风险(±{error_margin}周): {worst_risk:.4f}")


# 绘制SVM拟合曲线和拐点
def plot_curve_with_bends(bmi_grid, predictions, bend_points, groups):
    plt.figure(figsize=(9, 6))
    for g in groups:
        plt.scatter(g['data']['bmi'], g['data']['first_reach_week'], label=f"第{g['group_num']}组")
    plt.plot(bmi_grid, predictions, 'r-', linewidth=2, label='SVM拟合曲线')
    for bp in bend_points:
        plt.axvline(bp, color='purple', linestyle='--', alpha=0.7)
    plt.xlabel("BMI")
    plt.ylabel("最早达标时间(周)")
    plt.title("SVM拟合曲线与拐点")
    plt.legend()
    plt.show()


# 将分组数据转换为长格式，便于绘图
def groups_to_long_format(groups, show_range=False, decimal_places=2):
    all_data = []
    for g in groups:
        gid = g['group_num']
        if show_range and 'bmi_range' in g:
            low, high = g['bmi_range']
            label = f"第{gid}组\n[{low:.{decimal_places}f}–{high:.{decimal_places}f}]"
        else:
            label = f"第{gid}组"
        for time_val in g['data']['first_reach_week'].dropna().values:
            all_data.append({'分组': label, 'reach_time': time_val})
    return pd.DataFrame(all_data)


# 绘制各组箱线图和散点图
def plot_group_boxplots(groups, title=None, show_ranges=False, save_path=None):
    long_data = groups_to_long_format(groups, show_ranges)
    n_groups = long_data['分组'].nunique()
    if title is None:
        title = f"不同BMI分组达标时间分布（共{n_groups}组）"

    groups_list = list(long_data['分组'].unique())
    colors = sns.color_palette("Set2", len(groups_list))
    color_map = {g: colors[i] for i, g in enumerate(groups_list)}

    plt.figure(figsize=(10, 6))
    ax = sns.boxplot(data=long_data, x='分组', y='reach_time', hue='分组',
                     dodge=False, legend=False, palette=color_map, width=0.6, fliersize=3)
    sns.stripplot(data=long_data, x='分组', y='reach_time', color='gray',
                  alpha=0.6, jitter=0.25, dodge=False, size=4)

    counts = long_data.groupby('分组')['reach_time'].count()
    y_max = ax.get_ylim()[1]
    for i, label in enumerate(ax.get_xticklabels()):
        n = counts.get(label.get_text(), 0)
        ax.text(i, y_max, f"n={n}", ha='center', va='bottom', fontsize=10, color='#555')

    ax.set_xlabel("分组")
    ax.set_ylabel("最早达标时间（周）")
    ax.set_title(title)
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.show()


# 绘制各组均值和标准差的柱状图
def plot_group_means(groups, title=None, show_ranges=False, save_path=None):
    long_data = groups_to_long_format(groups, show_ranges)
    n_groups = long_data['分组'].nunique()
    if title is None:
        title = f"各分组平均达标时间及标准差（共{n_groups}组）"

    stats = long_data.groupby('分组')['reach_time'].agg(['mean', 'std', 'count']).reset_index()
    stats['std'] = stats['std'].fillna(0.0)

    plt.figure(figsize=(10, 6))
    ax = plt.gca()
    bars = ax.bar(stats['分组'], stats['mean'], yerr=stats['std'],
                  capsize=6, edgecolor='black', alpha=0.9)

    for bar, mean_val in zip(bars, stats['mean']):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                f"{mean_val:.2f}", ha='center', va='bottom', fontsize=10)

    ax.set_xlabel("分组")
    ax.set_ylabel("最早达标时间（周）")
    ax.set_title(title)
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.show()


# 主流程
def main():
    # 读取数据
    data = pd.read_excel('第一问.xlsx', sheet_name='Sheet1')
    male_data = data[data['Y染色体浓度'].notna()].copy()

    # 提取达标时间
    reach_data = get_first_reach_time(male_data)

    # 清理异常值
    reach_data = remove_weird_values(reach_data, col='first_reach_week', min_week=8, max_week=25)

    # 建立SVM模型
    svm_model, residual_cdf = build_svm_model(reach_data, n_folds=5)

    # 寻找拐点
    bend_points, bmi_grid, predictions = find_curve_bends(reach_data, svm_model)

    # 分组
    groups, summary_table = make_bmi_groups(reach_data, bend_points, min_size=5)
    print("\n分组结果：")
    print(pd.DataFrame(summary_table))

    # 优化检测时间
    _ = optimize_all_groups(
        groups, svm_model, residual_cdf,
        week_range=(10.0, 20.0), step=0.05,
        w1=1.0, w2=0.2, upper_bound=14.0, delay_cost=0.05,
        error_handling='worst', error_margin=0.5,
        plot_curves=True
    )

    # 打印详细风险分析
    print_group_details(
        groups, svm_model, residual_cdf,
        w1=1.0, w2=0.2, upper_bound=14.0, delay_cost=0.05,
        error_margin=0.5
    )

    # 误差敏感性分析
    check_error_sensitivity(groups, svm_model, residual_cdf, offsets=[-1, 0, +1])

    # 可视化
    plot_curve_with_bends(bmi_grid, predictions, bend_points, groups)
    plot_group_boxplots(groups, show_ranges=False)
    plot_group_means(groups, show_ranges=False)


# 运行主程序
if __name__ == "__main__":
    main()
