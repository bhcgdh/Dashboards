# -*-coding:utf-8 -*-
import warnings
warnings.filterwarnings('ignore')
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



