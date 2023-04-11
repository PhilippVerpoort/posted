import pathlib

import pandas as pd
import yaml

from src.path import pathOfDataFile


# read BAT CSV input file
def readTEDFile(path: pathlib.Path, mapColnamesDtypes: dict):
    return pd.read_csv(path, names=list(mapColnamesDtypes.keys()), dtype=mapColnamesDtypes, encoding='utf-8')


# read CSV data file
def readCSVDataFile(fname: str):
    path = pathOfDataFile(fname)
    return pd.read_csv(path)


# read YAML config file
def readYAMLDataFile(fname: str):
    path = pathOfDataFile(f"{fname}.yml")
    return yaml.load(open(path, 'r', encoding='utf-8').read(), Loader=yaml.FullLoader)
