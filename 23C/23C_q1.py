import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl

# 设置中文字体和负号显示
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号
mpl.rcParams['font.size'] = 20  # 设置字体大小

# 加载xlsx数据
df_sales = pd.read_excel('23年C题/附件2.xlsx')  # 销售流水
df_info = pd.read_excel('23年C题/附件1.xlsx')   # 商品信息
df_merged = pd.merge(df_sales, df_info, on='单品编码', how='left')

# 检查有哪些品类
unique_categories = df_merged['分类名称'].unique()
print("所有品类名称:", unique_categories)
print("品类数量:", len(unique_categories))

# 按品类分组计算总销量
category_sales = df_merged.groupby('分类名称')['销量(千克)'].sum().sort_values(ascending=False)

print("\n各品类总销量统计：")
for category, sales in category_sales.items():
    print(f"{category}: {sales:,.0f} 千克")

# 创建图形和坐标轴
fig, ax = plt.subplots(figsize=(14, 8))

# 定义美观的颜色方案
colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD']

# 绘制柱状图
bars = ax.bar(range(len(category_sales)), category_sales.values,
              color=colors, alpha=0.8, edgecolor='black', linewidth=1.2)

# 在每个柱子上方添加数值标签
for i, (category, sales) in enumerate(category_sales.items()):
    ax.text(i, sales + max(category_sales.values) * 0.01,
            f'{sales:,.0f}',
            ha='center', va='bottom', fontweight='bold', fontsize=18, color='#333333')

# 设置标题和标签
ax.set_title(' 蔬菜六大品类总销售量分布 ', fontsize=20, fontweight='bold', pad=20)
ax.set_xlabel('品类名称', fontsize=20, fontweight='bold')
ax.set_ylabel('总销量（千克）', fontsize=20, fontweight='bold')

# 设置x轴刻度标签
ax.set_xticks(range(len(category_sales)))
ax.set_xticklabels(category_sales.index, rotation=45, ha='right')

# 美化图形
ax.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5)
ax.spines[['top', 'right']].set_visible(False)

# 添加背景色
ax.set_facecolor('#f8f9fa')

# 自动调整布局
plt.tight_layout()

# 显示图形
plt.show()
'''

'''
# 5. 创建饼状图
fig, ax = plt.subplots(figsize=(10, 8))

# 定义颜色方案
colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD']

# 绘制饼状图
wedges, texts, autotexts = ax.pie(category_sales.values,
                                  labels=category_sales.index,
                                  colors=colors,
                                  autopct='%1.1f%%',
                                  startangle=90,
                                  shadow=True,
                                  explode=[0.05] * len(category_sales))  # 让每块稍微分离

# 美化百分比文字
for autotext in autotexts:
    autotext.set_color('white')
    autotext.set_fontsize(20)
    autotext.set_fontweight('bold')

# 设置标题
ax.set_title(' 蔬菜六大品类销量占比分布 ', fontsize=20, fontweight='bold', pad=20)

# 添加图例
ax.legend(wedges,
          [f'{cat}: {sales:,.0f}kg' for cat, sales in category_sales.items()],
          title="品类销量",
          loc="center left",
          bbox_to_anchor=(1, 0, 0.5, 1))

# 确保饼图是圆形
ax.axis('equal')

# 自动调整布局
plt.tight_layout()

# 显示图形
plt.show()

# 3. 确定销量列名（根据实际情况修改）
sales_column = '销量(千克)'

# 4. 转换日期格式（确保日期列是datetime类型）
df_merged['销售日期'] = pd.to_datetime(df_merged['销售日期'])

# 5. 按日期和品类分组，计算每日销量
daily_sales = df_merged.groupby(['销售日期', '分类名称'])[sales_column].sum().reset_index()

# 6. 数据透视，让每个品类成为一列
pivot_df = daily_sales.pivot(index='销售日期', columns='分类名称', values=sales_column).fillna(0)

# 7. 定义要分组的品类
group1_categories = ['花菜类', '食用菌', '花叶类']
group2_categories = ['辣椒类', '水生根茎类', '茄类']

# 增强版：使用不同的线型和颜色
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(18, 14))

# 定义颜色和线型
colors_group1 = ['#FF6B6B', '#4ECDC4', '#45B7D1']  # 红、青绿、蓝
colors_group2 = ['#96CEB4', '#FFEAA7', '#DDA0DD']  # 绿、黄、紫

# 第一组图
for i, category in enumerate(group1_categories):
    if category in pivot_df.columns:
        ax1.plot(pivot_df.index, pivot_df[category],
                color=colors_group1[i],
                markersize=4,
                linewidth=2.5,
                label=category,
                alpha=0.9)

ax1.set_title(' 第一组：花菜类、食用菌、花叶类 - 日销量趋势 ', fontsize=16, fontweight='bold', pad=20)
ax1.set_ylabel('日销量(千克)', fontsize=13, fontweight='bold')
ax1.legend(loc='best', fontsize=12, shadow=True)
ax1.grid(True, alpha=0.2, linestyle='-')
ax1.tick_params(axis='x', rotation=45)

# 第二组图
for i, category in enumerate(group2_categories):
    if category in pivot_df.columns:
        ax2.plot(pivot_df.index, pivot_df[category],
                color=colors_group2[i],
                markersize=4,
                linewidth=2.5,
                label=category,
                alpha=0.9)

ax2.set_title(' 第二组：辣椒类、水生根茎类、茄类 - 日销量趋势 ', fontsize=16, fontweight='bold', pad=20)
ax2.set_xlabel('日期', fontsize=13, fontweight='bold')
ax2.set_ylabel('日销量(千克)', fontsize=13, fontweight='bold')
ax2.legend(loc='best', fontsize=12, shadow=True)
ax2.grid(True, alpha=0.2, linestyle='-')
ax2.tick_params(axis='x', rotation=45)

plt.tight_layout()
plt.show()
