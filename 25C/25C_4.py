import pandas as pd
import numpy as np
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix, ConfusionMatrixDisplay, roc_curve
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.inspection import permutation_importance
from skopt import BayesSearchCV
from skopt.space import Real, Categorical
import matplotlib.pyplot as plt
import warnings

warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

# 数据加载
print("加载数据中...")
normal_data = pd.read_excel("normal_data.xlsx")
t13_data = pd.read_excel("T13_data.xlsx")
t18_data = pd.read_excel("T18_data.xlsx")
t21_data = pd.read_excel("T21_data.xlsx")


def calc_effective_sequencing(data):
    """计算有效测序量"""
    data['有效测序量'] = (data['原始读段数'] * data['在参考基因组上比对的比例'] *
                          (1 - data['重复读段的比例']) * (1 - data['被过滤掉读段数的比例']))
    return data


# 添加有效测序量
normal_data = calc_effective_sequencing(normal_data)
t13_data = calc_effective_sequencing(t13_data)
t18_data = calc_effective_sequencing(t18_data)
t21_data = calc_effective_sequencing(t21_data)

print("数据预处理完成")
print(f"正常样本: {len(normal_data)}")
print(f"T13样本: {len(t13_data)}")
print(f"T18样本: {len(t18_data)}")
print(f"T21样本: {len(t21_data)}")


def get_class_weights(y):
    """计算类别权重"""
    from sklearn.utils.class_weight import compute_class_weight
    classes = np.unique(y)
    weights = compute_class_weight('balanced', classes=classes, y=y)
    return dict(zip(classes, weights))


def generate_linear_approx(model, X_train, feature_names, task_name):
    """为SVM生成线性近似表达式"""
    from sklearn.linear_model import LogisticRegression
    print(f"为{task_name}生成线性近似...")

    try:
        svm_scores = model.decision_function(X_train)
        linear_model = LogisticRegression(penalty=None, solver='lbfgs', max_iter=1000, random_state=42)
        svm_labels = (svm_scores > 0).astype(int)
        linear_model.fit(X_train, svm_labels)
        coefs = linear_model.coef_[0]
        intercept = linear_model.intercept_[0]

        # 构建表达式
        terms = []
        for i, (coef, feature) in enumerate(zip(coefs, feature_names)):
            if abs(coef) > 0.001:
                sign = "+" if coef >= 0 else "-"
                terms.append(f"{sign} {abs(coef):.4f}×{feature}")

        expr = terms[0].lstrip('+ ') if terms else "0"
        for term in terms[1:]:
            expr += f" {term}"

        if abs(intercept) > 0.001:
            expr += f" {'+' if intercept >= 0 else '-'} {abs(intercept):.4f}"

        print(f"近似表达式: f(x) = {expr}")

        # 评估近似效果
        approx_preds = linear_model.predict(X_train)
        svm_preds = model.predict(X_train)
        accuracy = np.mean(approx_preds == svm_preds)

        print(f"近似准确率: {accuracy:.3%}")
        print(f"判断规则: f(x) > 0 → {task_name}异常")

        print("\n特征影响分析:")
        for coef, feature in zip(coefs, feature_names):
            if abs(coef) > 0.001:
                effect = "增加风险" if coef > 0 else "降低风险"
                print(f"  {feature}: {effect} (权重: {coef:.4f})")
        return {
            'coefficients': coefs,
            'intercept': intercept,
            'expression': expr,
            'accuracy': accuracy
        }

    except Exception as e:
        print(f"线性近似失败: {e}")
        return None


def analyze_features(model, X_test, y_test, feature_names, task_name):
    """分析特征重要性"""
    print(f"\n{task_name}特征重要性:")
    perm_importance = permutation_importance(
        model, X_test, y_test, n_repeats=10, random_state=42, scoring='roc_auc', n_jobs=-1
    )
    importance_df = pd.DataFrame({
        '特征': feature_names,
        '重要性': perm_importance.importances_mean,
        '标准差': perm_importance.importances_std
    }).sort_values('重要性', ascending=False)
    print(importance_df.to_string(index=False))

    # 可视化
    plt.figure(figsize=(10, 6))
    indices = np.argsort(perm_importance.importances_mean)
    plt.barh(range(len(indices)), perm_importance.importances_mean[indices],
             xerr=perm_importance.importances_std[indices], color='lightblue')
    plt.yticks(range(len(indices)), [feature_names[i] for i in indices])
    plt.xlabel('重要性得分')
    plt.title(f'{task_name}特征重要性')
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.show()

    return importance_df


def run_chromosome_analysis(normal_df, abnormal_df, chrom_num, task_name):
    """运行染色体异常分析"""
    features = [
        'X染色体的Z值（绝对值）',
        f'{chrom_num}号染色体的Z值（绝对值）',
        'GC含量',
        '有效测序量',
        '孕妇BMI'
    ]

    normal_df = normal_df.copy()
    abnormal_df = abnormal_df.copy()
    normal_df["标签"] = 0
    abnormal_df["标签"] = 1
    all_data = pd.concat([normal_df, abnormal_df], ignore_index=True)
    X = all_data[features].fillna(all_data[features].mean())
    y = all_data["标签"]
    X_array = np.array(X)
    y_array = np.array(y)
    print(f"数据分布: 正常={sum(y_array == 0)}, 异常={sum(y_array == 1)}")

    # 标准化
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_array)

    # 划分数据集
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y_array, test_size=0.2, random_state=42, stratify=y_array
    )

    # 训练SVM
    class_weights = get_class_weights(y_array)
    svm_model = SVC(probability=True, random_state=42, class_weight=class_weights)
    param_space = {
        'C': Real(0.01, 100, prior='log-uniform'),
        'gamma': Real(0.001, 10, prior='log-uniform'),
        'kernel': Categorical(['rbf', 'linear'])
    }

    optimizer = BayesSearchCV(
        estimator=svm_model,
        search_spaces=param_space,
        n_iter=15,
        cv=StratifiedKFold(n_splits=3, shuffle=True, random_state=42),
        scoring='roc_auc',
        n_jobs=-1,
        random_state=42
    )

    optimizer.fit(X_train, y_train)
    best_model = optimizer.best_estimator_

    print(f"最佳参数: {optimizer.best_params_}")
    print(f"最佳AUC: {optimizer.best_score_:.4f}")

    # 评估模型
    y_train_pred = best_model.predict(X_train)
    y_train_proba = best_model.predict_proba(X_train)[:, 1]
    y_test_pred = best_model.predict(X_test)
    y_test_proba = best_model.predict_proba(X_test)[:, 1]

    print("\n训练集效果:")
    print(classification_report(y_train, y_train_pred, target_names=["正常", f"{task_name}异常"]))
    print(f"AUC: {roc_auc_score(y_train, y_train_proba):.4f}")

    print("\n测试集效果:")
    print(classification_report(y_test, y_test_pred, target_names=["正常", f"{task_name}异常"]))
    print(f"AUC: {roc_auc_score(y_test, y_test_proba):.4f}")

    # 特征分析
    feature_importance = analyze_features(best_model, X_test, y_test, features, task_name)

    # 线性近似
    linear_info = generate_linear_approx(best_model, X_train, features, task_name)

    # 支持向量分析
    print(f"\n支持向量: {len(best_model.support_)}个 ({len(best_model.support_) / len(X_train):.2%})")
    support_labels = y_train[best_model.support_]
    print(f"正常支持向量: {sum(support_labels == 0)}")
    print(f"异常支持向量: {sum(support_labels == 1)}")

    # 可视化
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    cm_train = confusion_matrix(y_train, y_train_pred)
    cm_test = confusion_matrix(y_test, y_test_pred)
    ConfusionMatrixDisplay(cm_train, display_labels=["正常", f"{task_name}异常"]).plot(ax=ax1, cmap='Blues')
    ConfusionMatrixDisplay(cm_test, display_labels=["正常", f"{task_name}异常"]).plot(ax=ax2, cmap='Blues')
    ax1.set_title('训练集混淆矩阵')
    ax2.set_title('测试集混淆矩阵')
    plt.tight_layout()
    plt.show()

    # ROC曲线
    plt.figure(figsize=(10, 6))
    fpr_train, tpr_train, _ = roc_curve(y_train, y_train_proba)
    fpr_test, tpr_test, _ = roc_curve(y_test, y_test_proba)
    plt.plot(fpr_train, tpr_train, label=f'训练集 (AUC={roc_auc_score(y_train, y_train_proba):.3f})')
    plt.plot(fpr_test, tpr_test, label=f'测试集 (AUC={roc_auc_score(y_test, y_test_proba):.3f})')
    plt.plot([0, 1], [0, 1], 'k--', alpha=0.5)
    plt.xlabel('假阳性率')
    plt.ylabel('真阳性率')
    plt.title(f'{task_name} ROC曲线')
    plt.legend()
    plt.grid(alpha=0.3)
    plt.show()

    return {
        'model': best_model,
        'scaler': scaler,
        'features': features,
        'train_auc': roc_auc_score(y_train, y_train_proba),
        'test_auc': roc_auc_score(y_test, y_test_proba),
        'feature_importance': feature_importance,
        'linear_info': linear_info,
        'support_count': len(best_model.support_),
        'kernel': best_model.kernel
    }


# 运行所有分析
results = {}
for chrom, name in [("13", "T13"), ("18", "T18"), ("21", "T21")]:
    try:
        data = eval(f"{name.lower()}_data")
        results[name] = run_chromosome_analysis(normal_data, data, chrom, name)
        print(f"{name}分析完成")
    except Exception as e:
        print(f"{name}分析出错: {e}")
        import traceback

        traceback.print_exc()

# 结果汇总
if results:
    print("\n分析结果汇总:")
    summary = []
    for name, res in results.items():
        summary.append({
            '类型': name,
            '测试AUC': f"{res['test_auc']:.4f}",
            '核函数': res['kernel'],
            '支持向量数': res['support_count']
        })

    summary_df = pd.DataFrame(summary)
    print(summary_df.to_string(index=False))
