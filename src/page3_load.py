# -*-coding:utf-8 -*-
import pandas as pd
import datetime
import warnings

warnings.filterwarnings('ignore')
import numpy as np
import streamlit as st
# st.write('待优化')

# -*-coding:utf-8 -*-
import pandas as pd
import datetime
import warnings

warnings.filterwarnings('ignore')
import numpy as np
import streamlit as st
st.subheader('负荷')
try:
    from ..deal_input.deal_data import *
    from ..cons_deal.deal_ir import  *
    from ..cons_deal.deal_load import *
    # from ..plot_show.plotPv import *
except:
    from deal_input.deal_data import *
    from cons_deal.deal_ir import  *
    from cons_deal.deal_load import *
    # from plot_show.plotPower import *
# """
# 用电量分析
# 1） 根据不同的阈值展现不同的结果
# 2） 每周的均值展示
# 2） 工作日vs非工作日展示
# 3） 每个季度的均值展示
# # """
# param = st.session_state.param
# df_load = st.session_state.df_load
def showselect2(param,df_load,df_ir):
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
    st.write("对负荷数据进行范围筛选 ")

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
    df_lack = deal_val_lack(df_load, param_dayc, power_delete) #

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
                                    int(param_pv_scale_mean*0.2), int(param_pv_scale_max*2),
                                    int(param_pv_scale_best))

    df_load_pv = deal_load_pv(df_select_hour, df_ir, param_pv_scale_init, 1,
                              weeks = power_weekin,
                              hour_min = power_hour_start,
                              hour_max = power_hour_end,
                              day_min = power_day_start,
                              day_max = power_day_end)

    # 4 画图需要的tit , 整体消纳均值
    param_tit, param_xn = deal_every_day(df_load_pv, param_pv_scale_init)

    df_month = deal_month_hour_mean(df_load_pv)

    fig_month = deal_month_hour_mean_show(df_month, param_tit)
    st.pyplot(fig_month)

    fig_year = deal_year_hour_mean_show(df_load_pv, param_xn)
    st.pyplot(fig_year)



param = st.session_state.param
df_load2 = st.session_state.df_load2
df_ir2 = st.session_state.df_ir
showselect2(param,df_load2,df_ir2)








