import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix, ConfusionMatrixDisplay
import matplotlib.pyplot as plt
import warnings
from imblearn.over_sampling import SMOTE  # 导入SMOTE用于过采样

warnings.filterwarnings('ignore')

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

# ---------- 1. 数据加载 ----------
normal_data = pd.read_excel("normal_data.xlsx")
t13_data = pd.read_excel("T13_data.xlsx")
t18_data = pd.read_excel("T18_data.xlsx")
t21_data = pd.read_excel("T21_data.xlsx")


# ---------- 2. 添加有效测序量 ----------
def add_effective_sequencing(data):
    """ 计算有效测序量并添加到数据集中 """
    data['有效测序量'] = (data['原始读段数'] *
                          data['在参考基因组上比对的比例'] *
                          (1 - data['重复读段的比例']) *
                          (1 - data['被过滤掉读段数的比例']))
    return data


normal_data = add_effective_sequencing(normal_data)
t13_data = add_effective_sequencing(t13_data)
t18_data = add_effective_sequencing(t18_data)
t21_data = add_effective_sequencing(t21_data)

# ---------- 3. 特征定义 ----------
features_t13_t18_t21 = [
    "X染色体的Z值（绝对值）", "13号染色体的Z值（绝对值）", "GC含量", "有效测序量", "孕妇BMI"
]
features_t18 = [
    "X染色体的Z值（绝对值）", "18号染色体的Z值（绝对值）", "GC含量", "有效测序量", "孕妇BMI"
]
features_t21 = [
    "X染色体的Z值（绝对值）", "21号染色体的Z值（绝对值）", "GC含量", "有效测序量", "孕妇BMI"
]


# ---------- 4. 随机森林训练与评估 ----------
def train_and_evaluate_rf(task_name, normal_data, abnormal_data, features):
    """
    使用随机森林训练并评估某异常判定任务。
    task_name: 当前任务名称（例如 "T13"）
    normal_data, abnormal_data: 数据集（正常与异常样本）
    features: 用于训练的特征列
    """
    # 1. 添加分类标签
    normal_data["标签"] = 0  # 正常样本标记为 0
    abnormal_data["标签"] = 1  # 异常样本标记为 1
    task_data = pd.concat([normal_data, abnormal_data], axis=0).reset_index(drop=True)

    # 2. 数据预处理：提取特征和标签
    X = task_data[features]
    y = task_data["标签"]
    if X.isnull().sum().any():  # 处理缺失值
        X.fillna(X.mean(), inplace=True)
    scaler = StandardScaler()  # 数据标准化
    X_scaled = scaler.fit_transform(X)

    # 3. 使用SMOTE进行过采样（平衡数据）
    smote = SMOTE(sampling_strategy='auto', random_state=42)
    X_resampled, y_resampled = smote.fit_resample(X_scaled, y)

    # 4. 划分训练集和测试集
    X_train, X_test, y_train, y_test = train_test_split(
        X_resampled, y_resampled, test_size=0.2, random_state=42, stratify=y_resampled
    )

    # 5. 初始化和训练随机森林分类器
    model = RandomForestClassifier(
        n_estimators=100,  # 树的数量
        max_depth=None,  # 树的最大深度，不限制
        min_samples_split=2,  # 节点分裂时的最小样本数
        class_weight="balanced",  # 自动处理类别不平衡问题
        random_state=42
    )
    model.fit(X_train, y_train)

    # 6. 模型评估
    print(f"--- {task_name} 模型评估 ---")
    y_pred = model.predict(X_test)
    print("分类报告:\n", classification_report(y_test, y_pred, target_names=["正常", f"{task_name}异常"]))

    cm = confusion_matrix(y_test, y_pred)
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=["正常", f"{task_name}异常"])
    disp.plot(cmap="Blues")
    plt.title(f"{task_name} 混淆矩阵")
    plt.show()

    # 7. 特征重要性分析
    feature_importances = model.feature_importances_
    importance_df = pd.DataFrame({
        "特征": features,
        "重要性": feature_importances
    }).sort_values(by="重要性", ascending=False)

    print(f"\n{task_name} 特征重要性分析: \n", importance_df)

    # 特征重要性可视化
    plt.figure(figsize=(10, 6))
    plt.barh(importance_df["特征"], importance_df["重要性"], color="skyblue")
    plt.title(f"{task_name} 特征重要性")
    plt.xlabel("重要性值")
    plt.ylabel("特征")
    plt.gca().invert_yaxis()  # 反转Y轴方便观察
    plt.show()

    # 8. 判定新样本的函数
    def rf_classifier(features_values):
        """ 使用训练好的随机森林模型对新样本进行判定。 """
        standardized_features = scaler.transform([features_values])
        prediction = model.predict(standardized_features)[0]
        return "异常" if prediction == 1 else "正常"

    return rf_classifier


# ---------- 5. 训练并评估模型 ----------
# 针对 T13 异常判定
t13_rf_classifier = train_and_evaluate_rf("T13", normal_data.copy(), t13_data.copy(), features_t13_t18_t21)

# 针对 T18 异常判定
t18_rf_classifier = train_and_evaluate_rf("T18", normal_data.copy(), t18_data.copy(), features_t18)

# 针对 T21 异常判定
t21_rf_classifier = train_and_evaluate_rf("T21", normal_data.copy(), t21_data.copy(), features_t21)
