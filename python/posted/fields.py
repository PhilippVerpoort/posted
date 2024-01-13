from abc import abstractmethod
from typing import Union

import numpy as np
import pandas as pd


class AbstractFieldDefinition:
    def __init__(self, field_id: str):
        self._field_id: str = field_id

    @property
    def id(self) -> str:
        return self._field_id

    @property
    @abstractmethod
    def type(self):
        pass

    @property
    def is_coded(self) -> bool:
        return False

    @property
    def codes(self) -> None | list[str]:
        return None

    @property
    @abstractmethod
    def allowed_types(self):
        pass

    def is_allowed(self, value: str | float | int) -> bool:
        if self.is_coded:
            return value in (self.codes + ['*', '#'])
        else:
            return True

    # select and expand field based on values provided
    def select_and_expand(self, df: pd.DataFrame, field_vals: list) -> pd.DataFrame:
        if self.type == 'cases':
            df = pd.concat([
                df[df[self.id].isin(field_vals)],
                df[df[self.id] == '*']
                .drop(columns=[self.id])
                .merge(pd.DataFrame.from_dict({self.id: field_vals}), how='cross'),
            ])
        elif self._fields[self.id]['type'] == 'components':
            df = df.query(f"{self.id}.isin({field_vals})")

        # return
        return df.reset_index(drop=True)


class PeriodFieldDefinition(AbstractFieldDefinition):
    def __init__(self):
        super().__init__('period')

    @property
    def type(self) -> str:
        return 'cases'

    @property
    def allowed_types(self):
        return Union[int, float]

    # group by identifying columns and select periods/generate time series
    def select_and_expand(self, df: pd.DataFrame, field_vals: list[int | float]) -> pd.DataFrame:
        # expands asterisk values
        df = pd.concat([
                df[df['period'] != '*'],
                df[df['period'] == '*']
                .drop(columns=['period'])
                .merge(pd.DataFrame.from_dict({'period': field_vals}), how='cross'),
            ]).astype({'period': 'float'})

        # get list of groupable columns
        group_cols = [
            c for c in df.columns
            if c not in ['period', 'value']
        ]

        # perform groupby and do not drop NA values
        grouped = df.groupby(group_cols, dropna=False)

        # create return list
        ret = []

        # loop over groups
        for keys, rows in grouped:
            # get rows in group
            rows = rows[['period', 'value']]

            # get a list of periods that exist
            periods_exist = rows['period'].unique()

            # create dataframe containing rows for all requested periods
            req_rows = pd.DataFrame.from_dict({
                'period': field_vals,
                'period_upper': [min([ip for ip in periods_exist if ip >= p], default=np.nan) for p in field_vals],
                'period_lower': [max([ip for ip in periods_exist if ip <= p], default=np.nan) for p in field_vals],
            })

            # set missing columns from group
            req_rows[group_cols] = keys

            # check case
            cond_match = req_rows['period'].isin(periods_exist)
            cond_extrapolate = (req_rows['period_upper'].isna() | req_rows['period_lower'].isna())

            # match
            rows_match = req_rows.loc[cond_match] \
                .merge(rows, on='period')

            # extrapolate
            rows_extrapolate = req_rows.loc[~cond_match & cond_extrapolate] \
                .assign(period_combined=lambda x: np.where(x.notna()['period_upper'], x['period_upper'], x['period_lower'])) \
                .merge(rows.rename(columns={'period': 'period_combined'}), on='period_combined')

            # interpolate
            rows_interpolate = req_rows.loc[~cond_match & ~cond_extrapolate] \
                .merge(rows.rename(columns={c: f"{c}_upper" for c in rows.columns}), on='period_upper') \
                .merge(rows.rename(columns={c: f"{c}_lower" for c in rows.columns}), on='period_lower') \
                .assign(value=lambda row: row['value_lower'] + (row['period_upper'] - row['period']) /
                       (row['period_upper'] - row['period_lower']) * (row['value_upper'] - row['value_lower']))

            # combine into one dataframe and drop unused columns
            rows_append = pd.concat([rows_match, rows_extrapolate, rows_interpolate]) \
                .drop(columns=['period_upper', 'period_lower', 'period_combined', 'value_upper', 'value_lower'])

            # add to return list
            ret.append(rows_append)

        # convert return list to dataframe and return
        return pd.concat(ret).reset_index(drop=True)


class SourceFieldDefinition(AbstractFieldDefinition):
    def __init__(self):
        super().__init__('source')

    @property
    def type(self) -> str:
        return 'cases'

    @property
    def allowed_types(self):
        return str


class CustomFieldDefinition(AbstractFieldDefinition):
    def __init__(self, field_id: str, **field_specs):
        super().__init__(field_id)
        self._field_specs: dict = field_specs

        # check consistency of custom field definition
        assert 'name' in field_specs and isinstance(field_specs['name'], str)
        assert 'type' in field_specs and isinstance(field_specs['type'], str)
        if field_specs['type'] != 'comment':
            assert 'coded' in field_specs and isinstance(field_specs['coded'], bool)
            if field_specs['coded']:
                assert ('codes' in field_specs and
                        isinstance(field_specs['codes'], dict) and
                        all(isinstance(c, str) for c in field_specs['codes']))

    @property
    def type(self) -> str:
        return self._field_specs['type']

    @property
    def is_coded(self) -> bool:
        return self._field_specs['coded']

    @property
    def codes(self) -> list[str]:
        return list(self._field_specs['codes'].keys()) if self._field_specs['coded'] else None

    @property
    def allowed_types(self):
        return str
