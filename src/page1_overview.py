# -*-coding:utf-8 -*-
import pandas as pd
import datetime
import warnings

warnings.filterwarnings('ignore')
import numpy as np

from deal_input.deal_time import DealTime as DT
from deal_input.deal_data import *
from cons_deal.deal_ir import *
from cons_deal.deal_load import *
from cons_deal.deal_power import *
import streamlit as st
st.subheader('初始数据总览')

# 默认功率单位为Kw
param = {}
st.session_state.param_pv_unit = 'kw'  # 光伏功率单位
st.session_state.param_power_unit = 'kw'  # 用电功率单位
st.session_state.param_load_unit = 'kw'  # 负荷功率单位

param = {}
param["param_pv_unit"] = 'kw'  # 光伏功率单位
param["param_power_unit"] = 'kw'  # 用电功率单位
param["param_load_unit"] = 'kw'  # 负荷功率单位


df_power = st.session_state.df_power
df_load = st.session_state.df_load

col1 = list(df_power.columns)
col2 = list(df_load.columns)

def first_input_param(col1, col2):
    timezones = ["Africa/Abidjan","Africa/Accra","Africa/Addis_Ababa","Africa/Algiers","Africa/Asmara","Africa/Asmera","Africa/Bamako","Africa/Bangui","Africa/Banjul","Africa/Bissau","Africa/Blantyre","Africa/Brazzaville","Africa/Bujumbura","Africa/Cairo","Africa/Casablanca","Africa/Ceuta","Africa/Conakry","Africa/Dakar","Africa/Dar_es_Salaam","Africa/Djibouti","Africa/Douala","Africa/El_Aaiun","Africa/Freetown","Africa/Gaborone","Africa/Harare","Africa/Johannesburg","Africa/Juba","Africa/Kampala","Africa/Khartoum","Africa/Kigali","Africa/Kinshasa","Africa/Lagos","Africa/Libreville","Africa/Lome","Africa/Luanda","Africa/Lubumbashi","Africa/Lusaka","Africa/Malabo","Africa/Maputo","Africa/Maseru","Africa/Mbabane","Africa/Mogadishu","Africa/Monrovia","Africa/Nairobi","Africa/Ndjamena","Africa/Niamey","Africa/Nouakchott","Africa/Ouagadougou","Africa/Porto-Novo","Africa/Sao_Tome","Africa/Timbuktu","Africa/Tripoli","Africa/Tunis","Africa/Windhoek","America/Adak","America/Anchorage","America/Anguilla","America/Antigua","America/Araguaina","America/Argentina/Buenos_Aires","America/Argentina/Catamarca","America/Argentina/ComodRivadavia","America/Argentina/Cordoba","America/Argentina/Jujuy","America/Argentina/La_Rioja","America/Argentina/Mendoza","America/Argentina/Rio_Gallegos","America/Argentina/Salta","America/Argentina/San_Juan","America/Argentina/San_Luis","America/Argentina/Tucuman","America/Argentina/Ushuaia","America/Aruba","America/Asuncion","America/Atikokan","America/Atka","America/Bahia","America/Bahia_Banderas","America/Barbados","America/Belem","America/Belize","America/Blanc-Sablon","America/Boa_Vista","America/Bogota","America/Boise","America/Buenos_Aires","America/Cambridge_Bay","America/Campo_Grande","America/Cancun","America/Caracas","America/Catamarca","America/Cayenne","America/Cayman","America/Chicago","America/Chihuahua","America/Ciudad_Juarez","America/Coral_Harbour","America/Cordoba","America/Costa_Rica","America/Creston","America/Cuiaba","America/Curacao","America/Danmarkshavn","America/Dawson","America/Dawson_Creek","America/Denver","America/Detroit","America/Dominica","America/Edmonton","America/Eirunepe","America/El_Salvador","America/Ensenada","America/Fort_Nelson","America/Fort_Wayne","America/Fortaleza","America/Glace_Bay","America/Godthab","America/Goose_Bay","America/Grand_Turk","America/Grenada","America/Guadeloupe","America/Guatemala","America/Guayaquil","America/Guyana","America/Halifax","America/Havana","America/Hermosillo","America/Indiana/Indianapolis","America/Indiana/Knox","America/Indiana/Marengo","America/Indiana/Petersburg","America/Indiana/Tell_City","America/Indiana/Vevay","America/Indiana/Vincennes","America/Indiana/Winamac","America/Indianapolis","America/Inuvik","America/Iqaluit","America/Jamaica","America/Jujuy","America/Juneau","America/Kentucky/Louisville","America/Kentucky/Monticello","America/Knox_IN","America/Kralendijk","America/La_Paz","America/Lima","America/Los_Angeles","America/Louisville","America/Lower_Princes","America/Maceio","America/Managua","America/Manaus","America/Marigot","America/Martinique","America/Matamoros","America/Mazatlan","America/Mendoza","America/Menominee","America/Merida","America/Metlakatla","America/Mexico_City","America/Miquelon","America/Moncton","America/Monterrey","America/Montevideo","America/Montreal","America/Montserrat","America/Nassau","America/New_York","America/Nipigon","America/Nome","America/Noronha","America/North_Dakota/Beulah","America/North_Dakota/Center","America/North_Dakota/New_Salem","America/Nuuk","America/Ojinaga","America/Panama","America/Pangnirtung","America/Paramaribo","America/Phoenix","America/Port-au-Prince","America/Port_of_Spain","America/Porto_Acre","America/Porto_Velho","America/Puerto_Rico","America/Punta_Arenas","America/Rainy_River","America/Rankin_Inlet","America/Recife","America/Regina","America/Resolute","America/Rio_Branco","America/Rosario","America/Santa_Isabel","America/Santarem","America/Santiago","America/Santo_Domingo","America/Sao_Paulo","America/Scoresbysund","America/Shiprock","America/Sitka","America/St_Barthelemy","America/St_Johns","America/St_Kitts","America/St_Lucia","America/St_Thomas","America/St_Vincent","America/Swift_Current","America/Tegucigalpa","America/Thule","America/Thunder_Bay","America/Tijuana","America/Toronto","America/Tortola","America/Vancouver","America/Virgin","America/Whitehorse","America/Winnipeg","America/Yakutat","America/Yellowknife","Antarctica/Casey","Antarctica/Davis","Antarctica/DumontDUrville","Antarctica/Macquarie","Antarctica/Mawson","Antarctica/McMurdo","Antarctica/Palmer","Antarctica/Rothera","Antarctica/South_Pole","Antarctica/Syowa","Antarctica/Troll","Antarctica/Vostok","Arctic/Longyearbyen","Asia/Aden","Asia/Almaty","Asia/Amman","Asia/Anadyr","Asia/Aqtau","Asia/Aqtobe","Asia/Ashgabat","Asia/Ashkhabad","Asia/Atyrau","Asia/Baghdad","Asia/Bahrain","Asia/Baku","Asia/Bangkok","Asia/Barnaul","Asia/Beirut","Asia/Bishkek","Asia/Brunei","Asia/Calcutta","Asia/Chita","Asia/Choibalsan","Asia/Chongqing","Asia/Chungking","Asia/Colombo","Asia/Dacca","Asia/Damascus","Asia/Dhaka","Asia/Dili","Asia/Dubai","Asia/Dushanbe","Asia/Famagusta","Asia/Gaza","Asia/Harbin","Asia/Hebron","Asia/Ho_Chi_Minh","Asia/Hong_Kong","Asia/Hovd","Asia/Irkutsk","Asia/Istanbul","Asia/Jakarta","Asia/Jayapura","Asia/Jerusalem","Asia/Kabul","Asia/Kamchatka","Asia/Karachi","Asia/Kashgar","Asia/Kathmandu","Asia/Katmandu","Asia/Khandyga","Asia/Kolkata","Asia/Krasnoyarsk","Asia/Kuala_Lumpur","Asia/Kuching","Asia/Kuwait","Asia/Macao","Asia/Macau","Asia/Magadan","Asia/Makassar","Asia/Manila","Asia/Muscat","Asia/Nicosia","Asia/Novokuznetsk","Asia/Novosibirsk","Asia/Omsk","Asia/Oral","Asia/Phnom_Penh","Asia/Pontianak","Asia/Pyongyang","Asia/Qatar","Asia/Qostanay","Asia/Qyzylorda","Asia/Rangoon","Asia/Riyadh","Asia/Saigon","Asia/Sakhalin","Asia/Samarkand","Asia/Seoul","Asia/Shanghai","Asia/Singapore","Asia/Srednekolymsk","Asia/Taipei","Asia/Tashkent","Asia/Tbilisi","Asia/Tehran","Asia/Tel_Aviv","Asia/Thimbu","Asia/Thimphu","Asia/Tokyo","Asia/Tomsk","Asia/Ujung_Pandang","Asia/Ulaanbaatar","Asia/Ulan_Bator","Asia/Urumqi","Asia/Ust-Nera","Asia/Vientiane","Asia/Vladivostok","Asia/Yakutsk","Asia/Yangon","Asia/Yekaterinburg","Asia/Yerevan","Atlantic/Azores","Atlantic/Bermuda","Atlantic/Canary","Atlantic/Cape_Verde","Atlantic/Faeroe","Atlantic/Faroe","Atlantic/Jan_Mayen","Atlantic/Madeira","Atlantic/Reykjavik","Atlantic/South_Georgia","Atlantic/St_Helena","Atlantic/Stanley","Australia/ACT","Australia/Adelaide","Australia/Brisbane","Australia/Broken_Hill","Australia/Canberra","Australia/Currie","Australia/Darwin","Australia/Eucla","Australia/Hobart","Australia/LHI","Australia/Lindeman","Australia/Lord_Howe","Australia/Melbourne","Australia/NSW","Australia/North","Australia/Perth","Australia/Queensland","Australia/South","Australia/Sydney","Australia/Tasmania","Australia/Victoria","Australia/West","Australia/Yancowinna","Brazil/Acre","Brazil/DeNoronha","Brazil/East","Brazil/West","CET","CST6CDT","Canada/Atlantic","Canada/Central","Canada/Eastern","Canada/Mountain","Canada/Newfoundland","Canada/Pacific","Canada/Saskatchewan","Canada/Yukon","Chile/Continental","Chile/EasterIsland","Cuba","EET","EST","EST5EDT","Egypt","Eire","Etc/GMT","Etc/GMT+0","Etc/GMT+1","Etc/GMT+10","Etc/GMT+11","Etc/GMT+12","Etc/GMT+2","Etc/GMT+3","Etc/GMT+4","Etc/GMT+5","Etc/GMT+6","Etc/GMT+7","Etc/GMT+8","Etc/GMT+9","Etc/GMT-0","Etc/GMT-1","Etc/GMT-10","Etc/GMT-11","Etc/GMT-12","Etc/GMT-13","Etc/GMT-14","Etc/GMT-2","Etc/GMT-3","Etc/GMT-4","Etc/GMT-5","Etc/GMT-6","Etc/GMT-7","Etc/GMT-8","Etc/GMT-9","Etc/GMT0","Etc/Greenwich","Etc/UCT","Etc/UTC","Etc/Universal","Etc/Zulu","Europe/Amsterdam","Europe/Andorra","Europe/Astrakhan","Europe/Athens","Europe/Belfast","Europe/Belgrade","Europe/Berlin","Europe/Bratislava","Europe/Brussels","Europe/Bucharest","Europe/Budapest","Europe/Busingen","Europe/Chisinau","Europe/Copenhagen","Europe/Dublin","Europe/Gibraltar","Europe/Guernsey","Europe/Helsinki","Europe/Isle_of_Man","Europe/Istanbul","Europe/Jersey","Europe/Kaliningrad","Europe/Kiev","Europe/Kirov","Europe/Kyiv","Europe/Lisbon","Europe/Ljubljana","Europe/London","Europe/Luxembourg","Europe/Madrid","Europe/Malta","Europe/Mariehamn","Europe/Minsk","Europe/Monaco","Europe/Moscow","Europe/Nicosia","Europe/Oslo","Europe/Paris","Europe/Podgorica","Europe/Prague","Europe/Riga","Europe/Rome","Europe/Samara","Europe/San_Marino","Europe/Sarajevo","Europe/Saratov","Europe/Simferopol","Europe/Skopje","Europe/Sofia","Europe/Stockholm","Europe/Tallinn","Europe/Tirane","Europe/Tiraspol","Europe/Ulyanovsk","Europe/Uzhgorod","Europe/Vaduz","Europe/Vatican","Europe/Vienna","Europe/Vilnius","Europe/Volgograd","Europe/Warsaw","Europe/Zagreb","Europe/Zaporozhye","Europe/Zurich","GB","GB-Eire","GMT","GMT+0","GMT-0","GMT0","Greenwich","HST","Hongkong","Iceland","Indian/Antananarivo","Indian/Chagos","Indian/Christmas","Indian/Cocos","Indian/Comoro","Indian/Kerguelen","Indian/Mahe","Indian/Maldives","Indian/Mauritius","Indian/Mayotte","Indian/Reunion","Iran","Israel","Jamaica","Japan","Kwajalein","Libya","MET","MST","MST7MDT","Mexico/BajaNorte","Mexico/BajaSur","Mexico/General","NZ","NZ-CHAT","Navajo","PRC","PST8PDT","Pacific/Apia","Pacific/Auckland","Pacific/Bougainville","Pacific/Chatham","Pacific/Chuuk","Pacific/Easter","Pacific/Efate","Pacific/Enderbury","Pacific/Fakaofo","Pacific/Fiji","Pacific/Funafuti","Pacific/Galapagos","Pacific/Gambier","Pacific/Guadalcanal","Pacific/Guam","Pacific/Honolulu","Pacific/Johnston","Pacific/Kanton","Pacific/Kiritimati","Pacific/Kosrae","Pacific/Kwajalein","Pacific/Majuro","Pacific/Marquesas","Pacific/Midway","Pacific/Nauru","Pacific/Niue","Pacific/Norfolk","Pacific/Noumea","Pacific/Pago_Pago","Pacific/Palau","Pacific/Pitcairn","Pacific/Pohnpei","Pacific/Ponape","Pacific/Port_Moresby","Pacific/Rarotonga","Pacific/Saipan","Pacific/Samoa","Pacific/Tahiti","Pacific/Tarawa","Pacific/Tongatapu","Pacific/Truk","Pacific/Wake","Pacific/Wallis","Pacific/Yap","Poland","Portugal","ROC","ROK","Singapore","Turkey","UCT","US/Alaska","US/Aleutian","US/Arizona","US/Central","US/East-Indiana","US/Eastern","US/Hawaii","US/Indiana-Starke","US/Michigan","US/Mountain","US/Pacific","US/Samoa","UTC","Universal","W-SU","WET","Zulu"]
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
        st.session_state.param_latitude = st.text_input("纬度： 1.2",1)
    with c6:
        st.session_state.param_longitude = st.text_input("经度： 38",39)
    with c7:
        st.session_state.param_pv_scale = st.text_input("装机容量： 1000/kWh",1000)
    with c8:
        st.session_state.param_pv_eff = st.text_input("光伏效率： 0.9",0.9)


def dashshow(param):
    st.session_state.param_latitude = float(st.session_state.param_latitude)
    st.session_state.param_longitude = float(st.session_state.param_longitude)
    st.session_state.param_pv_scale = float(st.session_state.param_pv_scale)
    st.session_state.param_pv_eff = float(st.session_state.param_pv_eff)



    # 1 处理负荷和用电量 > 获取时间字段，功率字段 ，时间间隔，每天数据个数
    dt = DT()
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

    param_day_start = str(df_load['day'].min())[0:10] # 最小日作为后续滑块的起始、结束值
    param_day_end = str(df_load['day'].max())[0:10]

    df_ir = get_ir(latitude=st.session_state.param_latitude,
                   longitude=st.session_state.param_longitude,
                   freq=param_freq,
                   timestart=param_day_start,
                   timeend=param_day_end,
                   timezone=st.session_state.param_timezone)

    # 5 根据初始装机容量获取光伏数据
    # df_pv = get_pv( df_ir, eff = param_pv_eff, scale=param_pv_scale, unit=param_pv_unit)

    # 6 每个月用电量，暂时使用kw作为基础
    df_pw, df_pwms, fig = get_power(df_power, st.session_state.param_power_unit, param_freq_sum)

    st.pyplot(fig)

    # 1 处理负荷单位
    df_load = deal_load_unit(df_load, st.session_state.param_load_unit)

    # 2 根据原始数据,计算所有的消纳比例
    param_pv_scale_max, param_pv_scale_mean, df_recoms = deal_load_pv_all(df_load, df_ir,
                                                                          st.session_state.param_pv_eff, weeks=None,
                                                                          hour_min=0, hour_max=24, day_min=None,
                                                                          day_max=None)
    # st.dataframe(df_recoms.T) #展示部分数据，不做任何改变下，数据的变化

    # 3 初始值光伏推荐值》计算消纳比 》后续需要再进行新的输入参数进行改进
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

    #
    # st.session_state.param_t_power = param_t_power  # power时间字段
    # st.session_state.param_t_load = param_t_load  # load时间字段
    # st.session_state.param_val_power = param_val_power  # power值字段
    # st.session_state.param_val_load = param_val_load  # load值字段
    #
    # st.session_state.param_freq = param_freq  # 间隔15分钟
    # st.session_state.param_dayc = param_dayc  # 每天96个点
    # st.session_state.param_freq_sum = param_freq_sum  # 用电量除以4
    # st.session_state.param_day_start = param_day_start
    # st.session_state.param_day_end = param_day_end
    # st.session_state.param_pv_scale_max = param_pv_scale_max
    # st.session_state.param_pv_scale_mean = param_pv_scale_mean
    #
    # st.session_state.df_power = df_power
    # st.session_state.df_load = df_load
    #
    # st.session_state.param_t_power = param_t_power
    # st.session_state.param_val_power = param_val_power
    # st.session_state.param_freq = param_freq
    # st.session_state.param_dayc = param_dayc
    # st.session_state.param_t_load = param_t_load
    # st.session_state.param_val_load = param_val_load
    # st.session_state.param_freq = param_freq
    # st.session_state.param_dayc = param_dayc

first_input_param(col1, col2)
df_load2, df_power2, df_ir2, param2= dashshow(param)

st.session_state.param = param2
st.session_state.df_load2 = df_load2
st.session_state.df_power2 = df_power2
st.session_state.df_ir = df_ir2