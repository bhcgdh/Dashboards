# -*-coding:utf-8 -*-
import pandas as pd
import datetime
import warnings

warnings.filterwarnings('ignore')
import numpy as np

colors = [(0.424, 0.455, 0.686), (0.596, 0.812, 0.945), (0.984, 0.694, 0.851), (0.482, 0.525, 0.741),
          (0.631, 0.831, 0.671), (0.596, 0.384, 0.478), (0.918, 0.824, 0.808), (0.976, 0.706, 0.455)]
data_season = {1: '一', 2: '二', 3: '三', 4: '四'}
