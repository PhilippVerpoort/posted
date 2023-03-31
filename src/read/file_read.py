import pandas as pd
import yaml

from src.path import pathOfDataFile, pathOfBATFile


# read BAT CSV input file
def readBATFile(t: str, mapColnamesDtypes: dict):
    path = pathOfBATFile(t)
    return pd.read_csv(path, names=list(mapColnamesDtypes.keys()), dtype=mapColnamesDtypes, encoding='utf-8')


# read YAML config file
def readYAMLDataFile(fname: str):
    path = pathOfDataFile(f"{fname}.yml")
    return yaml.load(open(path, 'r', encoding='utf-8').read(), Loader=yaml.FullLoader)
