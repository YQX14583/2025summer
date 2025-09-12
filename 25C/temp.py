# 设置中文显示
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

# ---------- 1. 数据加载 ----------
# 请替换为实际路径，分别加载正常样本以及 T13、T18、T21 异常样本数据
normal_file = "normal_data.xlsx"
t13_file = "T13_data.xlsx"
t18_file = "T18_data.xlsx"
t21_file = "T21_data.xlsx"

# 读取数据
normal_data = pd.read_excel(normal_file)
t13_data = pd.read_excel(t13_file)
t18_data = pd.read_excel(t18_file)
t21_data = pd.read_excel(t21_file)