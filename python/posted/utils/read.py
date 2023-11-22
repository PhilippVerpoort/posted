from pathlib import Path

import pandas as pd
import yaml


# read CSV data file
def read_csv_file(fpath: str):
    return pd.read_csv(fpath)


# read YAML config file
def read_yml_file(fpath: Path):
    fhandle = open(fpath, 'r', encoding='utf-8')
    ret = yaml.load(stream=fhandle, Loader=yaml.FullLoader)
    fhandle.close()
    return ret
