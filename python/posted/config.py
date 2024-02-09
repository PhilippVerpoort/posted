from posted.path import databases
from posted.definitions import read_definitions
from posted.read import read_csv_file


# loop over databases
flows = {}
techs = {}
for database_path in databases.values():
    # read flow types
    flow_types = read_csv_file(database_path / 'flow_types.csv')

    print("flow_types")
    print(flow_types)
    print("pivoted")
    print(flow_types.pivot(index='flow_id', columns='attribute', values='value'))
    flows |= read_csv_file(database_path / 'flow_types.csv').pivot(index='flow_id', columns='attribute', values='value').to_dict('index')

    # read technologies
    techs |= read_csv_file(database_path / 'tech_types.csv').set_index('tech_id').to_dict('index')

# print(flows)
# print(techs)
# loop over databases and read definitions
variables = {}
for database_path in databases.values():
    variable_definitions = read_definitions(database_path / 'definitions' / 'variable', flows, techs)
    print(variable_definitions)
    # load variable definitions
    variables |= read_definitions(database_path / 'definitions' / 'variable', flows, techs)
