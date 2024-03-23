from typing import Optional

import numpy as np
import pandas as pd

from posted.config import variables
from posted.path import databases
from posted.read import read_yml_file
from posted.settings import default_periods
from posted.units import ureg, unit_variants


def is_float(string: str) -> bool:
    try:
        float(string)
        return True
    except ValueError:
        return False


class AbstractColumnDefinition:
    def __init__(self, col_type: str, name: str, description: str, dtype: str, required: bool):
        if col_type not in ['field', 'variable', 'unit', 'value', 'comment']:
            raise Exception(f"Columns must be of type field, variable, unit, value, or comment but found: {col_type}")
        if not isinstance(name, str):
            raise Exception(f"The 'name' must be a string but found type {type(name)}: {name}")
        if not isinstance(description, str):
            raise Exception(f"The 'description' must be a string but found type {type(description)}: {description}")
        if not (isinstance(dtype, str) and dtype in ['float', 'str', 'category']):
            raise Exception(f"The 'dtype' must be a valid data type but found: {dtype}")
        if not isinstance(required, bool):
            raise Exception(f"The 'required' argument must be a bool but found: {required}")

        self._col_type: str = col_type
        self._name: str = name
        self._description: str = description
        self._dtype: str = dtype
        self._required: bool = required

    @property
    def col_type(self):
        return self._col_type

    @property
    def name(self):
        return self._name

    @property
    def description(self):
        return self._description

    @property
    def dtype(self):
        return self._dtype

    @property
    def required(self):
        return self._required

    @property
    def default(self):
        return np.nan

    def is_allowed(self, cell: str | float | int) -> bool:
        return True


class VariableDefinition(AbstractColumnDefinition):
    def __init__(self, name: str, description: str, required: bool):
        super().__init__(
            col_type='variable',
            name=name,
            description=description,
            dtype='category',
            required=required,
        )

    def is_allowed(self, cell: str | float | int) -> bool:
        if pd.isnull(cell):
            return not self._required
        return isinstance(cell, str) and cell in variables


class UnitDefinition(AbstractColumnDefinition):
    def __init__(self, name: str, description: str, required: bool):
        super().__init__(
            col_type='unit',
            name=name,
            description=description,
            dtype='category',
            required=required,
        )

    def is_allowed(self, cell: str | float | int) -> bool:
        if pd.isnull(cell):
            return not self._required
        if not isinstance(cell, str):
            return False
        tokens = cell.split(';')
        if len(tokens) == 1:
            return cell in ureg
        elif len(tokens) == 2:
            return tokens[0] in ureg and tokens[1] in unit_variants
        else:
            return False


class ValueDefinition(AbstractColumnDefinition):
    def __init__(self, name: str, description: str, required: bool):
        super().__init__(
            col_type='value',
            name=name,
            description=description,
            dtype='float',
            required=required,
        )

    def is_allowed(self, cell: str | float | int) -> bool:
        if pd.isnull(cell):
            return not self._required
        return isinstance(cell, float | int)


class CommentDefinition(AbstractColumnDefinition):
    def __init__(self, name: str, description: str, required: bool):
        super().__init__(
            col_type='comment',
            name=name,
            description=description,
            dtype='str',
            required=required,
        )

    def is_allowed(self, cell: str | float | int) -> bool:
        return True


class AbstractFieldDefinition(AbstractColumnDefinition):
    def __init__(self, field_type: str, name: str, description: str, dtype: str, coded: bool,
                 codes: Optional[dict[str, str]] = None):
        if field_type not in ['case', 'component']:
            raise Exception('Fields must be of type case or component.')
        super().__init__(
            col_type='field',
            name=name,
            description=description,
            dtype=dtype,
            required=True,
        )

        self._field_type: str = field_type
        self._coded: bool = coded
        self._codes: None | dict[str, str] = codes

    @property
    def field_type(self) -> str:
        return self._field_type

    @property
    def coded(self) -> bool:
        return self._coded

    @property
    def codes(self) -> None | dict[str, str]:
        return self._codes

    @property
    def default(self):
        return '*' if self._field_type == 'case' else '#'

    def is_allowed(self, cell: str | float | int) -> bool:
        print("cell = ", cell)
        if pd.isnull(cell):
            return False
        if self._coded:
            # print(self._codes)
            return cell in self._codes or cell == '*' or (cell == '#' and self.col_type == 'component')
        else:
            return True

    def _expand(self, df: pd.DataFrame, col_id: str, field_vals: list, **kwargs) -> pd.DataFrame:
        print("col_id_expand = ", col_id)
        print(pd.concat([
            df[df[col_id].isin(field_vals)],
            df[df[col_id] == '*']
            .drop(columns=[col_id])
            .merge(pd.DataFrame.from_dict({col_id: field_vals}), how='cross'),
        ]))
        return pd.concat([
            df[df[col_id].isin(field_vals)],
            df[df[col_id] == '*']
            .drop(columns=[col_id])
            .merge(pd.DataFrame.from_dict({col_id: field_vals}), how='cross'),
        ])

    def _select(self, df: pd.DataFrame, col_id: str, field_vals: list, **kwargs):
        return df.query(f"{col_id}.isin({field_vals})").reset_index(drop=True)

    # select and expand field based on values provided
    def select_and_expand(self, df: pd.DataFrame, col_id: str, field_vals: None | list, **kwargs) -> pd.DataFrame:
        # get list of selected field values
       # print("field_vals_initial", field_vals)
        if field_vals is None:
            if col_id == 'period':
                field_vals = default_periods
            elif self._coded:
                field_vals = list(self._codes.keys())
            else:
                field_vals = [v for v in df[col_id].unique() if v != '*' and not pd.isnull(v)]
        else:
            # ensure that field values is a list of elements (not tuple, not single value)
            if isinstance(field_vals, tuple):
                field_vals = list(field_vals)
            elif not isinstance(field_vals, list):
                field_vals = [field_vals]
            #print("field_vals = ", field_vals)
            # check that every element is of allowed type
            for val in field_vals:
                #print("val = ", val)
                if not self.is_allowed(val):
                    raise Exception(f"Invalid type selected for field '{col_id}': {val}")
            if '*' in field_vals:
                raise Exception(f"Selected values for field '{col_id}' must not contain the asterisk."
                                f"Omit the '{col_id}' argument to select all entries.")
        print("access expand")
        # expand
        df = self._expand(df, col_id, field_vals, **kwargs)
        print("access select")
        # select
        df = self._select(df, col_id, field_vals, **kwargs)
        print("df after select")
        print(df)
        # return
        return df


class RegionFieldDefinition(AbstractFieldDefinition):
    def __init__(self, name: str, description: str):
        super().__init__(
            field_type='case',
            name=name,
            description=description,
            dtype='category',
            coded=True,
            codes={'World': 'World'},  # TODO: Insert list of country names here.
        )


class PeriodFieldDefinition(AbstractFieldDefinition):
    def __init__(self, name: str, description: str):
        super().__init__(
            field_type='case',
            name=name,
            description=description,
            dtype='float',
            coded=False,
        )

    def is_allowed(self, cell: str | float | int) -> bool:
        return is_float(cell) or cell == '*'

    def _expand(self, df: pd.DataFrame, col_id: str, field_vals: list, **kwargs) -> pd.DataFrame:
        return pd.concat([
            df[df[col_id] != '*'],
            df[df[col_id] == '*']
            .drop(columns=[col_id])
            .merge(pd.DataFrame.from_dict({col_id: field_vals}), how='cross'),
        ]).astype({'period': 'float'})

    # group by identifying columns and select periods/generate time series
    def _select(self, df: pd.DataFrame, col_id: str, field_vals: list[int | float], **kwargs) -> pd.DataFrame:
        # get list of groupable columns
        group_cols = [
            c for c in df.columns
            if c not in [col_id, 'value']
        ]
      
        # perform groupby and do not drop NA values
        grouped = df.groupby(group_cols, dropna=False)
        
        # create return list
        ret = []

        # loop over groups
        for keys, rows in grouped:
          
            # get rows in group
            rows = rows[[col_id, 'value']]
        
            # get a list of periods that exist
            periods_exist = rows[col_id].unique()

            # create dataframe containing rows for all requested periods
            req_rows = pd.DataFrame.from_dict({
                f"{col_id}": field_vals,
                f"{col_id}_upper": [min([ip for ip in periods_exist if ip >= p], default=np.nan) for p in field_vals],
                f"{col_id}_lower": [max([ip for ip in periods_exist if ip <= p], default=np.nan) for p in field_vals],
            })
       
            # set missing columns from group
            req_rows[group_cols] = keys
       
            # check case
            cond_match = req_rows[col_id].isin(periods_exist)
            cond_extrapolate = (req_rows[f"{col_id}_upper"].isna() | req_rows[f"{col_id}_lower"].isna())
           
            # match
            rows_match = req_rows.loc[cond_match] \
                .merge(rows, on=col_id)
     
            # extrapolate
            rows_extrapolate = (
                req_rows.loc[~cond_match & cond_extrapolate]
                    .assign(
                        period_combined=lambda x: np.where(
                            x.notna()[f"{col_id}_upper"],
                            x[f"{col_id}_upper"],
                            x[f"{col_id}_lower"],
                        )
                    )
                    .merge(rows.rename(columns={col_id: f"{col_id}_combined"}), on=f"{col_id}_combined")
                if 'extrapolate_period' not in kwargs or kwargs['extrapolate_period'] else
                pd.DataFrame()
            )
        
            # interpolate
            rows_interpolate = req_rows.loc[~cond_match & ~cond_extrapolate] \
                .merge(rows.rename(columns={c: f"{c}_upper" for c in rows.columns}), on=f"{col_id}_upper") \
                .merge(rows.rename(columns={c: f"{c}_lower" for c in rows.columns}), on=f"{col_id}_lower") \
                .assign(value=lambda row: row['value_lower'] + (row[f"{col_id}_upper"] - row[col_id]) /
                                          (row[f"{col_id}_upper"] - row[f"{col_id}_lower"]) * (row['value_upper'] - row['value_lower']))
     
            # combine into one dataframe and drop unused columns
            rows_to_concat = [df for df in [rows_match, rows_extrapolate, rows_interpolate] if not df.empty]
            if rows_to_concat:
                rows_append = pd.concat(rows_to_concat)
                rows_append.drop(columns=[
                        c for c in [f"{col_id}_upper", f"{col_id}_lower", f"{col_id}_combined", 'value_upper', 'value_lower']
                        if c in rows_append.columns
                    ], inplace=True)

                # add to return list
          
                ret.append(rows_append)
    
        # convert return list to dataframe and return
        return pd.concat(ret).reset_index(drop=True) if ret else df.iloc[[]]


class SourceFieldDefinition(AbstractFieldDefinition):
    def __init__(self, name: str, description: str):
        super().__init__(
            field_type='case',
            name=name,
            description=description,
            dtype='category',
            coded=False,  # TODO: Insert list of BibTeX identifiers here.
        )


class CustomFieldDefinition(AbstractFieldDefinition):
    def __init__(self, **field_specs):
        if not ('type' in field_specs and isinstance(field_specs['type'], str) and
                field_specs['type'] in ['case', 'component']):
            raise Exception("Field type must be provided and equal to 'case' or 'component'.")
        if not ('name' in field_specs and isinstance(field_specs['name'], str)):
            raise Exception('Field name must be provided and of type string.')
        if not ('description' in field_specs and isinstance(field_specs['description'], str)):
            raise Exception('Field description must be provided and of type string.')
        if not ('coded' in field_specs and isinstance(field_specs['coded'], bool)):
            raise Exception('Field coded must be provided and of type bool.')
        if field_specs['coded'] and not ('codes' in field_specs and isinstance(field_specs['codes'], dict)):
            raise Exception('Field codes must be provided and contain a dict of possible codes.')
        super().__init__(
            field_type=field_specs['type'],
            name=field_specs['name'],
            description=field_specs['description'],
            dtype='category',
            coded=field_specs['coded'],
            codes=field_specs['codes'] if 'codes' in field_specs else None,
        )


base_columns = {
    'region': RegionFieldDefinition(
        name='Region',
        description='The region that this value is reported for.',
    ),
    'period': PeriodFieldDefinition(
        name='Period',
        description='The period that this value is reported for.',
    ),
    'variable': VariableDefinition(
        name='Variable',
        description='The reported variable.',
        required=True,
    ),
    'reference_variable': VariableDefinition(
        name='Reference Variable',
        description='The reference variable. This is used as an addition to the reported variable to clear, '
                    'simplified, and transparent data reporting.',
        required=False,
    ),
    'value': ValueDefinition(
        name='Value',
        description='The reported value.',
        required=True,
    ),
    'uncertainty': ValueDefinition(
        name='Uncertainty',
        description='The reported uncertainty.',
        required=False,
    ),
    'unit': UnitDefinition(
        name='Unit',
        description='The reported unit that goes with the reported value.',
        required=True,
    ),
    'reference_value': ValueDefinition(
        name='Reference Value',
        description='The reference value. This is used as an addition to the reported variable to clear, simplified, '
                    'and transparent data reporting.',
        required=False,
    ),
    'reference_unit': UnitDefinition(
        name='Reference Unit',
        description='The reference unit. This is used as an addition to the reported variable to clear, simplified, '
                    'and transparent data reporting.',
        required=False,
    ),
    'comment': CommentDefinition(
        name='Comment',
        description='A generic free text field commenting on this entry.',
        required=False,
    ),
    'source': SourceFieldDefinition(
        name='Source',
        description='A reference to the source that this entry was taken from.',
    ),
    'source_detail': CommentDefinition(
        name='Source Detail',
        description='Detailed information on where in the source this entry can be found.',
        required=True,
    ),
}


def read_fields(variable: str):
    fields: dict[str, CustomFieldDefinition] = {}
    comments: dict[str, CommentDefinition] = {}

    for database_id in databases:
        fpath = databases[database_id] / 'fields' / ('/'.join(variable.split('|')) + '.yml')
        if fpath.exists():
            if not fpath.is_file():
                raise Exception(f"Expected YAML file, but not a file: {fpath}")
            
            for col_id, field_specs in read_yml_file(fpath).items():
                if field_specs['type'] in ('case', 'component'):
                    fields[col_id] = CustomFieldDefinition(**field_specs)
                elif field_specs['type'] == 'comment':
                    comments[col_id] = CommentDefinition(
                        **{k: v for k, v in field_specs.items() if k != 'type'},
                        required=False,
                    )
                else:
                    raise Exception(f"Unkown field type: {col_id}")
    # make sure the field ID is not the same as for a base column
    for col_id in fields:
        if col_id in base_columns:
            raise Exception(f"Field ID cannot be equal to a base column ID: {col_id}")

    return fields, comments
