from pathlib import Path

import pandas as pd
import yaml


def read_csv_file(fpath: str):
    """
    Read CSV data file

    Parameters
    ----------
    fpath: str
        Path of the file to read
    Returns
    -------
        pd.DataFrame
            DataFrame containg the data of the CSV
    """
    return pd.read_csv(fpath)


def read_yml_file(fpath: Path):
    """
    Read YAML config file

    Parameters
    ----------
    fpath: str
        Path of the file to read
    Returns
    -------
        dict
            Dictionary containing config info
    """
    fhandle = open(fpath, 'r', encoding='utf-8')
    ret = yaml.load(stream=fhandle, Loader=yaml.FullLoader)
    fhandle.close()
    return ret
