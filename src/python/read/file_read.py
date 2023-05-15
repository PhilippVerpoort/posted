from pathlib import Path

import pandas as pd
import yaml

from src.python.path import pathOfDataFile


# read TED CSV input file
def readTEDFile(path: Path, mapColnamesDtypes: dict):
    return pd.read_csv(
        path,
        names=list(mapColnamesDtypes.keys()),
        dtype=mapColnamesDtypes,
        sep=',',
        quotechar='"',
        encoding='utf-8',
    )


# save TED CSV file
def saveTEDFile(path: Path, df: pd.DataFrame):
    df.to_csv(
        path,
        header=False,
        index=False,
        sep=',',
        quotechar='"',
        encoding='utf-8',
        na_rep='',
    )


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
