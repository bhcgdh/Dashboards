import pandas as pd
import datetime
import warnings
warnings.filterwarnings('ignore')
import numpy as np
import streamlit as st
param_file_power = st.text_input("上传-用电量文件/完整路径")
try:
    from .deal_input.deal_files import read_file
except:
    from deal_input.deal_files import read_file

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

def read_files(files):
    df = pd.DataFrame()
    for file in files:
        st.write(file.name)
        tmp = read_file(file.name)
        try:
            df = df.append(tmp, ignore_index=True)
        except:
            df = pd.concat([df,tmp], ignore_index=True)
    return df

def read_file2(file):
    st.write(file)
    df = read_file(file)
    return df


def update_files():
    if st.button("上传数据"):
        st.session_state.logged_in = False
        st.rerun()

def input_files():
    param_file_power = st.text_input("上传-用电量文件/完整路径",)
    param_file_load = st.text_input("上传-用负荷文件/完整路径" )

    # param_file_power = st.file_uploader("上传-用电量文件/kwh", accept_multiple_files=True )
    # param_file_load = st.file_uploader("上传-用负荷文件/kwh", accept_multiple_files=True )

    if st.button("完成上传"):

        if param_file_power and param_file_load:
            df_power = read_file2(param_file_power)
            df_load = read_file2(param_file_load)
            # df_power = read_files(param_file_power)
            # df_load = read_files(param_file_load)

            st.session_state.df_power = df_power
            st.session_state.df_load = df_load

            st.session_state.logged_in = True

        elif param_file_load:
            df_load = read_files(param_file_load)
            st.session_state.df_load = df_load
            st.session_state.logged_in = True

        else:
            df_power = read_files(param_file_power)
            st.session_state.df_power = df_power
            st.session_state.logged_in = True

    st.rerun()


login_page = st.Page(input_files,  title="Input Files")     #, icon=":material/login:") # 输入数据
logout_page = st.Page(update_files, title="Update Files")    # icon=":material/logout:") # 更新数据

# 分页,每页展示对应的功率结果值
front = st.Page("src/page1_overview.py", title="OverView",  icon=":material/dashboard:", default=True) # 首页
page2 = st.Page("src/page2_power.py", title="PowerShow",  icon=":material/settings:",)
page3 = st.Page("src/page3_load.py", title="LoadShow",  icon=":material/settings:",)
page4 = st.Page("src/page4_pv.py", title="PvShow",  icon=":material/settings:",)


if st.session_state.logged_in:

    pg = st.navigation(
        {
            "Data": [logout_page],
            "Reports": [front,page2,page3,page4],  # 数据整体展示， 基本充放电要求下个数推荐，
            # "Tools": [search, history], #
        }
    )
else:

    pg = st.navigation([login_page])

pg.run()

