# 1 时间转为时间戳，秒级, 这里没有时区的要求
import time
import datetime
import pandas as pd
import streamlit
from dateutil.relativedelta import relativedelta
import numpy as np

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
        """
        :param data: 时间相关数据, 支持多种格式数据抓换
        :return: 将不同格式的数据转为标准的时间格式
        """
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
        """
        :param datas: 时间相关列表
        :param timezone: 当前时区，默认空
        :return: 时间列别
        """
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
        """
        :param t: 字符格式，如果是
        :return: 所有时间特征，
        """
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
        """
        types: 返回时间的类型，
           - s: 两个时间相差的总秒数
           - m: 两个时间相差的总分钟，默认该值
           - d: 两个时间相差的日数据,不足一天为0
        """
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
        """
        时间完整性判断，根据输入的dataframe数据，指定时间列名称
        :param df: 要进行判断的dataframe
        :param tn: 时间列名称
        :param freqs:时间间隔
        :param lack:缺失率，超过这个值，不建议继续进行计算
        :return: 是否
        """
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



