# -*-coding:utf-8 -*-
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

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

