# -*-coding:utf-8 -*-
import pandas as pd
import datetime
import warnings
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif']=['SimHei']  #解决中文显示乱码问题
plt.rcParams['axes.unicode_minus']=False  #解决坐标轴负数的负号显示问题

warnings.filterwarnings('ignore')
import numpy as np

colors = [(0.424, 0.455, 0.686), (0.596, 0.812, 0.945), (0.984, 0.694, 0.851), (0.482, 0.525, 0.741),
          (0.631, 0.831, 0.671), (0.596, 0.384, 0.478), (0.918, 0.824, 0.808), (0.976, 0.706, 0.455)]

data_week = {1: '一', 2: '二', 3: '三', 4: '四', 5: '五', 6: '六', 7: '日'}
data_season = {1: '一', 2: '二', 3: '三', 4: '四'}
def plot_power_month_sum(df, dfmonth):
    dfm = dfmonth.copy()
    dfm['ym'] = [i[0:7].replace("-", '') for i in dfm['ym2']]

    d1 = str(df.day.min())[0:10]
    d2 = str(df.day.max())[0:10]
    d3 = df.day.nunique()

    k1 = round(dfm.pw.mean(), 2)
    k2 = round(dfm.pw.min(), 2)
    k3 = round(dfm.pw.max(), 2)

    f0 = f"从{d1} 到 {d2} 总计 {d3} 天的数据，"
    f1 = f"平均每个月用电量{k1}kwh"
    f2 = f"月最小用电量{k2}kwh"
    f3 = f"月最大用电量{k3}kwh"
    tit = f0 + f1 + f2 + f3

    fig, ax = plt.subplots(figsize=(17, 6))

    ax.set_title(tit)
    ax.bar(dfm['ym'], dfm['pw'], width=0.3, label='当月总用电量');
    y_limit = int(dfm['pw'].max()) + dfm['pw'].std() * 0.5
    # ax.set_ylim(0, y_limit)  # 设置y坐标的范围
    ax.set_ylabel('月总用电量kwh')

    for m1, m2 in zip(dfm['ym'], dfm['pw']):
        ax.text(m1, m2, f"{int(m2)}")

    ax2 = ax.twinx()
    ax2.plot(dfm['ym'], dfm['day'], color='r', alpha=0.4, label='当月统计天数')
    ax2.scatter(dfm['ym'], dfm['day'], color='r', alpha=0.4)
    ax2.set_ylabel('每个月统计数值的天数')

    ax.legend(loc=2)
    ax2.legend(loc=1);
    return fig


# 每天的功率　共用一个ｘ坐标系
def plot_power_day(df):
    fig, ax = plt.subplots(figsize=(20, 5))
    ax.set_title("真实的每天的用电量数据kw/h",fontsize=15)


    for i, f in df.groupby('day'):
        k = f['season'].values[0]
        ax.plot(f['hourms'],  f['pw'].tolist() , color=colors[k], alpha=0.3)

    step = 4 # 间隔4个点显示

    xlb = df[['hour','minute','hourms']].drop_duplicates().sort_values(by=['hour','minute']).reset_index(drop=True)['hourms']
    xlb = [f"{int(a[0:2])}:{a[-2:]}" for a in xlb ]

    x = range(len(xlb))
    ax.set_xticks(x[::4],  xlb[::4] )

    ax.set_xlabel('time', fontsize=15)
    ax.set_ylabel('用电量', fontsize=12)
    return fig

#　不同周内的时间段功率均值，同一个ｘ坐标系
def plot_power_week_mean(df):
    fig, ax = plt.subplots(figsize=(20,5), fontsize=15)
    ax.set_title("平均每个周内数据,每个时间段内的电量均值/kwh")
    for i, f in df.groupby(['dayofweek','hourms'])['pw'].mean().groupby('dayofweek'):
        s1 = [i[0:5] for i in f.reset_index()['hourms'].values]
        s2 = [f"{int(a[0:2])}:{a[-2:]}" for a in s1]
        x = range(len(f))
        ax.scatter(x, f.values, label=f'周{data_week[i]}', c=colors[i], alpha=0.7)
        ax.plot(x, f.values , color=colors[i], alpha=0.9)
        step = 4
        ax.set_xlabel('time', fontsize=15)
        ax.set_ylabel('电量/kwh', fontsize=12)
        ax.set_xticks(ticks=x[::step], labels=s2[::step], rotation=50)
        ax.legend()
    return fig

# 不同月的日时间功率均值，连续画图，非共享一个坐标系，呈趋势图
def plot_power_month_mean(df):
    fig, ax = plt.subplots(figsize=(20,3))

    fs = df.groupby(['month','hourms'])['pw'].mean().reset_index()
    fs['x1'] = [f"{int(a[0:2])}:{a[-2:]}" for a in fs['hourms']]
    fs['x'] = [f"{fs['month'][i]}月 {fs['x1'][i]}" for i in fs.index]
    x = range(len(fs))
    xlb = fs['x']
    ax.plot(x, fs['pw'],color=colors[0])
    ax.scatter(x, fs['pw'],color=colors[0], s=0.3)
    ax.bar(x, fs['pw'],color=colors[0], label='平均时间段内电量',width=0.1)

    ax.legend(loc=4)
    step = 32

    ax.set_xticks(x[::step], labels=xlb[::step],rotation=50)
    ax.set_title("月度日用电均值/kwh", fontsize=15)
    ax.set_xlabel('time', fontsize=15)
    ax.set_ylabel('电量均值/kwh', fontsize=12)

    val = int(fs.pw.max())+1
    for ms, ix in enumerate(fs[fs['hourms']=='23-45-00'].index):
        ax.vlines(ix,0,val,color='r',)

        ax.text( ix-step, val, f"{int(ms+1)}月",color='r',alpha=0.8 )
    return fig

#　不同季节内的时间段功率均值，同一个ｘ坐标系
def plot_power_season_mean(df):
    fig, ax = plt.subplots(figsize=(20,5))
    ax.set_title("平均每季节内数据,每个时间段内的电量均值/kwh", fontsize=15)
    for i, f in df.groupby(['season','hourms'])['pw'].mean().groupby('season'):
        s1 = [i[0:5] for i in f.reset_index()['hourms'].values]
        s2 = [f"{int(a[0:2])}:{a[-2:]}" for a in s1]
        x = range(len(f))
        ax.scatter(x, f.values, label=f'第{i}季', c=colors[i], alpha=0.7)
        ax.plot(x, f.values , color=colors[i], alpha=0.9)
        step = 4
        ax.set_xlabel('time', fontsize=15)
        ax.set_ylabel('电量/kwh', fontsize=12)
        ax.set_xticks(ticks=x[::step], labels=s2[::step], rotation=50)
        ax.legend()
    return fig

# 每天唯一值的个数，统计查看，如当天只有2个唯一值的天数
def plot_power_nunique_count(df):
    f1 = df.groupby(['day'])['pw'].nunique().reset_index()
    f1 = pd.merge(f1, df.groupby(['day'])['pw'].sum().reset_index().rename(columns={'pw':'sum'}), how='left', on='day')
    f1['sum'] = round(f1['sum']/4,3)

    f2 = f1['pw'].value_counts().sort_index().reset_index().rename(columns={'index':'nunique','pw':'count'})

    a1,a2 = list(f2.head(1).values[0])
    v1 = f"当天只有{a1}个不重复的值，这样的数据有{a2}天"

    a1,a2 = list(f2.head(2).tail(1).values[0])
    v2 = f"当天只有{a1}个不重复的值，这样的数据有{a2}天"

    fig, ax = plt.subplots(figsize=(20,3))
    # ax.plot(f2['nunique'],f2['count'])
    ax.set_title(f"每天唯一值的个数,例如：{v1}, {v2}", fontsize=15)
    ax.set_xlabel('当日不重复数据，即唯一值的个数',fontsize=15)
    ax.set_ylabel('天数')
    ax.bar(f2['nunique'],f2['count'],width=0.3,color='r',alpha=0.3)
    return fig, f1
# fig,f1 = plot_power_nunique_count(df)

# 每天值过小的日数据，共享相同的x坐标轴
def plot_power_nunique_low_day(df, param=None):
    if param is None:
        param_freq_sum = 4
        pw_unique = 15
        pw_sum_min = 0
        pw_sum_max = 200
    else:
        # param['param_freq_sum']=4
        # param['pw_unique']=15
        # param['pw_sum_min']=0
        # param['pw_sum_max']=200
        param_freq_sum = param['param_freq_sum']
        pw_unique = param['pw_unique']
        pw_sum_min = param['pw_sum_min']
        pw_sum_max = param['pw_sum_max']

    _, f1 = plot_power_nunique_count(df)
    days = f1[(f1['pw'] < pw_unique) & (f1['sum'] > pw_sum_min) & (f1['sum'] < pw_sum_max)]['day'].tolist()
    dfs = df[df['day'].isin(days)]

    # 当数据偏移均值3倍方差的值，用均值替换，防止结果突太
    m1, m2 = dfs['pw'].mean(), dfs['pw'].std()
    m3 = m1 + m2 * 10
    dfs.loc[dfs[dfs['pw'] > m3].index, 'pw'] = m1

    fig, ax = plt.subplots(figsize=(20, 3))
    colors2 = colors * (len(days))
    ax.set_title(f"筛选出，每天功率值唯一值最多{pw_unique}个，当日电量值在{pw_sum_min} - {pw_sum_max}PWh值之间", fontsize=15)
    for i, (d, f) in enumerate(dfs.groupby('day')):
        ax.plot(f['hourms'], f['pw'].tolist(), color=colors2[i])
        ax.set_xticks(f['hourms'][::4], f['hourms'][::4], rotation=55)
    ax.set_xlabel('time', fontsize=15)
    ax.set_ylabel('pw/kwh', fontsize=12)
    return fig, days
# fig,days = plot_power_nunique_low_day(df)

# 随机展示30天异常的数据，
def plot_power_nunique_low_day30(df, days, fignum=30, param=None):
    if param is None:
        param_freq_sum = 4
    else:
        param_freq_sum = param['param_freq_sum']
    # days = f1[(f1['pw']<15)&(f1['sum']>0)&(f1['sum']<200)]['day'].tolist()
    k = min(fignum, len(days))
    days2 = days[0:k]

    n1 = len(days2)
    n2 = 5
    n3 = int(np.ceil(n1 / n2))
    fig, axs = plt.subplots(n3, n2, figsize=(20, 4 * n3))
    for i, day in enumerate(days2):
        row = int(i // n2)
        col = int(i % n2)
        ax = axs[row, col]
        fs = df[df['day'] == day]

        s1 = [i[0:5] for i in fs.reset_index()['hourms'].values]
        s2 = [f"{int(a[0:2])}:{a[-2:]}" for a in s1]

        tit = f"{str(day)[0:10]} 用电 {round(fs['pw'].sum() / param_freq_sum, 2)}kwh"
        ax.set_title(tit, fontsize=15)
        x = range(len(fs))
        ax.plot(x, fs['pw'], color=colors[0])
        ax.set_xticks(x[::16], s2[::16], rotation=50)
        ax.set_xlabel('time')
        ax.set_ylabel('pw/kwh')
    return fig
#fig = plot_power_nunique_low_day30(df,days)

