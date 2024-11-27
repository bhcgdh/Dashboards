# -*-coding:utf-8 -*-
import pandas as pd
import warnings
try:
    from .deal_pv import get_pv
except:
    from deal_pv import get_pv
warnings.filterwarnings('ignore')
import numpy as np
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif']=['SimHei']  #解决中文显示乱码问题
plt.rcParams['axes.unicode_minus']=False  #解决坐标轴负数的负号显示问题


# 单位统一为kw
def deal_load_unit(df, unit):
    if unit in ['MW', 'mw', 'Mw', 'mW']:
        df['pw'] = df['pw'] * 1000

    elif unit in ["GW", "Gw", "gw", "gW"]:
        df['pw'] = df['pw'] * 1000 * 1000

    elif unit in ["W", "w"]:
        df['pw'] = df['pw'] / 1000
    return df

# 基本推荐值，作为遍历的基础
def deal_load_recom(df):
    pv_std = np.std(df[(df['hour'] >= 9) & (df['hour'] <= 16)].groupby('day')['pw'].sum() / (4 * 6))
    pv_mean = np.mean(df[(df['hour'] >= 9) & (df['hour'] <= 16)].groupby('day')['pw'].sum() / (4 * 6))
    pv_max = int(np.max(df[(df['hour'] >= 9) & (df['hour'] <= 16)].groupby('day')['pw'].sum() / (4 * 6)))
    pv_min = int(pv_mean - pv_std * 0.3)

    return round(pv_min,3), round(pv_mean,3), round(pv_max,3)

# 根据已知负荷和光伏，计算消纳比例
def deal_load_pv_cost_tmp(df):
    s1 = []
    s2 = []
    for m1, m2 in df[['pw', 'pv']].values:
        m1, m2
        if m1 >= m2:
            s1.append(m2)
            s2.append(1)
        else:
            s1.append(m1)
            s2.append(m1 / m2)
    df['cs1'] = s1
    df['cs2'] = s2
    return df

def deal_load_pv_cost(df_load, df_pv):
    if 'pv' in df_load.columns:
        del df_load['pv']
    df = pd.merge(df_load, df_pv, how='left', on=['t','ym','hourms'])
    df = deal_load_pv_cost_tmp(df)
    return df

# 时间筛选，日的选择，小时的选择，周数据选择
def deal_load_pv_select(df,weeks=None,hour_min=0,hour_max=24,day_min=None, day_max=None):
    df_select = df.copy()
    if day_min is not None:
        df_select = df_select[df_select['day']>=day_min]
    if day_max is not None:
        df_select = df_select[df_select['day']<=day_max]
    if weeks is None:
        weeks = [1, 2, 3, 4, 5, 6, 7]
    df_select = df_select[df_select['dayofweek'].isin(weeks)]
    df_select = df_select[(df_select['hour']>=hour_min)&(df_select['hour']<=hour_max)]
    return df_select

def deal_load_pv(df_load, df_ir, scale, eff, weeks=None,hour_min=0,hour_max=24,day_min=None, day_max=None):
    df_pv = get_pv(df_ir, eff=eff, scale=scale, unit='kw')  # 根据装机容量获取 光伏发电量
    df_load_pv = deal_load_pv_cost(df_load, df_pv)  # 拼接光伏和负荷
    df_load_pv_select = deal_load_pv_select(df_load_pv, weeks=weeks, hour_min=hour_min, hour_max=hour_max,
                                            day_min=day_min, day_max=day_max)  # 筛选负荷

    return df_load_pv_select

# 不同光伏装机容量下的消纳比例
def deal_load_pv_all(df_load, df_ir, eff, weeks=None,hour_min=0,hour_max=24,day_min=None, day_max=None):
    """
    :param df_load:负荷数据
    :param df_ir: 辐照度数据
    :param eff: 光伏发电效率
    :param weeks: 约束周收据
    :param hour_min: 约束小时开始时间
    :param hour_max: 约束小时结束时间
    :param day_min: 约束起始日
    :param day_max: 约束结束日
    :return:光伏装机容量和消纳比值（<=1)
    """

    pv_min, pv_mean, pv_max = deal_load_recom(df_load)

    if (pv_max - pv_min) / 100 > 1000:
        dur = 500  # 间隔数据
    else:
        dur = 100
    tmp = []
    for scale in range(int(pv_mean), int(pv_max), dur):
        df_tmp = deal_load_pv(df_load, df_ir, scale, eff, weeks=weeks,hour_min=hour_min,
                              hour_max=hour_max,day_min=day_min, day_max=day_max)
        val = round(df_tmp['cs2'].mean(),3) # 消纳均值
        tmp.append([scale, val])
    tmp = pd.DataFrame(tmp, columns=['装机容量/kw','消纳比']) # 光伏装机容量，整体消纳比例
    return pv_max, pv_mean,  tmp


def deal_every_day(df, scale):
    """ df 是每天的数据 """
    df = deal_load_pv_cost_tmp(df)
    df.dropna(inplace=True)
    df.sort_values(by=['t'], inplace=True)
    df = df.reset_index(drop=True)
    d1 = str(df.day.min())[0:10]
    d2 = str(df.day.max())[0:10]
    d3 = int(df.day.nunique())
    d4 = round(100 * df['cs2'].mean(), 2)
    scale = round(scale, 2)
    tit = f"从{d1}到{d2}总计{d3}天每月日均消纳，{scale}kw光伏，整体日均消纳比是 {d4} %"
    return tit, d4


def deal_month_hour_mean(df):

    df = deal_load_pv_cost_tmp(df)

    """ 输入每天各个分钟数据 》计算每个月的分钟均值 """
    df_new = df.groupby(['ym', 'hourms'])[['pw', 'pv','cs2']].mean().reset_index()
    df_new['hms'] = [i.replace('-', ":") for i in df_new['hourms']]
    df_new['t'] = [df_new['ym'][i] + '-01 ' + df_new['hms'][i] for i in df_new.index]
    df_new['t'] = pd.to_datetime(df_new['t'])
    df_new.sort_values(by='t', inplace=True)
    df_new = df_new.reset_index(drop=True)
    return df_new


def deal_month_hour_mean_show(df, tit):
    df = deal_load_pv_cost_tmp(df)

    # df 是 月度的均值数据
    fig, ax = plt.subplots(figsize=(20, 3))

    ax.set_title(tit)
    x = df.index

    ax.plot(x, df['pw'], color='blue', alpha=0.6, label='负荷')
    ax.plot(x, df['pv'], color='r', label='光伏');

    labels = df[df['hourms'] == '12-00-00']['t'].tolist()
    ticks = df[df['hourms'] == '12-00-00']['t'].index

    ax.set_xticks(ticks=ticks, labels=labels, rotation=40)

    x1 = [round(100 * i, 2) for i in df.groupby('ym')['cs2'].mean().tolist()]
    x2 = [f"{i}%" for i in x1]
    for i in range(len(ticks)):
        ax.text(ticks[i], df['pv'][i], x2[i], )
    ax.legend()
    return fig


def deal_year_hour_mean_show(df, d4):
    df = deal_load_pv_cost_tmp(df)

    fig, ax = plt.subplots(figsize=(20, 3))

    tit = f"整体日均消耗{d4}%"
    ax.set_title(tit)

    dfy = df.groupby(['hourms'])[['pw', 'pv', 'cs2']].mean().reset_index()
    dfy['hour'] = [int(i[0:2]) for i in dfy['hourms']]

    ax.plot(dfy['hourms'], dfy['pw'], color='blue', alpha=0.6, label='负荷')
    ax.plot(dfy['hourms'], dfy['pv'], color='r', label='光伏');

    t1 = dfy['hourms'][::4]
    t2 = dfy['hour'][::4]
    ax.set_xticks(t1, t2)

    ax.legend()

    return fig



