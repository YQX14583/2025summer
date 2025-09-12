import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.svm import SVR
from sklearn.model_selection import KFold
from sklearn.base import clone
from sklearn.metrics import r2_score
import warnings
import seaborn as sns
from scipy.signal import argrelextrema

warnings.filterwarnings('ignore')

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

# 参数配置
Q3_FILE = '第三问.xlsx'
SHEET = 'Sheet1'
THRESHOLD = 0.04
WEEK_MIN, WEEK_MAX = 8, 25
T_BOUNDS = (10.0, 20.0)
GRID_STEP = 0.05
T_TARGET_UPPER = 14.0
W1, W2 = 1.0, 0.2
C_DELAY = 0.05
ERR_PARAM = 0.5
SVR_KW = dict(kernel='rbf', C=100, gamma=0.1, epsilon=0.1)
RANDOM_STATE = 42
PLOT_CURVES = True


def check_required_columns(df, cols):
    """检查数据是否包含必要的列"""
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"数据缺少必要列: {missing}")


def extract_reach_times_from_original(df, threshold=THRESHOLD):
    """提取每个孕妇首次达到Y染色体浓度阈值的时间"""
    need_cols = ['孕妇代码', '检测孕周', 'Y染色体浓度', '孕妇BMI', '年龄', '身高', '体重']
    check_required_columns(df, need_cols)

    df = df.copy()
    records = []

    for pid, sub in df.groupby('孕妇代码'):
        sub = sub.dropna(subset=['检测孕周']).sort_values('检测孕周')
        hit = sub[sub['Y染色体浓度'] >= threshold]
        if not hit.empty:
            first_hit = hit.iloc[0]
            base_row = sub.iloc[0]
            records.append({
                '孕妇代码': pid,
                'BMI': float(base_row['孕妇BMI']),
                '年龄': float(base_row['年龄']),
                '身高': float(base_row['身高']),
                '体重': float(base_row['体重']),
                'reach_time': float(first_hit['检测孕周'])
            })

    out_df = pd.DataFrame(records)
    if out_df.empty:
        raise ValueError("未提取到任何达标样本，请检查阈值或数据")
    return out_df.reset_index(drop=True)


def remove_outliers_iqr(df, col='reach_time', week_min=WEEK_MIN, week_max=WEEK_MAX):
    """使用IQR方法去除异常值"""
    Q1 = df[col].quantile(0.25)
    Q3 = df[col].quantile(0.75)
    IQR = Q3 - Q1
    lower = Q1 - 1.5 * IQR
    upper = Q3 + 1.5 * IQR
    cond = (df[col] >= lower) & (df[col] <= upper)
    cond &= (df[col] >= week_min) & (df[col] <= week_max)
    print(f"去极值: 原{len(df)}人, 剔除{len(df) - cond.sum()}人, 保留{cond.sum()}人")
    return df[cond].reset_index(drop=True)


def fit_svm_model_with_oof(df, target_col, feature_cols, n_splits=5,
                           svr_kwargs=None, random_state=RANDOM_STATE):
    """使用SVM和交叉验证训练模型并计算残差分布"""
    if svr_kwargs is None:
        svr_kwargs = SVR_KW

    X = df[feature_cols].to_numpy()
    y = df[target_col].to_numpy()
    base_model = SVR(**svr_kwargs)

    kf = KFold(n_splits=n_splits, shuffle=True, random_state=random_state)
    oof_pred = np.zeros_like(y, dtype=float)

    for tr, va in kf.split(X):
        m = clone(base_model)
        m.fit(X[tr], y[tr])
        oof_pred[va] = m.predict(X[va])

    final_model = clone(base_model).fit(X, y)
    print(f"SVM模型: 训练R²={r2_score(y, final_model.predict(X)):.3f}, 交叉验证R²={r2_score(y, oof_pred):.3f}")

    # 计算残差的经验分布
    residuals = y - oof_pred
    sorted_resid = np.sort(residuals)

    def resid_cdf(x):
        xs = np.atleast_1d(x)
        idx = np.searchsorted(sorted_resid, xs, side='right')
        return idx / sorted_resid.size

    return final_model, resid_cdf


def mean_reach_prob_at_T(yhat, resid_cdf, T):
    """计算在时间T的平均达标概率"""
    return float(np.mean(resid_cdf(T - yhat)))


def risks_at_T(T, yhat, resid_cdf, T_target_upper=T_TARGET_UPPER, c_delay=C_DELAY):
    """计算在时间T的不达标风险和延误风险"""
    p_bar = mean_reach_prob_at_T(yhat, resid_cdf, T)
    R_nd = 1.0 - p_bar
    R_delay = max(0.0, T - T_target_upper) * c_delay
    return R_nd, R_delay


def total_risk(T, yhat, resid_cdf, w1=W1, w2=W2,
               T_target_upper=T_TARGET_UPPER, c_delay=C_DELAY,
               err_param=ERR_PARAM):
    """计算考虑误差的总风险"""
    R1 = risks_at_T(T - err_param, yhat, resid_cdf, T_target_upper, c_delay)
    R2 = risks_at_T(T + err_param, yhat, resid_cdf, T_target_upper, c_delay)
    return max(w1 * R1[0] + w2 * R1[1], w1 * R2[0] + w2 * R2[1])


def auto_group_by_svm_curve(df, svm_model, feature_cols, target_feature='BMI',
                            n_min=4, threshold=0.02):
    """基于SVM拟合曲线的拐点自动进行BMI分组"""
    bmi_range = np.linspace(df[target_feature].min(), df[target_feature].max(), 200)
    X_plot = pd.DataFrame({col: [df[col].mean()] * len(bmi_range) for col in feature_cols})
    X_plot[target_feature] = bmi_range

    pred_curve = svm_model.predict(X_plot[feature_cols])
    dydx = np.gradient(pred_curve, bmi_range)
    d2ydx2 = np.gradient(dydx, bmi_range)

    keypoints_idx = argrelextrema(np.abs(d2ydx2), np.greater, order=n_min)[0]
    keypoints = bmi_range[keypoints_idx[(np.abs(d2ydx2[keypoints_idx]) > threshold)]]

    df['bmi_group_label'] = pd.cut(df[target_feature],
                                   bins=[-np.inf] + list(keypoints) + [np.inf],
                                   labels=False)

    # 可视化
    plt.figure(figsize=(10, 6))
    plt.plot(bmi_range, pred_curve, 'r-', linewidth=2, label='SVM拟合曲线')
    plt.scatter(df[target_feature], df['reach_time'], alpha=0.7, label='原始数据')
    plt.scatter(keypoints, svm_model.predict(X_plot[X_plot[target_feature].isin(keypoints)][feature_cols]),
                color='green', s=100, marker='x', label='拐点')
    plt.xlabel("BMI")
    plt.ylabel("预测达标孕周")
    plt.title("基于SVM曲线拐点的BMI分组")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.show()

    return df, sorted(keypoints)


def optimize_groups_by_risk(groups, model, resid_cdf, feature_cols, T_bounds, step,
                            w1, w2, T_target_upper, c_delay, err_param, plot_curves):
    """为每个分组优化检测时间以最小化风险"""
    for g in groups:
        Xg = g['data'][feature_cols].to_numpy()
        yhat = model.predict(Xg)

        grid = np.arange(T_bounds[0], T_bounds[1] + step, step)
        risks = [total_risk(T, yhat, resid_cdf, w1, w2, T_target_upper, c_delay, err_param) for T in grid]
        min_idx = np.argmin(risks)

        g['optimal_week_risk'] = grid[min_idx]
        g['R_nd'], g['R_delay'] = risks_at_T(grid[min_idx], yhat, resid_cdf, T_target_upper, c_delay)
        g['avg_reach_prob'] = mean_reach_prob_at_T(yhat, resid_cdf, grid[min_idx])

        if plot_curves:
            plt.figure(figsize=(6, 4))
            plt.plot(grid, risks, label=f"组{g['group_id']}")
            plt.axvline(grid[min_idx], color='r', linestyle='--', label=f"最优{grid[min_idx]:.2f}周")
            plt.xlabel("检测孕周")
            plt.ylabel("风险")
            plt.title(f"组{g['group_id']}风险曲线")
            plt.legend()
            plt.grid(alpha=0.3)
            plt.tight_layout()
            plt.show()


def print_group_risk_details(groups):
    """打印各分组的风险分析结果"""
    print("\n=== 各组风险分析结果 ===")
    for g in groups:
        bmi_min, bmi_max = g['bmi_range']
        print(f"\n分组{g['group_id']}: BMI范围[{bmi_min:.2f}-{bmi_max:.2f}], 样本数{len(g['data'])}")
        print(f"  最优检测周: {g['optimal_week_risk']:.2f}")
        print(f"  平均达标概率: {g['avg_reach_prob']:.2%}")
        print(f"  未达标风险: {g['R_nd']:.4f}, 延误风险: {g['R_delay']:.4f}")
        print(f"  总风险: {g['R_nd'] + g['R_delay']:.4f}")


def analyze_time_error(groups, model, resid_cdf, feature_cols, offsets=[-1, 0, +1],
                       w1=W1, w2=W2, T_target_upper=T_TARGET_UPPER, c_delay=C_DELAY):
    """分析检测时间误差对风险的敏感性"""
    print("\n=== 时间误差敏感性分析 ===")

    for g in groups:
        opt_t = g.get('optimal_week_risk')
        if opt_t is None:
            continue

        Xg = g['data'][feature_cols].to_numpy()
        yhat = model.predict(Xg)

        print(f"\n分组{g['group_id']} (最优{opt_t:.2f}周):")
        for d in offsets:
            T = opt_t + d
            p_bar = mean_reach_prob_at_T(yhat, resid_cdf, T)
            R_nd, R_delay = risks_at_T(T, yhat, resid_cdf, T_target_upper, c_delay)
            R_total = w1 * R_nd + w2 * R_delay

            print(f"  偏差{d:+}周: 达标概率{p_bar:.2%}, 总风险{R_total:.4f}")


def plot_boxplot_by_bmi_group(df, col='reach_time', title="达标孕周分布箱型图"):
    """绘制按BMI分组的箱型图"""
    plt.figure(figsize=(8, 6))
    df['bmi_group_label'] = df['bmi_group_label'] + 1
    sns.boxplot(x='bmi_group_label', y=col, data=df, width=0.6, showfliers=False, palette="Set3")
    plt.title(title)
    plt.xlabel("BMI分组")
    plt.ylabel("达标孕周")
    plt.grid(axis='y', alpha=0.5)
    plt.tight_layout()
    plt.show()


def main():
    # 1. 加载和处理数据
    df = pd.read_excel(Q3_FILE, sheet_name=SHEET)
    reach_df = extract_reach_times_from_original(df)
    reach_df = remove_outliers_iqr(reach_df)

    # 2. 训练SVM模型
    feature_cols = ['BMI', '年龄', '身高', '体重']
    model, resid_cdf = fit_svm_model_with_oof(reach_df, 'reach_time', feature_cols)

    # 3. 自动BMI分组
    reach_df, keypoints = auto_group_by_svm_curve(reach_df, model, feature_cols)

    # 构建分组数据结构
    groups = []
    for group_label, group_data in reach_df.groupby('bmi_group_label'):
        groups.append({
            'group_id': group_label + 1,
            'bmi_range': (group_data['BMI'].min(), group_data['BMI'].max()),
            'data': group_data
        })

    # 4. 风险优化分析
    optimize_groups_by_risk(groups, model, resid_cdf, feature_cols,
                            T_BOUNDS, GRID_STEP, W1, W2, T_TARGET_UPPER,
                            C_DELAY, ERR_PARAM, PLOT_CURVES)

    # 5. 结果输出和可视化
    print_group_risk_details(groups)
    analyze_time_error(groups, model, resid_cdf, feature_cols)
    plot_boxplot_by_bmi_group(reach_df)


if __name__ == "__main__":
    main()
