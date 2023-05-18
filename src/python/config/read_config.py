import pandas as pd
import yaml

from src.python.path import pathOfDataFile


# read CSV data file
def readCSVDataFile(fname: str):
    fpath = pathOfDataFile(fname)
    return pd.read_csv(fpath)


# read YAML config file
def readYAMLDataFile(fname: str):
    fpath = pathOfDataFile(f"{fname}.yml")
    fhandle = open(fpath, 'r', encoding='utf-8')
    ret = yaml.load(stream=fhandle, Loader=yaml.FullLoader)
    fhandle.close()
    return ret
