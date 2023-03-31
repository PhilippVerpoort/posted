import numpy as np
import pandas as pd

from src.read.file_read import readBATFile
from src.read.read_config import techs, dataformats


# basic processing of BAT data
def basic_proc_batdata(only_techs: list = None, units: dict = None):
    if only_techs:
        tech_list = only_techs
    else:
        tech_list = list(techs.keys())

    r = {}
    for techid in tech_list:
        mapColsDtypes = {
            colname: dataformats['bat'][colname]['dtype']
            for colname in dataformats['bat']
        }
        bat = readBATFile(techid, mapColsDtypes)

        __checkConsistency(techid, bat)

        bat = __insertDefaults(techid, bat)

        r[techid] = bat



    return r


# check bat dataframe is consistent
def __checkConsistency(techid: str, df: pd.DataFrame):
    # TODO: check reported units match dataformats['bat']

    # TODO: check reference units match techs[techid]

    pass


# insert defaults for reference value and unit
def __insertDefaults(techid: str, df: pd.DataFrame):
    # reference value
    df['reference_value'].fillna(1.0, inplace=True)

    # reference unit
    default_ref_units = [
        {'type': 'capex', 'reference_unit_def': techs[techid]['default-ref-units']['capacity'], },
        {'type': 'fopex_rel', 'reference_unit_def': '1', },
        *({'type': typeid, 'reference_unit_def': techs[techid]['default-ref-units']['operation'], }
          for typeid in ['fopex_tot', 'energy_dem', 'feedstock_dem']),
    ]
    df = df.merge(pd.DataFrame.from_records(default_ref_units), on='type')
    df = df \
        .assign(reference_unit=np.where(df['reference_unit'].isnull(), df['reference_unit_def'],
                                        df['reference_unit'])) \
        .drop(columns=['reference_unit_def'])

    return df
