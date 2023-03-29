import pandas as pd
import yaml

from src.path import pathOfDataFile, pathOfBATFile


def readBATFile(t: str, cols: list):
    path = pathOfBATFile(t)
    return pd.read_csv(path, names=cols, encoding='utf-8')


def readYAMLDataFile(fname: str):
    path = pathOfDataFile(f"{fname}.yml")
    return yaml.load(open(path, 'r', encoding='utf-8').read(), Loader=yaml.FullLoader)
