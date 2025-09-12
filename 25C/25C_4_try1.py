import pandas as pd
import numpy as np
from sklearn.inspection import permutation_importance
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest
from sklearn.svm import OneClassSVM
from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix
from skopt import BayesSearchCV
from skopt.space import Real, Categorical, Integer
from xgboost import XGBClassifier
from imblearn.under_sampling import RandomUnderSampler
import matplotlib.pyplot as plt
import warnings
import seaborn as sns

warnings.filterwarnings('ignore')

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False


# ---------- 1. 数据加载与预处理 ----------
# 假设数据已经加载
# ---------- 1. 数据加载与预处理 ----------
# (您的数据加载和计算有效测序量的代码保持不变)
normal_data = pd.read_excel("normal_data.xlsx")
t13_data = pd.read_excel("T13_data.xlsx")
t18_data = pd.read_excel("T18_data.xlsx")
t21_data = pd.read_excel("T21_data.xlsx")


def add_effective_sequencing(data):
    data['有效测序量'] = (data['原始读段数'] *
                          data['在参考基因组上比对的比例'] *
                          (1 - data['重复读段的比例']) *
                          (1 - data['被过滤掉读段数的比例']))
    return data


normal_data = add_effective_sequencing(normal_data)
t13_data = add_effective_sequencing(t13_data)
t18_data = add_effective_sequencing(t18_data)
t21_data = add_effective_sequencing(t21_data)



def prepare_data(normal_df, abnormal_df, target_chromosome):
    """准备数据"""
    features = [
        f'X染色体的Z值（绝对值）',
        f'{target_chromosome}号染色体的Z值（绝对值）',
        'GC含量',
        '有效测序量',
        '孕妇BMI'
    ]

    normal_df["标签"] = 0
    abnormal_df["标签"] = 1
    combined_data = pd.concat([normal_df, abnormal_df], axis=0).reset_index(drop=True)

    X = combined_data[features]
    y = combined_data["标签"]

    # 处理缺失值
    X.fillna(X.mean(), inplace=True)

    # 标准化
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    return X_scaled, y, scaler, features


# ---------- 2. 异常检测方法 ----------
def anomaly_detection_approach(X, y, contamination=0.1):
    """
    异常检测框架：只使用正常样本训练，检测异常
    """
    print("训练异常检测模型...")

    # 只使用正常样本训练
    X_normal = X[y == 0]

    # 多种异常检测算法
    detectors = {
        'IsolationForest': IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100
        ),
        'OneClassSVM': OneClassSVM(
            nu=contamination,
            kernel='rbf',
            gamma='scale'
        )
    }

    results = {}
    for name, detector in detectors.items():
        print(f"  训练 {name}...")

        try:
            if name == 'OneClassSVM':
                detector.fit(X_normal)
                scores = detector.decision_function(X)
            else:
                detector.fit(X)
                if hasattr(detector, 'score_samples'):
                    scores = detector.score_samples(X)
                else:
                    scores = detector.decision_function(X)

            # 统一为异常概率（分数越高越可能是异常）
            if name == 'IsolationForest':
                scores = -scores  # IsolationForest分数需要取反

            # 标准化到0-1范围
            scores = (scores - np.min(scores)) / (np.max(scores) - np.min(scores))
            results[name] = scores

        except Exception as e:
            print(f"  {name}训练失败: {e}")
            continue

    # 集成结果（简单平均）
    if results:
        ensemble_scores = np.mean(list(results.values()), axis=0)
        print("异常检测模型训练完成")
        return ensemble_scores
    else:
        print("所有异常检测器都失败了")
        return None


# ---------- 3. 贝叶斯优化XGBoost ----------
def bayesian_xgboost(X, y, n_iter=20):
    """
    贝叶斯优化XGBoost参数
    """
    print("贝叶斯优化XGBoost...")

    # 定义搜索空间
    search_spaces = {
        'scale_pos_weight': Real(1, 50, prior='log-uniform'),  # 正样本权重
        'max_depth': Integer(3, 6),
        'learning_rate': Real(0.01, 0.2, prior='log-uniform'),
        'subsample': Real(0.6, 0.9),
        'colsample_bytree': Real(0.6, 0.9),
        'reg_alpha': Real(0, 1),
        'reg_lambda': Real(1, 10)
    }

    # 智能降采样（保持一定的不平衡度）
    rus = RandomUnderSampler(
        sampling_strategy={0: len(y[y == 1]) * 3, 1: len(y[y == 1])},  # 3:1的比例
        random_state=42
    )
    X_resampled, y_resampled = rus.fit_resample(X, y)

    # XGBoost模型
    model = XGBClassifier(
        eval_metric='logloss',
        random_state=42,
        n_estimators=100,
        use_label_encoder=False
    )

    # 贝叶斯优化
    opt = BayesSearchCV(
        estimator=model,
        search_spaces=search_spaces,
        n_iter=n_iter,
        cv=3,
        scoring='roc_auc',
        random_state=42,
        n_jobs=-1,
        verbose=0
    )

    opt.fit(X_resampled, y_resampled)

    print(f"最佳AUC分数: {opt.best_score_:.4f}")
    print("最佳参数:", opt.best_params_)

    return opt.best_estimator_


# ---------- 4. 集成最终模型 ----------
def ensemble_predictions(anomaly_scores, xgb_model, X, weights=[0.6, 0.4]):
    """
    集成异常检测和XGBoost的结果
    """
    # XGBoost预测概率
    xgb_proba = xgb_model.predict_proba(X)[:, 1]

    # 加权集成
    final_scores = weights[0] * anomaly_scores + weights[1] * xgb_proba

    return final_scores


# ---------- 5. 主函数 ----------
def innovative_solution(normal_df, abnormal_df, target_chromosome, task_name):
    """
    创新解决方案主函数
    """
    print(f"\n{'=' * 50}")
    print(f"开始处理 {task_name}")
    print(f"{'=' * 50}")

    # 1. 准备数据
    X, y, scaler, features = prepare_data(normal_df, abnormal_df, target_chromosome)
    print(f"数据分布: 正常={sum(y == 0)}, 异常={sum(y == 1)}")

    # 2. 异常检测
    anomaly_scores = anomaly_detection_approach(X, y, contamination=len(y[y == 1]) / len(y))

    # 3. 贝叶斯优化XGBoost
    xgb_model = bayesian_xgboost(X, y, n_iter=15)

    # 4. 集成预测
    final_scores = ensemble_predictions(anomaly_scores, xgb_model, X)

    # 5. 评估结果（使用0.5阈值）
    y_pred = (final_scores > 0.5).astype(int)

    print(f"\n{task_name} 最终结果:")
    print("分类报告:")
    print(classification_report(y, y_pred, target_names=["正常", f"{task_name}异常"]))
    print(f"AUC Score: {roc_auc_score(y, final_scores):.4f}")

    # 6. 可视化结果
    plot_results(y, final_scores, task_name)

    return final_scores, xgb_model, scaler


def plot_results(y_true, y_scores, task_name):
    """可视化结果"""
    plt.figure(figsize=(15, 5))

    # 1. 分数分布
    plt.subplot(131)
    plt.hist(y_scores[y_true == 0], alpha=0.7, label='正常', bins=20)
    plt.hist(y_scores[y_true == 1], alpha=0.7, label='异常', bins=20)
    plt.axvline(x=0.5, color='red', linestyle='--', label='阈值=0.5')
    plt.xlabel('异常概率')
    plt.ylabel('样本数')
    plt.title(f'{task_name} - 分数分布')
    plt.legend()

    # 2. 混淆矩阵
    plt.subplot(132)
    y_pred = (y_scores > 0.5).astype(int)
    cm = confusion_matrix(y_true, y_pred)
    plt.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
    plt.title(f'{task_name} - 混淆矩阵')
    plt.colorbar()
    tick_marks = np.arange(2)
    plt.xticks(tick_marks, ['正常', '异常'])
    plt.yticks(tick_marks, ['正常', '异常'])
    plt.ylabel('真实标签')
    plt.xlabel('预测标签')

    # 3. ROC曲线
    plt.subplot(133)
    from sklearn.metrics import roc_curve
    fpr, tpr, _ = roc_curve(y_true, y_scores)
    plt.plot(fpr, tpr, label=f'AUC = {roc_auc_score(y_true, y_scores):.3f}')
    plt.plot([0, 1], [0, 1], 'k--')
    plt.xlabel('假阳性率')
    plt.ylabel('真阳性率')
    plt.title(f'{task_name} - ROC曲线')
    plt.legend()

    plt.tight_layout()
    plt.show()


def analyze_feature_importance(model, X, y, feature_names, task_name):
    """
    分析特征重要性
    """
    print(f"\n=== {task_name} 特征重要性分析 ===")

    # 方法1: 基于模型内置的特征重要性（如果可用）
    if hasattr(model, 'feature_importances_'):
        print("基于模型内置的特征重要性:")
        importance_df = pd.DataFrame({
            '特征': feature_names,
            '重要性': model.feature_importances_
        }).sort_values('重要性', ascending=False)

        print(importance_df.to_string(index=False))

        # 可视化
        plt.figure(figsize=(10, 6))
        plt.barh(importance_df['特征'], importance_df['重要性'], color='skyblue')
        plt.title(f'{task_name} - 模型内置特征重要性')
        plt.xlabel('重要性得分')
        plt.gca().invert_yaxis()
        plt.tight_layout()
        plt.show()

    # 方法2: 排列重要性（更可靠）
    print("\n基于排列的特征重要性:")
    try:
        perm_importance = permutation_importance(
            model, X, y,
            n_repeats=10,
            random_state=42,
            scoring='roc_auc'
        )

        perm_df = pd.DataFrame({
            '特征': feature_names,
            '重要性均值': perm_importance.importances_mean,
            '重要性标准差': perm_importance.importances_std
        }).sort_values('重要性均值', ascending=False)

        print(perm_df.to_string(index=False))

        # 可视化排列重要性
        plt.figure(figsize=(12, 6))
        indices = np.argsort(perm_importance.importances_mean)
        plt.barh(range(len(indices)),
                 perm_importance.importances_mean[indices],
                 xerr=perm_importance.importances_std[indices],
                 color='lightgreen', alpha=0.7)
        plt.yticks(range(len(indices)), [feature_names[i] for i in indices])
        plt.title(f'{task_name} - 排列特征重要性 (±1标准差)')
        plt.xlabel('排列重要性得分')
        plt.tight_layout()
        plt.show()

    except Exception as e:
        print(f"排列重要性计算失败: {e}")

    # 方法3: SHAP值分析（最先进的方法）
    try:
        import shap
        print("\nSHAP值分析:")

        # 创建SHAP解释器
        if hasattr(model, 'predict_proba'):
            explainer = shap.Explainer(model, X, feature_names=feature_names)
            shap_values = explainer(X)

            # 摘要图
            plt.figure(figsize=(10, 8))
            shap.summary_plot(shap_values, X, feature_names=feature_names, show=False)
            plt.title(f'{task_name} - SHAP特征重要性')
            plt.tight_layout()
            plt.show()

            # 条形图（平均绝对SHAP值）
            plt.figure(figsize=(10, 6))
            shap.summary_plot(shap_values, X, feature_names=feature_names, plot_type="bar", show=False)
            plt.title(f'{task_name} - 平均绝对SHAP值')
            plt.tight_layout()
            plt.show()

        else:
            print("模型不支持SHAP分析")

    except ImportError:
        print("SHAP库未安装，跳过SHAP分析")
        print("请安装: pip install shap")
    except Exception as e:
        print(f"SHAP分析失败: {e}")


def analyze_correlation(X, y, feature_names, task_name):
    """
    分析特征相关性
    """
    print(f"\n=== {task_name} 特征相关性分析 ===")

    # 创建包含目标变量的DataFrame
    data_df = pd.DataFrame(X, columns=feature_names)
    data_df['target'] = y

    # 计算相关性矩阵
    corr_matrix = data_df.corr()

    # 可视化相关性热图
    plt.figure(figsize=(10, 8))
    mask = np.triu(np.ones_like(corr_matrix, dtype=bool))  # 创建上三角掩码
    sns.heatmap(corr_matrix,
                mask=mask,
                annot=True,
                cmap='coolwarm',
                center=0,
                square=True,
                fmt='.2f')
    plt.title(f'{task_name} - 特征相关性热图')
    plt.tight_layout()
    plt.show()

    # 显示与目标变量的相关性
    target_corr = corr_matrix['target'].drop('target').sort_values(key=abs, ascending=False)
    print("特征与目标变量的相关性:")
    for feature, corr in target_corr.items():
        print(f"{feature}: {corr:.3f}")


# 在您的主函数中添加特征分析
def innovative_solution_with_importance(normal_df, abnormal_df, target_chromosome, task_name):
    """
    包含特征重要性分析的完整解决方案
    """
    print(f"\n{'=' * 50}")
    print(f"开始处理 {task_name}")
    print(f"{'=' * 50}")

    # 1. 准备数据
    X, y, scaler, features = prepare_data(normal_df, abnormal_df, target_chromosome)
    print(f"数据分布: 正常={sum(y == 0)}, 异常={sum(y == 1)}")

    # 2. 异常检测
    anomaly_scores = anomaly_detection_approach(X, y, contamination=len(y[y == 1]) / len(y))

    # 3. 贝叶斯优化XGBoost
    xgb_model = bayesian_xgboost(X, y, n_iter=15)

    # 4. 特征重要性分析
    analyze_feature_importance(xgb_model, X, y, features, task_name)
    analyze_correlation(X, y, features, task_name)

    # 5. 集成预测
    final_scores = ensemble_predictions(anomaly_scores, xgb_model, X)

    # 6. 评估结果
    y_pred = (final_scores > 0.5).astype(int)

    print(f"\n{task_name} 最终结果:")
    print(classification_report(y, y_pred, target_names=["正常", f"{task_name}异常"]))
    print(f"AUC Score: {roc_auc_score(y, final_scores):.4f}")

    return final_scores, xgb_model, scaler


# 运行带有特征重要性分析的任务
print("开始运行带特征重要性分析的解决方案...")

# 运行三个任务
final_results = {}
for target, name in [("13", "T13"), ("18", "T18"), ("21", "T21")]:
    try:
        scores, model, scaler = innovative_solution_with_importance(
            normal_data.copy(),
            eval(f"{name.lower()}_data.copy()"),
            target, name
        )
        final_results[name] = {
            'scores': scores,
            'model': model,
            'scaler': scaler
        }
    except Exception as e:
        print(f"{name} 处理失败: {e}")
        continue

print("\n所有任务完成！")


# 额外的：比较三个任务的特征重要性
def compare_feature_importance_across_tasks(final_results, feature_names):
    """
    比较不同任务的特征重要性
    """
    print("\n=== 跨任务特征重要性比较 ===")

    importance_comparison = {}
    for task_name, result in final_results.items():
        model = result['model']
        if hasattr(model, 'feature_importances_'):
            importance_comparison[task_name] = model.feature_importances_

    if importance_comparison:
        comp_df = pd.DataFrame(importance_comparison, index=feature_names)
        comp_df = comp_df.T  # 转置以便更好的可视化

        # 可视化比较
        comp_df.plot(kind='bar', figsize=(12, 8), colormap='viridis')
        plt.title('跨任务特征重要性比较')
        plt.ylabel('重要性得分')
        plt.xlabel('任务')
        plt.xticks(rotation=45)
        plt.legend(title='特征', bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.tight_layout()
        plt.show()

        print("各任务特征重要性排名:")
        for task_name, importances in importance_comparison.items():
            ranked_features = sorted(zip(feature_names, importances),
                                     key=lambda x: x[1], reverse=True)
            print(f"\n{task_name}:")
            for feature, importance in ranked_features:
                print(f"  {feature}: {importance:.4f}")


# 运行跨任务比较
if final_results:
    # 假设所有任务使用相同的特征
    sample_features = ['X染色体的Z值（绝对值）', '目标染色体的Z值（绝对值）',
                       'GC含量', '有效测序量', '孕妇BMI']
    compare_feature_importance_across_tasks(final_results, sample_features)