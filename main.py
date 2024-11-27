import warnings
warnings.filterwarnings('ignore')
import numpy as np
import streamlit as st
import time
import datetime
from dateutil.relativedelta import relativedelta
import pandas as pd
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif']=['SimHei']  #解决中文显示乱码问题
plt.rcParams['axes.unicode_minus']=False  #解决坐标轴负数的负号显示问题

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

import photovoltaic as pv
from pvlib.location import Location
from pytz import timezone
import requests



# # 从timestart 到 timeend (间隔 freq) 下太阳辐照度
def get_elevation(lat, long):
    # Query the height of the motherland based on longitude and latitude
    query = ('https://api.open-elevation.com/api/v1/lookup'f'?locations={lat},{long}')
    r = requests.get(query).json()
    elevation = pd.io.json.json_normalize(r, 'results')['elevation'].values[0]
    return elevation

class Base():
    def __init__(self, json):
        keys = json.keys()
        must = ['latitude', 'longitude', 'freq', 'timestart', 'timeend', 'timezone']
        lack = set(must).difference(set(keys))  # 可是
        if len(lack) > 0:
            raise Exception(f'Necessary data is missing and the program cannot continue execution : {lack}')
        try:
            self.name = json['name']  # 站点位置名称
        except:
            pass

        self.latitude = json['latitude']  # 33.4484
        self.longitude = json['longitude']  # -112.074
        try:
            self.altitude = json['altitude']  # 331 给定的海拔高度和网站提供的会有一定的差异，对于计算的结果影响不大
        except:
            self.altitude = get_elevation(self.latitude, self.longitude)
        self.time_zone = json['timezone']  # US / Arizona
        self.time_utcoffset = datetime.datetime.now(timezone(self.time_zone)).utcoffset().total_seconds() / 3600  # 获取时区校正值
        if len(json['timestart']) == 10:
            self.time_start = datetime.datetime.strptime(json['timestart'], '%Y-%m-%d')
            self.time_end = datetime.datetime.strptime(json['timeend'], '%Y-%m-%d')
        else:
            self.time_start = datetime.datetime.strptime(json['timestart'], '%Y-%m-%d %H:%M:%S')
            self.time_end = datetime.datetime.strptime(json['timeend'], '%Y-%m-%d %H:%M:%S')
        if self.time_start > self.time_end:
            raise Exception('wrong data, time_start is greater than time_end')
        self.time_freq = f"{json['freq']}Min"

        try:
            self.type = json['type']
        except:
            self.type = 1

class PVs(Base):

    def get_local_solor_time(self, df):
        return df['hour'] + df[['TimeCorrection', 'minute']].sum(axis=1) / 60

    def get_elev_azi(self, df):
        value = [pv.sun.elev_azi(df['Declination'][i],
                                 self.latitude,
                                 df['LocalSolorTime'][i]) for i in df.index]
        elevation = [i[0] for i in value]  # 海拔高度
        azimuth = [i[1] for i in value]  # 方位角
        return elevation, azimuth

    def get_sun_rise_set(self, df):
        value = [pv.sun.sun_rise_set(self.latitude,
                                     df['Declination'][i],
                                     df['TimeCorrection'][i]
                                     ) for i in df.index]
        sunrise = [i[0] for i in value]  # 海拔高度
        sunset = [i[1] for i in value]  # 方位角
        return sunrise, sunset

    # """ 获取太阳方位角等基本数据，"""
    def get_basic_value(self, df):
        # 1 时间的处理
        df['dayofyear'] = df['time'].dt.dayofyear
        df['hour'] = df['time'].dt.hour
        df['minute'] = df['time'].dt.minute

        # 2 根据时间计算太阳相关度数
        df['Eot'] = df['dayofyear'].apply(lambda x: pv.sun.equation_of_time(x))  # 时间等式
        df['Declination'] = df['dayofyear'].apply(lambda x: pv.sun.declination(x))  # 1 declination， 赤纬角，
        df['TimeCorrection'] = df['Eot'].apply(
            lambda x: pv.sun.time_correction(x, self.longitude, self.time_utcoffset))  # 时间修正系数,每天不一样
        df['LocalSolorTime'] = self.get_local_solor_time(df)  # 本地太阳时间
        df['Elevation'], df['Azimuth'] = self.get_elev_azi(df)  # 计算海拔( Elevation 也称为 solar altitude angle )和太阳方位角度
        df['Sunrise'], df['Sunset'] = self.get_sun_rise_set(df)  # 计算日出日落的时间
        df['Zenith'] = 90 - df['Elevation']
        df['Air_Mass'] = df['Zenith'].apply(lambda x: pv.sun.air_mass(x))  # 空气质量单位，由天顶角获取
        return df

    #  只获取辐照度，不获取其他细数据
    def get_local_pv(self):
        phx = Location(self.latitude, self.longitude, self.time_zone, self.altitude, self.name)
        if len(str(self.time_end)) == 10:
            tmp = datetime.datetime.strptime(str(self.time_end), '%Y-%m-%d') + datetime.timedelta(days=1)
        else:
            tmp = datetime.datetime.strptime(str(self.time_end), '%Y-%m-%d %H:%M:%S') + datetime.timedelta(days=1)

        # times = pd.date_range(self.time_start, tmp, freq=self.time_freq, tz=phx.tz, closed='left')
        times = pd.date_range(self.time_start, tmp, freq=self.time_freq, tz=phx.tz, inclusive='left')

        # times = [i.tz_localize(None) for i in times] # 去掉时区，否则通过 dt.date获取的数据会恢复到正常日期
        # df['t1'] = df['time'].dt.tz_convert(None)  # 2020-11-01 00:00:00+08:00 》2020-10-31 16:00:00
        # df['t2'] = df['time'].dt.tz_localize(None) # 2020-11-01 00:00:00+08:00 》2020-11-01 00:00:00
        # times = pd.date_range(self.time_start, tmp, freq=self.time_freq, closed='left')
        df = phx.get_clearsky(times)
        df['ghi_suns'] = df.ghi / 1000  # ghi就是地面的辐照度，
        # df = df.reset_dinex()¬
        df['time'] = df.index
        df.reset_index(drop=True, inplace=True)
        return df

    # 根据已有时间等数据，获取较为详尽的其他物理数据
    def get_local_pv_all(self):
        if self.type == 1:
            return self.get_local_pv()
        else:
            df = self.get_local_pv()
            return self.get_basic_value(df)

    def do(self):
        return self.get_local_pv_all()


# 1 输入数据是json格式，标准格式，所有数据必须，有缺失则报错，
def input_json():

    json = {}
    json['name'] = 'd1_changyuan'
    json['latitude'] = 33.4484
    json['longitude'] = -112.074
    json['altitude'] = 331
    json['freq'] = '15Min'  # 时间间隔
    json['timestart'] = '2023-01-01'
    json['timeend'] = '2023-01-02'
    json['timezone'] = 'Europe/Bucharest'  # 罗马尼亚
    json['type'] = 1  # 表示只获取辐照度数据, 否则获取其他太阳参数值
    return json

def get_ir(latitude=None, longitude=None, freq=None, timestart=None, timeend=None, timezone=None):
    data = input_json()
    data['latitude'] = data['latitude'] if latitude is None else latitude
    data['longitude'] = data['longitude'] if longitude is None else longitude
    data['freq'] = data['freq'] if freq is None else freq
    data['timestart'] = data['timestart'] if timestart is None else timestart
    data['timeend'] = data['timeend'] if timeend is None else timeend
    data['timezone'] = data['timezone'] if timezone is None else timezone
    df = PVs(data).do()
    df['t'] = [str(i)[0:19] for i in df['time']]
    df['t'] = pd.to_datetime((df['t']))

    df['year'] = df['t'].dt.year
    df['month'] = df['t'].dt.month
    df['ym'] = df['year'].astype(str) + '-' + df['month'].astype(str)  # 年月数据
    df['tmp_m'] = [str(i) if len(str(i)) == 2 else f"0{int(i)}" for i in df['month']]
    df['ym2'] = [str(df['year'][i]) + '-' + str(df['tmp_m'][i]) + "-01" for i in df.index]  # 年月，每个月第一天
    df['ym'] = [i[0:7] for i in df['ym2']]
    df['hourms'] = [datetime.datetime.strftime(i, '%H-%M-%S') for i in df['t']]  # 小时分钟秒
    return df[['t', 'ghi','ym','hourms']]



def df_reset(df):
    df.sort_values(by='t', inplace=True)
    df = df.reset_index(drop=True)
    return df


def deal_val_non_num(df, val):
    # """ 数据转为数值类型，但是可能存在异常数据，不可转换"""
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
    # """ 可能数据是累计值，即每个数据都比前一个数据大
    # 即有5天的数据，当天有90个点值都比前一个值大，则进行diff处理"""
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
        if tmp1 > int(daycount) * 0.92:
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
    if day_start is not None and day_end is not None:
        df_new = df[(df['day'] >= day_start) & (df['day'] <= day_end)]

    elif day_start is not None:
        df_new = df[df['day'] >= day_start]

    elif day_end is not None:
        df_new = df[df['day'] <= day_end]

    else:
        df_new = df.copy()

    df_new = df_reset(df_new)
    return df_new


def deal_val_select_week(df, weekin=None, weekout=None):
    if weekin is not None:
        df_new = df[df['dayofweek'].isin(weekin)]
    elif weekout is not None:
        df_new = df[~df['dayofweek'].isin(weekin)]
    df_new = df_reset(df_new)
    return df_new


def deal_val(df, val, dayc=None, delete=None, hour_start=None, hour_end=None, day_start=None, day_end=None):
    # """
    # # :param df: 包含时间和功率数据
    # # :param val: 功率字段值
    # # :param dayc: 根据freq间隔时间,计算一天理论数据点个数
    # # :param delete:删除当日数值个数占比小于90%的日数据
    # # :param hour_start:筛选每天有效小时的起始值,如7点
    # # :param hour_end:筛选每天有效小时的末端值,如7点
    # # :param day_start:筛选开始时间
    # # :param day_end:筛选结束时间
    # # :return: 进行处理后的数据
    # # """
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


class ReadExcel:
    def __init__(self, file):
        self.file = file

    def read_test1(self):
        try:
            df = pd.read_excel(self.file)
        except:
            df = None
        return df

    def read_test2(self):
        try:
            with open(self.file, encoding='gbk') as f:
                df = pd.read_excel(f)
        except:
            df = None
        return df

    def read_test3(self):
        try:
            with open(self.file, encoding='utf-8') as f:
                df = pd.read_excel(f)
        except:
            df = None
        return df

    def read_xlsx(self):
        i = 0
        read_func = [self.read_test1, self.read_test2, self.read_test3]
        n = len(read_func)
        while i < n:
            df = read_func[0]()
            if df is not None:
                break
        return df

class ReadCsv:
    def __init__(self, file):
        self.file = file

    def read_test1(self):
        try:
            df = pd.read_csv(self.file)
        except:
            df = None
        return df

    def read_test2(self):
        try:
            with open(self.file, encoding='gbk') as f:
                df = pd.read_csv(f)
        except:
            df = None
        return df

    def read_test3(self):
        try:
            with open(self.file, encoding='utf-8') as f:
                df = pd.read_csv(f)
        except:
            df = None
        return df

    def read_csv(self):
        i = 0
        df = None
        read_func = [self.read_test1, self.read_test2, self.read_test3]
        n = len(read_func)
        while i < n:
            df = read_func[0]()
            if df is not None:
                break
        return df

class ReadTable:
    def __init__(self, file):
        self.file = file

    def read_test1(self):
        try:
            df = pd.read_table(self.file)
        except:
            df = None
        return df

    def read_test2(self):
        try:
            with open(self.file, encoding='gbk') as f:
                df = pd.read_table(f)
        except:
            df = None
        return df

    def read_test3(self):
        try:
            with open(self.file, encoding='utf-8') as f:
                df = pd.read_table(f)
        except:
            df = None
        return df

    def read_table(self):
        i = 0
        df = None
        read_func = [self.read_test1, self.read_test2, self.read_test3]
        n = len(read_func)
        while i < n:
            df = read_func[0]()
            if df is not None:
                break
        return df

def read_file_one(file):
    df = None
    if 'csv' in file:
        df = ReadCsv(file).read_csv()

    elif 'xls' in file:
        df = ReadExcel(file).read_xlsx()

    elif 'txt' in file:
        df = ReadTable(file).read_table()

    return df


def read_file_muil(files):
    # files = [f1, f2]
    df = read_file_one(files[0])
    if len(files) > 1:
        for file in files[1:]:
            tmp = read_file_one(file)
            if df.shape[1] == tmp.shape[1]:
                df = df.append(tmp, ignore_index=True)
            # else:
            #     st.write("文件字段不一致导致无法进行拼接")
    return df

def read_file(filename):
    if isinstance(filename,list):
        df = read_file_muil(filename)
    else:
        df = read_file_one(filename)
    df = df.reset_index(drop=True)
    return df
# 1 时间转为时间戳，秒级, 这里没有时区的要求


class DealTime:
    def __init__(self):
        pass
    # ==============   时间转换
    # 时间列表转为时间戳列表
    @staticmethod
    def times_to_stamps(t, types=13):
        # 返回serise格式的数据列
        return [int( (10 ** ( types - 10 ) ) * time.mktime(time.strptime(str(i), "%Y-%m-%d %H:%M:%S"))) for i in t]

    # 单个时间转为单个时间戳
    @staticmethod
    def time_to_stamp(t, types=13):
        return int( (10 ** ( types - 10 ) ) * time.mktime(time.strptime(str(t), "%Y-%m-%d %H:%M:%S")) )

    # 时间戳列表转为时间列表
    @staticmethod
    def stamps_to_times(t, timezone):
        num = len(str(int(t[0])))
        if num == 10:
            unit = 's'
        else:
            unit = 'ms'
        # return [pd.Timestamp(i, unit=unit, tz=timezone) for i in t]
        return [datetime.datetime.strftime(pd.Timestamp(int(i), unit=unit, tz=timezone), "%Y-%m-%d %H:%M:%S") for i in t]


    # 单个时间戳转为datetime64类型"""
    @staticmethod
    def stamp_to_time(t, timezone):
        num = len(str(int(t)))
        if num == 10:
            unit = 's'
        else:
            unit = 'ms'
        return datetime.datetime.strftime(pd.Timestamp(int(t), unit=unit, tz=timezone), "%Y-%m-%d %H:%M:%S")

    # Dataframe数据时间格式转换
    @staticmethod
    def pandas_str_to_time(df, tn='t'):
        try:
            df[tn] = pd.to_datetime(df[tn])
        except ValueError:
            pass

    def data_to_time(self,data, timezone=None):
        # """
        # :param data: 时间相关数据, 支持多种格式数据抓换
        # :return: 将不同格式的数据转为标准的时间格式
        # """
        # 1 10和13位的整数，时间戳 》时间
        if isinstance(data, (int, float)):
            data = self.stamp_to_time(data, timezone)

        # 2 字符类型数据,
        elif isinstance(data, str):
            if len(data)==19:
                data = datetime.datetime.strptime(data, "%Y-%m-%d %H:%M:%S")
            elif len(data)==10:
                data = datetime.datetime.strptime(data, "%Y-%m-%d")
            else:
                raise Exception('wrong length of data')
        elif isinstance(data, datetime.datetime):
            pass
        else:
            raise Exception('unknow data types ')
        return data

    def datas_to_times(self, datas, timezone=None):
        # """
        # :param datas: 时间相关列表
        # :param timezone: 当前时区，默认空
        # :return: 时间列别
        # """
        tmp1, tmp2 = datas[0], len(str(datas[0]))

        # 1 10和13位的整数，时间戳 》时间
        if isinstance(tmp1, (int, float, np.int8, np.int32, np.int64,np.float16, np.float32,np.float64 )):
            datas = [self.stamp_to_time(data, timezone) for data in datas]

        # 2 字符类型数据,
        elif isinstance(tmp1, str):
            if tmp2==19:
                datas =[datetime.datetime.strptime(data, "%Y-%m-%d %H:%M:%S") for data in datas ]
            elif tmp2==10:
                datas =[ datetime.datetime.strptime(data, "%Y-%m-%d") for data in datas]
            else:
                raise Exception('wrong length of data')
        elif isinstance(tmp1, datetime.datetime):
            pass
        else:
            raise Exception('unknow data types ')
        return datas

    # ==============   获取时间的特征，不同颗粒度，不同节假日。
    def get_time_feature(self, df, tn='t'):
        # """
        # :param t: 字符格式，如果是
        # :return: 所有时间特征，
        # """
        try:
            df[tn] = self.datas_to_times(df[tn])
        except:
            raise Exception('cannot change time data to datetime types')

        df['year'] = df[tn].dt.year
        df['month'] = df[tn].dt.month
        df['day'] = df[tn].dt.date
        df['day'] = pd.to_datetime(df['day'])
        df['hour'] = df[tn].dt.hour
        df['minute'] = df[tn].dt.minute
        df['hourms'] = [datetime.datetime.strftime(i, '%H-%M-%S')for i in df[tn]] # 小时分钟秒
        # df['hourms2'] = df['hour']*4 + df['minute']//15
        df['dayofyear'] = df[tn].dt.dayofyear # 一年的第几天
        df['dayofweek'] = df[tn].dt.dayofweek+1 # 一周的第几天
        df['dayofmonth'] = df[tn].dt.day # 一个月的第几天

        df['ym'] = df['year'].astype(str) + '-' + df['month'].astype(str) # 年月数据
        df['tmp_m'] = [str(i) if len(str(i)) == 2 else f"0{int(i)}" for i in df['month']]
        df['ym2'] = [str(df['year'][i]) + '-' + str(df['tmp_m'][i]) + "-01" for i in df.index] # 年月，每个月第一天
        df['ym'] = [i[0:7] for i in df['ym2']]
        try:
            df['weekofyear'] = df[tn].dt.weekofyear # 一年中的第几周
        except:
            df['weekofyear'] = df['t'].dt.isocalendar().week
        df['season'] = df[tn].dt.quarter # 季节
        return df

    # ==============   时间数据的加减计算
    def get_time_calculation(self, data,timezone=None, years=0, months=0, weeks=0, hours=0, days=0,minutes=0, seconds=0):
        # 1 数据转为时间格式，方便后续计算
        data = self.data_to_time(data, timezone)

        # 2 时间加减，注意，用s ,hour表示将小时转为hour,22:00:00 > 10:00:00
        data = data + relativedelta( years=years, months=months, days=days, weeks=weeks,
                                     hours=hours, minutes=minutes, seconds=seconds)
        return data


    def get_time_calculations(self,datas, timezone=None, years=0, months=0,
                              weeks=0, hours=0, days=0,minutes=0, seconds=0):
        # datas是时间列表列表 timezone是在输入的时间是时间戳才需要"""
        datas = self.datas_to_times(datas, timezone)
        datas = [data + relativedelta( years=years, months=months, days=days, weeks=weeks,
                                     hours=hours, minutes=minutes, seconds=seconds) for data in datas]
        return datas

    def get_time_interval(self, data1, data2, types='m',timezone=None):
        # """
        # types: 返回时间的类型，
        #    - s: 两个时间相差的总秒数
        #    - m: 两个时间相差的总分钟，默认该值
        #    - d: 两个时间相差的日数据,不足一天为0
        # """
        data1 = self.data_to_time(data1, timezone)
        data2 = self.data_to_time(data2, timezone)
        delta = data1 - data2
        if types=='m':
            return delta.total_seconds()/60
        elif types=='s':
            return delta.total_seconds()
        elif types=='d':
            return delta.days

    def get_time_intervals(self,datas1, datas2, types='m',timezone=None):
        datas1 = self.datas_to_times(datas1,timezone)
        datas2 = self.datas_to_times(datas2,timezone)
        deltas = [datas1[i]-datas2[i] for i in range(len( datas1 ))]
        if types=='m':
            return [delta.total_seconds()/60 for delta in deltas]
        elif types=='s':
            return [delta.total_seconds() for delta in deltas]
        elif types=='d':
            return [delta.days for delta in deltas]

    # ==============   时间连续性判断
    def judge_time_continuous(self, df, tn='t', freqs='15Min', lack=0.3):
        # """
        # 时间完整性判断，根据输入的dataframe数据，指定时间列名称
        # :param df: 要进行判断的dataframe
        # :param tn: 时间列名称
        # :param freqs:时间间隔
        # :param lack:缺失率，超过这个值，不建议继续进行计算
        # :return: 是否
        # """
        df[tn] = pd.to_datetime(df[tn])
        m1 = df['t'].min()
        m2 = df['t'].max()
        m3 = self.get_time_calculation(str(m2), days=1)
        df['day'] = df['t'].dt.date
        days = df['day'].nunique()

        # if 'D' in freqs:
        #     m3 = self.get_time_calculation( m2, days=1)
        #     df_time = pd.date_range(m1, m3, freq=freqs, closed='left')
        # else:
        #     df_time = pd.date_range(m1, m2, freq=freqs)
        try:
            df_time = pd.date_range(m1, m3, freq='15Min', closed='left') #
        except:
            df_time = pd.date_range(m1, m3, freq='15Min', inclusive='left') #
        df_miss = len(df_time) - len(df)
        per = df_miss/len(df)

        if df_miss > 0:
            ms1 = '从{} 到 {} 共计 {}天 {}条数据，间隔{} 缺失{}条数据'.format(m1, m2, days,len(df), freqs, df_miss)
        else:
            ms1 = '从{} 到 {} 共计 {}天 {}条数据，间隔{} 没有缺失数据'.format(m1, m2, days,len(df), freqs)

        if per>lack:
            ms2 = f'缺失率高于{lack}, 不建议继续进行计算 '
        else:
            ms2 = '缺失率适中，可以进行相关计算'
        df_time = pd.DataFrame(df_time, columns=['t'])
        df = pd.merge(df_time, df, how='left', on=['t'])
        df = self.get_time_feature(df)
        return df, ms1, ms2

    @staticmethod
    def get_time_freq(df, tn='t'):
        df['t'] = pd.to_datetime(df[tn])
        df.sort_values(by='t', inplace=True)
        df = df.reset_index()

        try:
            freq = str(int(df.head(10000).sort_values(by=['t'])['t'].diff(1).astype('timedelta64[m]').value_counts().index[0]))
        except:
            try:
                freq = str(int(df.head(10000).sort_values(by=['t'])['t'].diff(1).dt.seconds.value_counts().index[0] / 60))
            except:
                freq = int(15)

        # freq = int(freq.seconds / 60)
        return freq
    @staticmethod
    # 查找字段中属于时间字段的字段
    def get_time_find(df):
        df.dropna(inplace=True)
        tname = []
        for i in df.columns:
            try:
                pd.to_datetime(df[df[i]!=0][i])
                try:
                    df[i].astype(float)  # 过滤可以转为数值的数据
                except:
                    tname.append(i)
                    pass
            except:
                pass
        if len(tname) == 0:
            print("请定义正确的时间数据， 例如 2023年11月10日，2023-12-12 12:12:12")
            return None
        else:
            return tname[0]

    def get_name_tval(self,df, tname, valname):
        col = list(df.columns)
        t, val = tname, valname
        # 没有时间 》 进行判别 通过时间转换且去除数值数据
        if t is None:
            t = self.get_time_find(df)
            df['t'] = pd.to_datetime(df[t])
        else:
            df['t'] = pd.to_datetime(df[t])

        # 没有数值指定，如果只有两列数据，可以计算，否则无
        if val is None and len(col) == 2:
            val = list(set(col).difference([t]))[0]
        elif val is None and len(col)>2:
            print("需要指定要进行计算的数值列名称，否则无法继续计算")
        else:
            pass
        return t, val

    def get_name_tval_freq(self, df, tname, valname):
        t, val = self.get_name_tval(df, tname, valname)
        df = df.groupby(t).head(1)      # 根据时间进行去重
        df = df.reset_index(drop=True)

        freq = self.get_time_freq(df)  # 时间频率，一般是间隔15分钟，
        dayc = (60 / int(freq)) * 24
        df = df.reset_index(drop=True)
        try:
            df['t'] = df[t]
            df['pw'] = df[val]
        except:
            pass

        return df, t, val, freq, dayc



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


def df_reset(df):
    df.sort_values(by='t', inplace=True)
    df = df.reset_index(drop=True)
    return df


def deal_val_non_num(df, val):
    # """ 数据转为数值类型，但是可能存在异常数据，不可转换"""
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
    # """ 可能数据是累计值，即每个数据都比前一个数据大
    # 即有5天的数据，当天有90个点值都比前一个值大，则进行diff处理"""
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
        if tmp1 > int(daycount) * 0.92:
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
    if day_start is not None and day_end is not None:
        df_new = df[(df['day'] >= day_start) & (df['day'] <= day_end)]

    elif day_start is not None:
        df_new = df[df['day'] >= day_start]

    elif day_end is not None:
        df_new = df[df['day'] <= day_end]

    else:
        df_new = df.copy()

    df_new = df_reset(df_new)
    return df_new


def deal_val_select_week(df, weekin=None, weekout=None):
    if weekin is not None:
        df_new = df[df['dayofweek'].isin(weekin)]
    elif weekout is not None:
        df_new = df[~df['dayofweek'].isin(weekin)]
    df_new = df_reset(df_new)
    return df_new


def deal_val(df, val, dayc=None, delete=None, hour_start=None, hour_end=None, day_start=None, day_end=None):
    # """
    # :param df: 包含时间和功率数据
    # :param val: 功率字段值
    # :param dayc: 根据freq间隔时间,计算一天理论数据点个数
    # :param delete:删除当日数值个数占比小于90%的日数据
    # :param hour_start:筛选每天有效小时的起始值,如7点
    # :param hour_end:筛选每天有效小时的末端值,如7点
    # :param day_start:筛选开始时间
    # :param day_end:筛选结束时间
    # :return: 进行处理后的数据
    # """
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

def get_pv(df_ir, eff=1, scale=100, unit='kw'):
    # 统一单位为kw
    if unit in ['MW', 'mw', 'Mw', 'mW']:
        scale = scale * 1000

    elif unit in ["GW", "Gw", "gw", "gW"]:
        scale = scale * 1000 * 1000

    elif unit in ["W", "w"]:
        scale = scale / 1000

    df_ir['pv_full'] = (df_ir['ghi'] / df_ir['ghi'].max()) * scale
    df_ir['pv'] = df_ir['pv_full'] * eff

    return df_ir

def get_pv_eff(df, eff):
    df['pv'] = df['pv_full'] * eff
    return df

def deal_load_pv(df_load, df_ir, scale, eff, weeks=None,hour_min=0,hour_max=24,day_min=None, day_max=None):
    df_pv = get_pv(df_ir, eff=eff, scale=scale, unit='kw')  # 根据装机容量获取 光伏发电量
    df_load_pv = deal_load_pv_cost(df_load, df_pv)  # 拼接光伏和负荷
    df_load_pv_select = deal_load_pv_select(df_load_pv, weeks=weeks, hour_min=hour_min, hour_max=hour_max,
                                            day_min=day_min, day_max=day_max)  # 筛选负荷

    return df_load_pv_select

# 不同光伏装机容量下的消纳比例
def deal_load_pv_all(df_load, df_ir, eff, weeks=None,hour_min=0,hour_max=24,day_min=None, day_max=None):
    # """
    # :param df_load:负荷数据
    # :param df_ir: 辐照度数据
    # :param eff: 光伏发电效率
    # :param weeks: 约束周收据
    # :param hour_min: 约束小时开始时间
    # :param hour_max: 约束小时结束时间
    # :param day_min: 约束起始日
    # :param day_max: 约束结束日
    # :return:光伏装机容量和消纳比值（<=1)
    # """

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
    # """ df 是每天的数据 """
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

    # """ 输入每天各个分钟数据 》计算每个月的分钟均值 """
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



def first_input_param(col1, col2):
    timezones = ["Europe/Bucharest"]

    c1, c2, c3, c4 = st.columns(4)
    # with c1:
    #     st.session_state.param_t = st.sidebar.selectbox("时间字段名: time ", col1)
    # with c2:
    #     st.session_state.param_val_power = st.sidebar.selectbox("用电量字段：active energy(+)(kWh) ", col1)
    # with c3:
    #     st.session_state.param_val_load = st.sidebar.selectbox("负荷字段： Active power(+)(kWh)", col2)
    # with c4:
    #     st.session_state.param_timezone = st.sidebar.selectbox("时区:Europe/Bucharest", timezones)

    st.session_state.param_t = "Date"
    st.session_state.param_val_power = "active energy(+)(kWh)"
    st.session_state.param_val_load = "Active power(+)(kW)"
    st.session_state.param_timezone = "Europe/Bucharest"

    st.sidebar.write("时间字段：", st.session_state.param_t)
    st.sidebar.write("用电功率：", st.session_state.param_val_power)
    st.sidebar.write("负荷功率：", st.session_state.param_val_load)
    st.sidebar.write("TimeZone：", st.session_state.param_timezone)

    c5, c6, c7, c8 = st.columns(4)
    with c5:
        st.session_state.param_latitude = st.text_input("纬度： 1.2", 1)
    with c6:
        st.session_state.param_longitude = st.text_input("经度： 38", 39)
    with c7:
        st.session_state.param_pv_scale = st.text_input("装机容量： 1000/kWh", 1000)
    with c8:
        st.session_state.param_pv_eff = st.text_input("光伏效率： 0.9", 0.9)


def dashshow(param):
    st.session_state.param_latitude = float(st.session_state.param_latitude)
    st.session_state.param_longitude = float(st.session_state.param_longitude)
    st.session_state.param_pv_scale = float(st.session_state.param_pv_scale)
    st.session_state.param_pv_eff = float(st.session_state.param_pv_eff)

    # 1 处理负荷和用电量 > 获取时间字段，功率字段 ，时间间隔，每天数据个数
    dt = DealTime()
    df_power, param_t_power, param_val_power, param_freq, param_dayc = dt.get_name_tval_freq(st.session_state.df_power,
                                                                                             st.session_state.param_t,
                                                                                             st.session_state.param_val_power
                                                                                             )

    df_load, param_t_load, param_val_load, param_freq, param_dayc = dt.get_name_tval_freq(st.session_state.df_load,
                                                                                          st.session_state.param_t,
                                                                                          st.session_state.param_val_load)

    # 2 连续性计算 》 获取填充后的结果数据
    df_power, info_cont1_power, info_cont2_power = dt.judge_time_continuous(df_power,
                                                                            freqs=f'{param_freq}Min',
                                                                            lack=0.3)

    df_load, info_cont1_load, info_cont2_load = dt.judge_time_continuous(df_load,
                                                                         freqs=f'{param_freq}Min',
                                                                         lack=0.3)
    st.write("用电量数据" + info_cont1_power + ' ' + info_cont2_power)
    st.write("负荷数据" + info_cont1_load + ' ' + info_cont2_load)

    # 3 判断是否进减去上一位处理，df_power_lack：删除缺失较多的日，df_power_select_day、hour：筛选天和小时
    df_power, df_power_lack, df_power_select_day, df_power_select_hour = deal_val(df_power,
                                                                                  param_val_power,
                                                                                  dayc=param_dayc)
    df_load, df_load_lack, df_load_select_day, df_load_select_hour = deal_val(df_load,
                                                                              param_val_load,
                                                                              dayc=param_dayc)

    # 4 计算起始时间，结束时间，功率求和倍数
    param_freq_sum = 60 / int(param_freq)  # 值为4， 15分钟，则功率小时累计和之后除以4

    param_day_start = str(df_load['day'].min())[0:10]  # 最小日作为后续滑块的起始、结束值
    param_day_end = str(df_load['day'].max())[0:10]
    st.write("开始计算辐照度")
    df_ir = get_ir(latitude=st.session_state.param_latitude,
                   longitude=st.session_state.param_longitude,
                   freq=param_freq,
                   timestart=param_day_start,
                   timeend=param_day_end,
                   timezone=st.session_state.param_timezone)

    # 5 根据初始装机容量获取光伏数据
    # df_pv = get_pv( df_ir, eff = param_pv_eff, scale=param_pv_scale, unit=param_pv_unit)
    st.write("开始计算月度用电量")

    # 6 每个月用电量，暂时使用kw作为基础
    df_pw, df_pwms, fig = get_power(df_power, st.session_state.param_power_unit, param_freq_sum)

    st.pyplot(fig)

    # 1 处理负荷单位
    df_load = deal_load_unit(df_load, st.session_state.param_load_unit)

    st.write("开始计算参考的光伏装机容量")

    # 2 根据原始数据,计算所有的消纳比例
    param_pv_scale_max, param_pv_scale_mean, df_recoms = deal_load_pv_all(df_load,
                                                                          df_ir,
                                                                          st.session_state.param_pv_eff, weeks=None,
                                                                          hour_min=0, hour_max=24, day_min=None,
                                                                          day_max=None)
    # st.dataframe(df_recoms.T) #展示部分数据，不做任何改变下，数据的变化

    # 3 初始值光伏推荐值》计算消纳比 》后续需要再进行新的输入参数进行改进
    st.write("开始计算参考的光伏装机容量2")

    param_pv_scale_init = param_pv_scale_mean * 1.1
    df_load_pv = deal_load_pv(df_load, df_ir, param_pv_scale_init, st.session_state.param_pv_eff)

    # 4 画图需要的tit , 整体消纳均值
    param_tit, param_xn = deal_every_day(df_load_pv, param_pv_scale_init)

    df_month = deal_month_hour_mean(df_load_pv)

    fig_month = deal_month_hour_mean_show(df_month, param_tit)
    st.pyplot(fig_month)

    fig_year = deal_year_hour_mean_show(df_load_pv, param_xn)
    st.pyplot(fig_year)

    param['param_val_power'] = st.session_state.param_val_power
    param['param_val_load'] = st.session_state.param_val_load
    param['param_timezone'] = st.session_state.param_timezone
    param['param_latitude'] = st.session_state.param_latitude
    param['param_longitude'] = st.session_state.param_longitude
    param['param_pv_scale'] = st.session_state.param_pv_scale
    param['param_pv_eff'] = st.session_state.param_pv_eff
    param['param_t'] = param_t_power
    param['param_t_power'] = param_t_power  # power时间字段
    param['param_val_power'] = param_val_power  # power值字段
    param['param_t_load'] = param_t_load  # 负荷时间字段
    param['param_val_load'] = param_val_load
    param['param_freq'] = param_freq  # 间隔15分钟
    param['param_dayc'] = param_dayc  # 每天96个点
    param['param_freq_sum'] = param_freq_sum  # 用电量除以4
    param['param_day_start'] = param_day_start
    param['param_day_end'] = param_day_end
    param['param_pv_scale_max'] = param_pv_scale_max
    param['param_pv_scale_mean'] = param_pv_scale_mean
    param['param_pv_scale_init'] = param_pv_scale_init

    # st.session_state.df_load = df_load
    # st.session_state.df_power = df_power

    return df_load, df_power, df_ir, param


def page1():
    st.subheader('初始数据总览')

    # 默认功率单位为Kw
    param = {}
    st.session_state.param_pv_unit = 'kw'  # 光伏功率单位
    st.session_state.param_power_unit = 'kw'  # 用电功率单位
    st.session_state.param_load_unit = 'kw'  # 负荷功率单位
    param['param_pv_unit'] = 'kw'  # 光伏功率单位
    param['param_power_unit'] = 'kw'  # 用电功率单位
    param['param_load_unit'] = 'kw'  # 负荷功率单位

    df_power = st.session_state.df_power
    df_load = st.session_state.df_load

    col1 = list(df_power.columns)
    col2 = list(df_load.columns)

    first_input_param(col1, col2)
    df_load2, df_power2, df_ir2, param2 = dashshow(param)
    return df_load2, df_power2, df_ir2, param2
    # st.session_state.param = param2
    # st.session_state.df_load2 = df_load2
    # st.session_state.df_power2 = df_power2
    # st.session_state.df_ir = df_ir2

def showselect(param,df_power):
    param_t = param['param_t']
    param_val_power = param['param_val_power']
    param_val_load = param['param_val_load']
    param_latitude = param["param_latitude"]
    param_longitude = param["param_longitude"]
    param_timezone = param["param_timezone"]
    param_pv_eff = param["param_pv_eff"]

    param_pv_scale = param["param_pv_scale"]
    param_pv_scale_max = param['param_pv_scale_max']
    param_pv_scale_mean = param['param_pv_scale_mean']

    param_day_start = param['param_day_start']
    param_day_end = param['param_day_end']

    param_freq = param['param_freq'] # 间隔15分钟
    param_freq_sum = param['param_freq_sum'] # 每天96个点
    param_dayc = param['param_dayc'] # 用电量要除以的数，除 4 （= 60/15）

    param_pv_unit = param['param_pv_unit'] # 单位默认都是kw
    param_power_unit = param['param_power_unit']
    param_load_unit = param['param_load_unit']

    param_delete = 0
    param_hour_start = 0
    param_hour_end = 24

    # 1 处理负荷和用电量
    st.write("对用电量数据进行范围筛选 ")

    c1, c2 = st.columns(2)
    with c1:
        #1 缺失过多删除

        power_delete = st.slider('删除缺失值较多的日-数据占比低于40%', 1, 100, 40)
        power_delete = int(power_delete)
    with c2:
        #  HOUR 小时范围 选择

        power_hour_range = st.slider('小时范围(1-2表示1点到2点)', min_value=0, max_value=24, value=(0, 24))  # 初始为全天数据
        power_hour_start, power_hour_end = int(power_hour_range[0]), int(power_hour_range[1])


    # 2 DAY 范围 选择
    param_day_start = datetime.datetime.strptime(param_day_start, "%Y-%m-%d")
    param_day_end = datetime.datetime.strptime(param_day_end, "%Y-%m-%d")

    power_date_range = st.slider('日期范围', min_value=param_day_start, max_value=param_day_end,
                                 value=(param_day_start, param_day_end))
    power_day_start, power_day_end = power_date_range[0], power_date_range[1]


    # 4 week 周数据选择
    power_week = st.selectbox("选择周数据", ["工作日", "周末", "不筛选"], index=2)
    tmp = {"工作日": [1, 2, 3, 4, 5], "周末": [6, 7], "不筛选": [1, 2, 3, 5, 6, 7]}
    power_weekin = tmp[power_week]

    # 5 删除缺失占比超过设置阈值的日数据
    df_lack = deal_val_lack(df_power, param_dayc, power_delete) #

    # 6 选择指定的日期，工作日或周末，小时数据范围
    df_select_day = deal_val_select_day(df_lack, power_day_start, power_day_end)
    df_select_week = deal_val_select_week(df_select_day, power_weekin)
    df_select_hour = deal_val_select_hour(df_select_week, power_hour_start, power_hour_end)

    # 7 对数据进行空值填充
    df_select_hour = deal_val_fillna(df_select_hour)

    df_pw, df_pwms, fig = get_power(df_select_hour, param_power_unit, param_freq_sum)
    st.pyplot(fig)

def page2(param2,df_power2):
    # param = st.session_state.param
    # df_power2 = st.session_state.df_power2
    showselect(param2,df_power2)


def showselect2(param, df_load, df_ir):
    param_t = param['param_t']
    param_val_power = param['param_val_power']
    param_val_load = param['param_val_load']
    param_latitude = param["param_latitude"]
    param_longitude = param["param_longitude"]
    param_timezone = param["param_timezone"]
    param_pv_eff = param["param_pv_eff"]

    param_pv_scale = param["param_pv_scale"]
    param_pv_scale_max = param['param_pv_scale_max']
    param_pv_scale_mean = param['param_pv_scale_mean']

    param_day_start = param['param_day_start']
    param_day_end = param['param_day_end']

    param_freq = param['param_freq']  # 间隔15分钟
    param_freq_sum = param['param_freq_sum']  # 每天96个点
    param_dayc = param['param_dayc']  # 用电量要除以的数，除 4 （= 60/15）

    param_pv_unit = param['param_pv_unit']  # 单位默认都是kw
    param_power_unit = param['param_power_unit']
    param_load_unit = param['param_load_unit']

    param_delete = 0
    param_hour_start = 0
    param_hour_end = 24

    # 1 处理负荷和用电量
    st.write("对负荷数据进行范围筛选 ")

    c1, c2 = st.columns(2)
    with c1:
        # 1 缺失过多删除

        power_delete = st.slider('删除缺失值较多的日-数据占比低于40%', 1, 100, 40)
        power_delete = int(power_delete)
    with c2:
        #  HOUR 小时范围 选择

        power_hour_range = st.slider('小时范围(1-2表示1点到2点)', min_value=0, max_value=24, value=(0, 24))  # 初始为全天数据
        power_hour_start, power_hour_end = int(power_hour_range[0]), int(power_hour_range[1])

    # 2 DAY 范围 选择
    param_day_start = datetime.datetime.strptime(param_day_start, "%Y-%m-%d")
    param_day_end = datetime.datetime.strptime(param_day_end, "%Y-%m-%d")

    power_date_range = st.slider('日期范围', min_value=param_day_start, max_value=param_day_end,
                                 value=(param_day_start, param_day_end))
    power_day_start, power_day_end = power_date_range[0], power_date_range[1]

    # 4 week 周数据选择
    power_week = st.selectbox("选择周数据", ["工作日", "周末", "不筛选"], index=2)
    tmp = {"工作日": [1, 2, 3, 4, 5], "周末": [6, 7], "不筛选": [1, 2, 3, 5, 6, 7]}
    power_weekin = tmp[power_week]

    # 5 删除缺失占比超过设置阈值的日数据
    df_lack = deal_val_lack(df_load, param_dayc, power_delete)  #

    # 6 选择指定的日期，工作日或周末，小时数据范围
    df_select_day = deal_val_select_day(df_lack, power_day_start, power_day_end)
    df_select_week = deal_val_select_week(df_select_day, power_weekin)
    df_select_hour = deal_val_select_hour(df_select_week, power_hour_start, power_hour_end)

    # 7 对数据进行空值填充
    # df_select_hour = deal_val_fillna(df_select_hour)
    df_select_hour['pw'] = df_select_hour['pw'].fillna(df_select_hour.groupby('hourms')['pw'].transform('mean'))

    # st.write(df_select_hour.describe())

    # 3 初始值光伏推荐值》计算消纳比 》后续需要再进行新的输入参数进行改进
    param_pv_scale_best = param['param_pv_scale_init']
    param_pv_scale_init = st.slider('手动选择参考的光伏装机容量',
                                    int(param_pv_scale_mean * 0.2), int(param_pv_scale_max * 2),
                                    int(param_pv_scale_best))

    df_load_pv = deal_load_pv(df_select_hour, df_ir, param_pv_scale_init, 1,
                              weeks=power_weekin,
                              hour_min=power_hour_start,
                              hour_max=power_hour_end,
                              day_min=power_day_start,
                              day_max=power_day_end)

    # 4 画图需要的tit , 整体消纳均值
    param_tit, param_xn = deal_every_day(df_load_pv, param_pv_scale_init)

    df_month = deal_month_hour_mean(df_load_pv)

    fig_month = deal_month_hour_mean_show(df_month, param_tit)
    st.pyplot(fig_month)

    fig_year = deal_year_hour_mean_show(df_load_pv, param_xn)
    st.pyplot(fig_year)


def page3():
    param = st.session_state.param
    df_load2 = st.session_state.df_load2
    df_ir2 = st.session_state.df_ir
    showselect2(param, df_load2, df_ir2)


def read_files(files):
    df = pd.DataFrame()
    for file in files:
        tmp = read_file(file.name)
        try:
            df = df.append(tmp, ignore_index=True)
        except:
            df = pd.concat([df,tmp], ignore_index=True)
    return df

def read_file2(file):
    df = read_file(file)
    return df


param_file_power = st.text_input("上传-用电量文件/完整路径")
param_file_load = st.text_input("上传-用负荷文件/完整路径" )

if param_file_power:
    df_power = read_file2(param_file_power)
    if param_file_load:
        df_load = read_file2(param_file_load)
        st.session_state.df_power = df_power
        st.session_state.df_load = df_load
        df_load2, df_power2, df_ir2, param2 = page1()
        # page2()
        # time.sleep(0.2)
        # page3()

# front = st.Page("src/page1_overview.py", title="OverView",  icon=":material/dashboard:", default=True) # 首页
# page2 = st.Page("src/page2_power.py", title="PowerShow",  icon=":material/settings:",)
# page3 = st.Page("src/page3_load.py", title="LoadShow",  icon=":material/settings:",)
# # page4 = st.Page("src/page4_pv.py", title="PvShow",  icon=":material/settings:",)


