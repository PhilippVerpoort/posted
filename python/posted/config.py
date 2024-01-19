from posted.path import databases
from posted.definitions import read_definitions
from posted.read import read_csv_file


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
