import pandas as pd
import yaml

from posted.path import pathOfDataFile

def readCSVDataFile(fname: str):
    """ Read a CSV data file.

    This function reads in a csv file specified by the relative file path.

    Parameters
    ----------
    fname : str
        The relative file path.

    Returns
    -------
    pd.DataFrame
        The data frame read from the csv file.
    """
    # read CSV data file
    fpath = pathOfDataFile(fname)
    return pd.read_csv(fpath)

def readYAMLDataFile(fname: str):
    # add exptext docu
    """ Read a YAML data file.

    This function reads in a yaml file specified by the relative file path (without the file extension).

    Parameters
    ----------
    fname : str
        The relative file path (without the file extension).

    Returns
    -------
    dict
        The dictionary read from the yaml file.
    """
    # read YAML data file
    fpath = pathOfDataFile(f"{fname}.yml")
    fhandle = open(fpath, 'r', encoding='utf-8')
    ret = yaml.load(stream=fhandle, Loader=yaml.FullLoader)
    fhandle.close()
    return ret
