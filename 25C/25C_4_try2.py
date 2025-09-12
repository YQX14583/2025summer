import pandas as pd
import numpy as np
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix, ConfusionMatrixDisplay
from sklearn.model_selection import train_test_split, StratifiedKFold
from skopt import BayesSearchCV
from skopt.space import Real, Categorical
from imblearn.over_sampling import SMOTE  # 添加SMOTE过采样
import matplotlib.pyplot as plt
import warnings

warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

# ---------- 1. 数据加载 ----------
print("正在加载数据...")
normal_data = pd.read_excel("normal_data.xlsx")
t13_data = pd.read_excel("T13_data.xlsx")
t18_data = pd.read_excel("T18_data.xlsx")
t21_data = pd.read_excel("T21_data.xlsx")


def add_effective_sequencing(data):
    """计算有效测序量"""
    data['有效测序量'] = (data['原始读段数'] *
                          data['在参考基因组上比对的比例'] *
                          (1 - data['重复读段的比例']) *
                          (1 - data['被过滤掉读段数的比例']))
    return data


# 添加有效测序量
normal_data = add_effective_sequencing(normal_data)
t13_data = add_effective_sequencing(t13_data)
t18_data = add_effective_sequencing(t18_data)
t21_data = add_effective_sequencing(t21_data)

print("数据加载和预处理完成！")
print(f"正常样本数: {len(normal_data)}")
print(f"T13异常样本数: {len(t13_data)}")
print(f"T18异常样本数: {len(t18_data)}")
print(f"T21异常样本数: {len(t21_data)}")


# ---------- 2. 手动计算类别权重 ----------
def calculate_class_weight(y):
    """手动计算类别权重"""
    from sklearn.utils.class_weight import compute_class_weight
    classes = np.unique(y)
    weights = compute_class_weight('balanced', classes=classes, y=y)
    return dict(zip(classes, weights))


# ---------- 3. SVM解决方案函数 ----------
def run_svm_for_chromosome(normal_df, abnormal_df, target_chromosome, task_name):
    """
    为特定染色体运行SVM分析
    """
    print(f"\n{'=' * 60}")
    print(f"开始处理 {task_name}")
    print(f"{'=' * 60}")

    # 定义特征集
    features = [
        f'X染色体的Z值（绝对值）',
        f'{target_chromosome}号染色体的Z值（绝对值）',
        'GC含量',
        '有效测序量',
        '孕妇BMI'
    ]

    # 准备数据
    normal_df = normal_df.copy()
    abnormal_df = abnormal_df.copy()

    normal_df["标签"] = 0  # 正常样本
    abnormal_df["标签"] = 1  # 异常样本

    # 合并数据
    combined_data = pd.concat([normal_df, abnormal_df], ignore_index=True)

    # 处理缺失值
    X = combined_data[features].fillna(combined_data[features].mean())
    y = combined_data["标签"]

    print(f"数据分布: 正常={sum(y == 0)}, 异常={sum(y == 1)}")
    print(f"不平衡比例: {sum(y == 0) / sum(y == 1):.1f}:1")

    # 计算类别权重
    class_weight = calculate_class_weight(y)
    print(f"自动计算的类别权重: {class_weight}")

    # 数据标准化
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # SMOTE过采样
    smote = SMOTE(random_state=42)
    X_res, y_res = smote.fit_resample(X_scaled, y)
    print(f"过采样后数据分布: 正常={sum(y_res == 0)}, 异常={sum(y_res == 1)}")

    # 划分训练测试集 - 使用numpy数组避免pandas索引问题
    X_train, X_test, y_train, y_test = train_test_split(
        X_res, np.array(y_res),  # 将y转换为numpy数组
        test_size=0.2,
        random_state=42,
        stratify=y_res
    )

    # ---------- SVM模型训练 ----------
    print("\n训练SVM模型...")

    # 使用固定类别权重，避免BayesSearchCV的问题
    svm_model = SVC(
        probability=True,
        random_state=42,
        class_weight=class_weight  # 使用计算好的权重
    )

    # 只优化其他参数
    search_spaces = {
        'C': Real(0.01, 100, prior='log-uniform'),
        'gamma': Real(0.001, 10, prior='log-uniform'),
        'kernel': Categorical(['rbf', 'linear'])
    }

    opt = BayesSearchCV(
        estimator=svm_model,
        search_spaces=search_spaces,
        n_iter=15,
        cv=StratifiedKFold(n_splits=3, shuffle=True, random_state=42),
        scoring='roc_auc',
        n_jobs=-1,
        random_state=42
    )

    opt.fit(X_train, y_train)

    print(f"最佳参数: {opt.best_params_}")
    print(f"最佳AUC: {opt.best_score_:.4f}")

    best_svm = opt.best_estimator_

    # ---------- 模型评估 ----------
    print("\n模型评估:")

    # 训练集性能
    y_train_pred = best_svm.predict(X_train)
    y_train_proba = best_svm.predict_proba(X_train)[:, 1]

    print("训练集性能:")
    print(classification_report(y_train, y_train_pred,
                                target_names=["正常", f"{task_name}异常"]))
    print(f"训练集AUC: {roc_auc_score(y_train, y_train_proba):.4f}")

    # 测试集性能
    y_test_pred = best_svm.predict(X_test)
    y_test_proba = best_svm.predict_proba(X_test)[:, 1]

    print("测试集性能:")
    print(classification_report(y_test, y_test_pred,
                                target_names=["正常", f"{task_name}异常"]))
    print(f"测试集AUC: {roc_auc_score(y_test, y_test_proba):.4f}")

    # ---------- 可视化结果 ----------
    # 1. 混淆矩阵
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

    cm_train = confusion_matrix(y_train, y_train_pred)
    disp_train = ConfusionMatrixDisplay(confusion_matrix=cm_train,
                                        display_labels=["正常", f"{task_name}异常"])
    disp_train.plot(ax=ax1, cmap='Blues')
    ax1.set_title(f'{task_name} - 训练集混淆矩阵')

    cm_test = confusion_matrix(y_test, y_test_pred)
    disp_test = ConfusionMatrixDisplay(confusion_matrix=cm_test,
                                       display_labels=["正常", f"{task_name}异常"])
    disp_test.plot(ax=ax2, cmap='Blues')
    ax2.set_title(f'{task_name} - 测试集混淆矩阵')

    plt.tight_layout()
    plt.show()

    # 2. ROC曲线
    from sklearn.metrics import roc_curve, auc

    plt.figure(figsize=(10, 6))

    # 训练集ROC
    fpr_train, tpr_train, _ = roc_curve(y_train, y_train_proba)
    roc_auc_train = auc(fpr_train, tpr_train)
    plt.plot(fpr_train, tpr_train, label=f'训练集 (AUC = {roc_auc_train:.3f})')

    # 测试集ROC
    fpr_test, tpr_test, _ = roc_curve(y_test, y_test_proba)
    roc_auc_test = auc(fpr_test, tpr_test)
    plt.plot(fpr_test, tpr_test, label=f'测试集 (AUC = {roc_auc_test:.3f})')

    plt.plot([0, 1], [0, 1], 'k--', label='随机分类器')
    plt.xlabel('假阳性率')
    plt.ylabel('真阳性率')
    plt.title(f'{task_name} - ROC曲线')
    plt.legend(loc='lower right')
    plt.grid(True, alpha=0.3)
    plt.show()

    # ---------- 特征重要性分析 ----------
    print(f"\n{task_name} 特征重要性分析:")

    # 排列重要性
    from sklearn.inspection import permutation_importance

    perm_importance = permutation_importance(
        best_svm, X_test, y_test,
        n_repeats=5,
        random_state=42, n_jobs=-1
    )

    # 输出特征重要性
    feature_importance = perm_importance.importances_mean
    feature_names = features

    importance_df = pd.DataFrame({
        'Feature': feature_names,
        'Importance': feature_importance
    }).sort_values(by='Importance', ascending=False)

    print(importance_df)

    # 可视化特征重要性
    plt.figure(figsize=(10, 6))
    plt.barh(importance_df['Feature'], importance_df['Importance'], color='skyblue')
    plt.xlabel('Mean Decrease in Accuracy')
    plt.title(f'{task_name} - 特征重要性')
    plt.gca().invert_yaxis()  # 反转y轴，重要性高的在上面
    plt.show()


# ---------- 4. 执行任务 ----------
# 分别对T13、T18、T21进行SVM分析
run_svm_for_chromosome(normal_data, t13_data, '13', 'T13')
run_svm_for_chromosome(normal_data, t18_data, '18', 'T18')
run_svm_for_chromosome(normal_data, t21_data, '21', 'T21')


