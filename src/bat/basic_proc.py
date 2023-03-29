from src.read.read_bat import read_bat
from src.read.read_config import techs


# basic processing of BAT data
def basic_proc_batdata(only_techs: list = None, default_units: dict = None):
    if only_techs:
        tech_list = only_techs
    else:
        tech_list = list(techs.keys())

    r = {}
    for t in tech_list:
        bat_df = read_bat(t)
        r[t] = bat_df

    return r
