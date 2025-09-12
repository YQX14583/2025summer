import matplotlib.pyplot as plt
import matplotlib.patches as patches

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

def create_flowchart():
    """创建代码思路流程图"""
    fig, ax = plt.subplots(figsize=(16, 12))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 12)
    ax.axis('off')

    # 定义颜色
    colors = {
        'data': '#FFE4E1',  # 数据准备 - 浅粉色
        'model': '#E6E6FA',  # 建模 - 淡紫色
        'group': '#F0FFF0',  # 分组 - 蜜瓜绿
        'risk': '#FFF0F5',  # 风险分析 - 薰衣草紫
        'result': '#F0F8FF'  # 结果 - 爱丽丝蓝
    }

    # 定义节点位置和大小
    nodes = {
        'start': (5, 11, '开始', '#DDA0DD'),
        'data_extract': (5, 9.5, '数据提取\n提取达标时间', colors['data']),
        'data_clean': (5, 8, '数据清洗\n剔除异常值', colors['data']),
        'svr_model': (5, 6.5, 'SVR建模\n建立BMI-时间关系', colors['model']),
        'residual_cdf': (3, 5, '残差分析\n计算CDF函数', colors['model']),
        'inflection': (7, 5, '拐点检测\n二阶导数分析', colors['model']),
        'grouping': (5, 3.5, '智能分组\n基于拐点划分', colors['group']),
        'risk_analysis': (3, 2, '风险计算\n未达标+延误风险', colors['risk']),
        'optimization': (7, 2, '时间优化\n最小化总风险', colors['risk']),
        'sensitivity': (5, 0.5, '敏感性分析\n误差影响评估', colors['result']),
        'end': (5, -1, '输出结果\n最佳检测时间', '#98FB98')
    }

    # 绘制节点
    for x, y, text, color in nodes.values():
        if text == '开始' or text == '输出结果\n最佳检测时间':
            # 椭圆节点
            ellipse = patches.Ellipse((x, y), 1.5, 0.8, fc=color, ec='black', lw=2)
            ax.add_patch(ellipse)
            ax.text(x, y, text, ha='center', va='center', fontsize=10, fontweight='bold')
        else:
            # 矩形节点
            rect = patches.Rectangle((x - 1.2, y - 0.4), 2.4, 0.8, fc=color, ec='black', lw=2)
            ax.add_patch(rect)
            ax.text(x, y, text, ha='center', va='center', fontsize=9)

    # 绘制连接线
    connections = [
        ('start', 'data_extract'),
        ('data_extract', 'data_clean'),
        ('data_clean', 'svr_model'),
        ('svr_model', 'residual_cdf'),
        ('svr_model', 'inflection'),
        ('residual_cdf', 'risk_analysis'),
        ('inflection', 'grouping'),
        ('grouping', 'risk_analysis'),
        ('grouping', 'optimization'),
        ('risk_analysis', 'optimization'),
        ('optimization', 'sensitivity'),
        ('sensitivity', 'end')
    ]

    for start, end in connections:
        x1, y1, _, _ = nodes[start]
        x2, y2, _, _ = nodes[end]

        # 调整箭头位置
        if start == 'svr_model' and end == 'residual_cdf':
            y1 = y1 - 0.4
            x2 = x2 + 0.5
        elif start == 'svr_model' and end == 'inflection':
            y1 = y1 - 0.4
            x2 = x2 - 0.5

        ax.annotate('', xy=(x2, y2 + 0.4), xytext=(x1, y1 - 0.4),
                    arrowprops=dict(arrowstyle='->', lw=1.5, color='black'))

    # 添加注释
    ax.text(1, 10.5, '数据准备阶段', fontsize=12, fontweight='bold', color='darkred')
    ax.text(1, 6.8, '建模分析阶段', fontsize=12, fontweight='bold', color='darkblue')
    ax.text(1, 4.2, '分组策略阶段', fontsize=12, fontweight='bold', color='darkgreen')
    ax.text(1, 1.2, '风险优化阶段', fontsize=12, fontweight='bold', color='purple')
    ax.text(1, -0.3, '结果输出阶段', fontsize=12, fontweight='bold', color='darkcyan')

    plt.title('SVR风险评估解决方案流程图', fontsize=16, fontweight='bold', pad=20)
    plt.tight_layout()
    plt.show()


# 绘制流程图
create_flowchart()