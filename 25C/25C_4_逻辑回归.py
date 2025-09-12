import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, ConfusionMatrixDisplay, roc_auc_score
import matplotlib.pyplot as plt
import warnings

warnings.filterwarnings('ignore')

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

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


# ---------- 2. 为特定染色体异常判定定义函数 ----------
def train_and_evaluate_lr(task_name, normal_df, abnormal_df, target_chromosome):
    """
    使用逻辑回归训练并评估某条染色体异常的判定模型。

    task_name: 任务名称，如 "T13"
    normal_df, abnormal_df: 正常和异常数据集
    target_chromosome: 目标染色体号，如 "13"
    """

    # 2.1 定义精准的特征集
    features = [
        f'X染色体的Z值（绝对值）',
        f'{target_chromosome}号染色体的Z值（绝对值）',
        'GC含量',
        '有效测序量',
        '孕妇BMI'
    ]

    # 2.2 准备数据
    normal_df["标签"] = 0  # 正常样本标记为 0
    abnormal_df["标签"] = 1  # 异常样本标记为 1
    combined_data = pd.concat([normal_df, abnormal_df], axis=0).reset_index(drop=True)

    X = combined_data[features]
    y = combined_data["标签"]

    # 处理缺失值（用均值填充）
    X.fillna(X.mean(), inplace=True)

    # 2.3 数据标准化 (非常重要！)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # 2.4 划分训练集和测试集
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.2, random_state=42, stratify=y
    )

    # 2.5 训练逻辑回归模型
    # 使用 'balanced' 模式自动调整类别权重，处理数据不平衡
    model = LogisticRegression(
        class_weight='balanced',
        random_state=42,
        max_iter=1000  # 确保收敛
    )
    model.fit(X_train, y_train)

    # 2.6 模型评估
    print(f"\n\n=== {task_name} 逻辑回归模型评估 ===")
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]  # 获取异常的概率

    print("分类报告:")
    print(classification_report(y_test, y_pred, target_names=["正常", f"{task_name}异常"]))
    print(f"AUC Score: {roc_auc_score(y_test, y_pred_proba):.4f}")

    # 2.7 混淆矩阵可视化
    cm = confusion_matrix(y_test, y_pred)
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=["正常", f"{task_name}异常"])
    disp.plot(cmap="Blues")
    plt.title(f"{task_name} 混淆矩阵")
    plt.show()

    # 2.8 ★★★ 模型可解释性分析 ★★★
    print(f"\n{task_name} 模型系数与OR值分析:")
    # 获取系数和截距
    coefficients = model.coef_[0]
    intercept = model.intercept_[0]

    # 计算OR值 (Odds Ratio)
    odds_ratios = np.exp(coefficients)

    # 创建结果DataFrame
    result_df = pd.DataFrame({
        '特征': features,
        '系数': coefficients,
        'OR值': odds_ratios
    })
    result_df = result_df.sort_values('OR值', ascending=False)

    print(result_df.to_string(index=False))

    # 2.9 可视化特征重要性（通过OR值）
    plt.figure(figsize=(10, 6))
    bars = plt.barh(result_df['特征'], result_df['OR值'], color=['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#6F1D1B'])
    plt.title(f'{task_name} 特征OR值 (OR > 1 增加风险，OR < 1 降低风险)')
    plt.xlabel('OR值')
    plt.axvline(x=1, color='gray', linestyle='--', linewidth=1)  # 添加参考线
    # 在条形上添加数值标签
    for bar in bars:
        width = bar.get_width()
        plt.text(width + 0.02, bar.get_y() + bar.get_height() / 2, f'{width:.2f}', ha='left', va='center')
    plt.tight_layout()
    plt.show()

    # 2.10 返回模型和标准化器，用于新样本预测
    return model, scaler, features


# ---------- 3. 训练并评估三个模型 ----------
print("开始训练女胎染色体异常判定模型...")

# 训练T13模型
lr_model_t13, scaler_t13, features_t13 = train_and_evaluate_lr("T13", normal_data.copy(), t13_data.copy(), "13")

# 训练T18模型
lr_model_t18, scaler_t18, features_t18 = train_and_evaluate_lr("T18", normal_data.copy(), t18_data.copy(), "18")

# 训练T21模型
lr_model_t21, scaler_t21, features_t21 = train_and_evaluate_lr("T21", normal_data.copy(), t21_data.copy(), "21")


# ---------- 4. 新样本预测函数 ----------
def predict_new_sample(model, scaler, feature_names, sample_data):
    """
    预测一个新样本
    sample_data: 一个字典或列表，包含特征值，顺序与feature_names一致
    """
    # 如果是字典，转换为按feature_names顺序的数组
    if isinstance(sample_data, dict):
        sample_array = np.array([sample_data[feat] for feat in feature_names]).reshape(1, -1)
    else:
        sample_array = np.array(sample_data).reshape(1, -1)

    # 标准化
    sample_scaled = scaler.transform(sample_array)

    # 预测概率和类别
    probability = model.predict_proba(sample_scaled)[0, 1]  # 异常的概率
    prediction = model.predict(sample_scaled)[0]

    return {
        '异常概率': probability,
        '预测类别': '异常' if prediction == 1 else '正常',
        '判定阈值': 0.5  # 可以自定义阈值
    }


# 示例：预测一个T21的新样本
example_sample_t21 = {
    'X染色体的Z值（绝对值）': 0.5,
    '21号染色体的Z值（绝对值）': 3.0,  # 很高的Z值，预示高风险
    'GC含量': 0.40,
    '有效测序量': 3000000,
    '孕妇BMI': 28.0
}

result = predict_new_sample(lr_model_t21, scaler_t21, features_t21, example_sample_t21)
print(f"\nT21新样本预测结果: {result}")

