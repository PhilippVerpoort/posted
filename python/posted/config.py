from posted.path import DATA_PATH, databases
from posted.definitions import read_definitions
from posted.read import read_yml_file, read_csv_file


# read data format and dtypes
base_format_path = DATA_PATH / 'config' / 'base_format.yml'
base_format = read_yml_file(base_format_path)
base_dtypes = {
    col_id: col_specs['dtype']
    for col_id, col_specs in base_format.items()
}


# default selection options
default_periods = [2030, 2040, 2050]


# loop over databases
flows = {}
techs = {}
for database_path in databases.values():
    # read flow types
    flows |= read_csv_file(database_path / 'flow_types.csv').pivot(index='flow_id', columns='attribute', values='value').to_dict('index')

    # read technologies
    techs |= read_csv_file(database_path / 'tech_types.csv').set_index('tech_id').to_dict('index')


# loop over databases and read definitions
variables = {}
for database_path in databases.values():
    # load variable definitions
    variables |= read_definitions(database_path / 'definitions' / 'variable', flows, techs)
