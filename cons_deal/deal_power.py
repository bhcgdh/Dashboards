# -*-coding:utf-8 -*-
import pandas as pd
import warnings
warnings.filterwarnings('ignore')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif']=['SimHei']  #解决中文显示乱码问题
plt.rcParams['axes.unicode_minus']=False  #解决坐标轴负数的负号显示问题
try:
    from ..plot_show.plotPower import  plot_power_month_sum
except:
    from plot_show.plotPower import  plot_power_month_sum



def deal_power_month_sum(df, per):
    # 统计每个月的用电量值 pw， 每个月数据天数 day
    df1 = df.groupby(['ym2'])['day'].nunique().reset_index()
    df2 = df.groupby(['ym2'])['pw'].sum().reset_index()
    df2['pw'] = df2['pw'] / per
    dfs = pd.merge(df1, df2, how='left', on='ym2')
    return dfs


def deal_power_unit(df, unit):
    if unit in ['MW', 'mw', 'Mw', 'mW']:
        df['pw'] = df['pw'] * 1000

    elif unit in ["GW", "Gw", "gw", "gW"]:
        df['pw'] = df['pw'] * 1000 * 1000

    elif unit in ["W", "w"]:
        df['pw'] = df['pw'] / 1000

    df.reset_index(inplace=True)
    return df

def get_power(df, unit, per):
    df_power = deal_power_unit(df, unit)
    df_power_ms = deal_power_month_sum(df_power, per)

    fig = plot_power_month_sum(df_power, df_power_ms)
    return df_power, df_power_ms, fig


