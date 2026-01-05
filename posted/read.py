from pathlib import Path

import pandas as pd
import yaml


def read_tedf_from_csv(fpath: str):
    """
    Read CSV data file

    Parameters
    ----------
    fpath: str
        Path of the file to read
    Returns
    -------
        pd.DataFrame
            DataFrame containing the data of the CSV
    """
    df = pd.read_csv(
        fpath,
        sep=",",
        quotechar='"',
        encoding="utf-8",
        dtype=str,
    ).fillna("")
    df.index = df.index + 2
    return df


def read_yaml(fpath: Path):
    """
    Read YAML config file

    Parameters
    ----------
    fpath: str
        Path of the file to read
    Returns
    -------
        dict
            Dictionary containing config
    """
    with open(fpath, mode="r", encoding="utf-8") as file_handle:
        return yaml.load(
            stream=file_handle,
            Loader=yaml.FullLoader,
        )
