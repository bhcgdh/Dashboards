# -*-coding:utf-8 -*-
import pandas as pd
import datetime
import warnings

warnings.filterwarnings('ignore')
import numpy as np
import streamlit as st

def df_reset(df):
    df.sort_values(by='t', inplace=True)
    df = df.reset_index(drop=True)
    return df

def deal_val_non_num(df, val):
    """ 数据转为数值类型，但是可能存在异常数据，不可转换"""
    non_num = []  # 记录所有非数值类型数据
    for i in df[val]:
        try:
            float(i)
        except:
            df[val].replace(i, np.NaN, inplace=True)
            non_num.append(i)
    df[val] = df[val].astype(float)
    df['pw'] = df[val]
    return df, non_num

def deal_val_fillna(df):
    df = df_reset(df)
    # 剩余的进行填充，使用月小时均值》季小时均值》整体小时均值
    # df['pw'] = df.groupby(['month', 'hourms'], sort=False)['pw'].apply(lambda x: x.fillna(x.mean())).reset_index()['pw']
    # df['pw'] = df.groupby(['season', 'hourms'], sort=False)['pw'].apply(lambda x: x.fillna(x.mean())).reset_index()['pw']
    # df['pw'] = df.groupby(['hourms'], sort=False)['pw'].apply(lambda x: x.fillna(x.mean())).reset_index()['pw']
    # df.fillna(0, inplace=True)
    df['pw'] = df['pw'].fillna(df.groupby('hourms')['pw'].transform('mean'))

    return df

def deal_val_diff(df, val, daycount):

    """ 可能数据是累计值，即每个数据都比前一个数据大
    即有5天的数据，当天有90个点值都比前一个值大，则进行diff处理"""
    a1 = df.groupby('day')['pw'].count()
    a2 = df.groupby('day')['pw'].sum()
    a3 = df[df['pw'] == 0].groupby('day')['pw'].count()
    a4 = pd.merge(a1.reset_index(), a2.reset_index(), how='left', on='day').merge(a3.reset_index(), how='left',
                                                                                  on='day')
    a4.columns = ['day', 'count', 'sum', 'zeroct']
    a4.fillna(0, inplace=True)
    tmp = df.groupby('day')['pw'].sum().mean() * 0.9
    # 1 当天数据没有缺失值，当天的功率值大于均值的0.9倍，当天0值的个数最多占一半的10天，
    a5 = a4[(a4['count'] == daycount) & (a4["sum"] >= tmp) & (a4['zeroct'] < 0.5 * daycount)]['day'].tolist()[0:10]
    # df_count = df.groupby('day')[val].count().reset_index()
    df2 = df[df['day'].isin(a5[0:20])]
    s = []
    for i, f in df2.groupby('day'):
        tmp = f[val].diff(1)
        tmp1 = np.sum(tmp >= 0)
        if tmp1 > int(daycount)*0.92:
            s.append(True)
    if sum(s) > 5:

        df['pw'] = df[val].diff(1)
    else:
        df['pw'] = df[val]

    return df


def deal_val_lack(df, pa_dayc, pa_delete):
    # 暂时不对缺失的数据进行约束,所有数据使用均值处理
    # 删除缺失值超过 pa_dayc 比例的数据
    if pa_delete is None:
        pa_delete = 0
    if pa_delete > 1:
        pa_delete = pa_delete * 0.01
    dfn = df.groupby('day')['pw'].count().reset_index()  # 每天的个数 
    df2 = df[df['day'].isin(dfn[dfn['pw'] >= pa_delete * pa_dayc]['day'])]
    df2 = df_reset(df2)
    return df2


def deal_val_select_hour(df, hour_start=None, hour_end=None, hours=None):
    if hours is not None:
        df_new = df[df['hour'].isin(hours)]

    elif hour_start is not None and hour_end is not None:
        df_new = df[(df['hour'] >= hour_start) & (df['hour'] <= hour_end)]

    elif hour_start is not None:
        df_new = df[(df['hour'] >= hour_start)]

    elif hour_end is not None:
        df_new = df[(df['hour'] <= hour_end)]

    else:
        df_new = df.copy()

    df_new = df_reset(df_new)
    return df_new


def deal_val_select_day(df, day_start, day_end):
    if day_start is not None and day_end  is not None:
        df_new = df[(df['day'] >= day_start) & (df['day'] <= day_end)]
        
    elif day_start is not None:
        df_new = df[df['day'] >= day_start]

    elif day_end is not None:
        df_new = df[df['day'] <= day_end]

    else:
        df_new = df.copy()

    df_new = df_reset(df_new)
    return df_new

def deal_val_select_week(df, weekin=None,weekout=None):
    if weekin is not None:
        df_new = df[df['dayofweek'].isin(weekin)]
    elif weekout is not None:
        df_new = df[~df['dayofweek'].isin(weekin)]
    df_new = df_reset(df_new)
    return df_new


def deal_val(df, val, dayc=None, delete=None,hour_start=None, hour_end=None, day_start=None, day_end=None):
    """
    :param df: 包含时间和功率数据
    :param val: 功率字段值
    :param dayc: 根据freq间隔时间,计算一天理论数据点个数
    :param delete:删除当日数值个数占比小于90%的日数据
    :param hour_start:筛选每天有效小时的起始值,如7点
    :param hour_end:筛选每天有效小时的末端值,如7点
    :param day_start:筛选开始时间
    :param day_end:筛选结束时间
    :return: 进行处理后的数据
    """
    dayc = int(dayc)
    df, val_non_num = deal_val_non_num(df, val)
    df = deal_val_diff(df, val, dayc)
    df_lack = deal_val_lack(df, dayc, delete)
    df_select_day = deal_val_select_day(df_lack, day_start, day_end)
    df_select_hour = deal_val_select_hour(df_select_day, hour_start, hour_end)

    df = deal_val_fillna(df)
    df_lack = deal_val_fillna(df_lack)
    df_select_day = deal_val_fillna(df_select_day)
    df_select_hour = deal_val_fillna(df_select_hour)

    return df, df_lack, df_select_day, df_select_hour
