import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, roc_auc_score
import matplotlib.pyplot as plt
from imblearn.over_sampling import SMOTE  # 关键：用于过采样
import warnings
from sklearn.model_selection import StratifiedKFold, cross_val_score


# ---------- 1. 数据加载与预处理 ----------
# [您的数据加载代码保持不变]
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
# ---------- 2. 混合模型策略 ----------
def train_hybrid_model(task_name, normal_df, abnormal_df, target_chromosome):
    """
    使用RF+LR混合策略处理极端不平衡数据
    """

    # 2.1 定义特征集
    features = [
        f'X染色体的Z值（绝对值）',
        f'{target_chromosome}号染色体的Z值（绝对值）',
        'GC含量',
        '有效测序量',
        '孕妇BMI'
    ]

    # 2.2 准备数据
    normal_df["标签"] = 0
    abnormal_df["标签"] = 1
    combined_data = pd.concat([normal_df, abnormal_df], axis=0).reset_index(drop=True)

    X = combined_data[features]
    y = combined_data["标签"]

    print(f"\n{task_name} 数据分布: 正常={sum(y == 0)}, 异常={sum(y == 1)}, 比例={sum(y == 0) / sum(y == 1):.1f}:1")

    X.fillna(X.mean(), inplace=True)

    # 2.3 数据标准化
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # 2.4 使用SMOTE解决极端不平衡问题
    smote = SMOTE(sampling_strategy='auto', random_state=42)
    X_resampled, y_resampled = smote.fit_resample(X_scaled, y)

    # 2.5 划分训练测试集
    X_train, X_test, y_train, y_test = train_test_split(
        X_resampled, y_resampled, test_size=0.2, random_state=42, stratify=y_resampled
    )

    # 2.6 第一层：随机森林
    print("训练随机森林...")
    rf_model = RandomForestClassifier(
        n_estimators=100,
        class_weight='balanced',
        random_state=42
    )
    rf_model.fit(X_train, y_train)

    # 获取RF的预测概率作为新特征
    X_train_rf_feature = rf_model.predict_proba(X_train)[:, 1]
    X_test_rf_feature = rf_model.predict_proba(X_test)[:, 1]

    # 2.7 第二层：构建新的特征集（RF概率 + 最重要的原始特征）
    # 选择Z值作为最重要的临床特征
    z_value_index = features.index(f'{target_chromosome}号染色体的Z值（绝对值）')
    X_train_z = X_train[:, z_value_index]
    X_test_z = X_test[:, z_value_index]

    X_train_new = np.column_stack([X_train_rf_feature, X_train_z])
    X_test_new = np.column_stack([X_test_rf_feature, X_test_z])

    # 2.8 第二层：逻辑回归
    print("训练逻辑回归...")
    lr_model = LogisticRegression(random_state=42, max_iter=1000)
    lr_model.fit(X_train_new, y_train)

    # 2.9 模型评估
    print(f"\n=== {task_name} 混合模型评估 ===")
    y_pred = lr_model.predict(X_test_new)
    y_pred_proba = lr_model.predict_proba(X_test_new)[:, 1]

    print("分类报告:")
    print(classification_report(y_test, y_pred, target_names=["正常", f"{task_name}异常"]))
    print(f"AUC Score: {roc_auc_score(y_test, y_pred_proba):.4f}")

    # 2.10 可解释性分析
    print(f"\n{task_name} 逻辑回归系数:")
    print(f"RF异常概率 系数: {lr_model.coef_[0][0]:.4f}, OR值: {np.exp(lr_model.coef_[0][0]):.4f}")
    print(f"Z值特征 系数: {lr_model.coef_[0][1]:.4f}, OR值: {np.exp(lr_model.coef_[0][1]):.4f}")
    print(f"截距: {lr_model.intercept_[0]:.4f}")

    return rf_model, lr_model, scaler, features


# ---------- 3. 训练模型 ----------
print("开始训练混合模型...")

# 训练三个模型
rf_model_t13, lr_model_t13, scaler_t13, features_t13 = train_hybrid_model("T13", normal_data.copy(), t13_data.copy(),
                                                                          "13")
rf_model_t18, lr_model_t18, scaler_t18, features_t18 = train_hybrid_model("T18", normal_data.copy(), t18_data.copy(),
                                                                          "18")
rf_model_t21, lr_model_t21, scaler_t21, features_t21 = train_hybrid_model("T21", normal_data.copy(), t21_data.copy(),
                                                                            "21")