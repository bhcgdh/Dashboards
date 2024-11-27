import photovoltaic as pv
from pvlib.location import Location
from pytz import timezone
import requests
import pandas as pd
import datetime
import warnings

warnings.filterwarnings('ignore')


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

