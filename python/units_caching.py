from posted.config import flows
from posted.units import ureg, unit_convert
from posted.path import DATA_PATH
import os
import pandas as pd


# check allowed dimensions for a flow type
def allowed_flow_dims(flow_type: None | str):
    if flow_type != flow_type:
        allowed_dims = ['[currency]']
    else:
        flow_type_data = flows[flow_type]
        allowed_dims = [str(ureg.Quantity(flow_type_data['default_unit'].split(
            ';')[0]).dimensionality)]  # default units dim is always accepted
        if (flow_type_data['energycontent_LHV'] == flow_type_data['energycontent_LHV'] or
           flow_type_data['energycontent_HHV'] == flow_type_data['energycontent_HHV']):
            if '[length] ** 2 * [mass] / [time] ** 2' not in allowed_dims:
                allowed_dims += ['[length] ** 2 * [mass] / [time] ** 2']
            if '[mass]' not in allowed_dims:  # [mass] is always accepted when there is a energydensity
                allowed_dims += ['[mass]']

        if (flow_type_data['density_norm'] == flow_type_data['density_norm'] or
                flow_type_data['density_std'] == flow_type_data['density_std']):
            allowed_dims += ['[volume]']
            allowed_dims += ['[length] ** 3']
            if '[mass]' not in allowed_dims:  # [mass] is always accepted when there is a energydensity
                allowed_dims += ['[mass]']

    return allowed_dims


# Collect a list of all unique units that appear in all the inout data files
compatible_units = []

# Define a list of all units, that should have conversion factors from and to,
# regardless of their occurrence in data files
standard_units = ["kW", "MW", "GW", "kWh", "MWh", "GWh", "t", "kg"]
standard_units_per_year = [unit + "/a" for unit in standard_units]
standard_units_per_day = [unit + "/d" for unit in standard_units]
standard_units_per_hour = [unit + "/h" for unit in standard_units]
standard_units_times_year = ["a*" + unit for unit in standard_units]
standard_units_times_day = ["d*" + unit for unit in standard_units]
standard_units_times_hour = ["h*" + unit for unit in standard_units]


standard_units = standard_units + standard_units_per_year + standard_units_per_day + \
    standard_units_per_hour + standard_units_times_day + \
    standard_units_times_hour + standard_units_times_year

print(standard_units)
# Create an empty DataFrame to store the appended data
appended_data = pd.DataFrame()
# Loop through all ted files
for filename in os.listdir(DATA_PATH / 'database/tedfs/Tech/'):
    filepath = os.path.join(DATA_PATH / 'database/tedfs/Tech/', filename)
    # Check if the file is a CSV file
    if filename.endswith(".csv"):

        # Read the ted file and extract only columns
        # "reported_unit" and "reference_unit"
        data = pd.read_csv(filepath, usecols=["unit", "reference_unit"])

        # Append the data to the main DataFrame
        appended_data = pd.concat([appended_data, data], ignore_index=True)

# Get unique values from columns "reported_unit" and "reference_unit"
unique_values = appended_data[["unit", "reference_unit"]].values.ravel()

unique_values = pd.unique(unique_values).tolist()
unique_values = list(set(unique_values + standard_units))

# define unit sets
mass_units = []
volume_units = []
energy_units = []
other_units = []

# ----- Divide the found units into categories based on
# dimension and append extensions to them (LHV/HHV/norm/standard)

# loop through all found unqiue unit entries
for unit_str in unique_values:
    if unit_str == unit_str:
        # extra unit info (LHV/HHV/norm/standard) is cut for now
        if len(unit_str.split(';')) > 1:
            unit_str = unit_str.split(';')[0]
        if unit_str in ureg:
            unit = getattr(ureg, unit_str)
            # check if unit has a valid dimension
            if hasattr(unit, 'dimensionality'):
                if unit.dimensionality == '[length] ** 2 * [mass] / [time] ** 2':
                    # energy units are appened with LHV and HHV
                    energy_units.append(unit_str)
                    energy_units.append(unit_str + ';LHV')
                    energy_units.append(unit_str + ';HHV')
                # add power units here
                elif unit.dimensionality == '[length] ** 2 * [mass] / [time] ** 3':
                    energy_units.append(unit_str)
                    energy_units.append(unit_str + ';LHV')
                    energy_units.append(unit_str + ';HHV')
                elif unit.dimensionality == '[length] ** 3' or unit.dimensionality == '[volume]':
                    # volume units are appened with norm and standard
                    volume_units.append(unit_str)
                    volume_units.append(unit_str + ';norm')
                    volume_units.append(unit_str + ';std')
                elif unit.dimensionality == '[length] ** 3 / [time]' or unit.dimensionality == '[volume] /[time]':
                    # volume units are appened with norm and standard
                    volume_units.append(unit_str)
                    volume_units.append(unit_str + ';norm')
                    volume_units.append(unit_str + ';std')
                elif unit.dimensionality == '[mass] / [time]':
                    # mass units are not augmented
                    mass_units.append(unit_str)
                elif unit.dimensionality == '[mass]':
                    # mass units are not augmented
                    mass_units.append(unit_str)
                # all units without extra info are the units
                #
                # that are convertable without a flow_type
                other_units.append(unit_str)

# TODO: do automatic adjustment on the base year defined in units.py

other_units.append("EUR_2005")
other_units.append("USD_2005")
other_units.append("EUR_2005/a")
other_units.append("USD_2005/a")


# ----- Define all possible conversions for each entry type
# and additionally for a missing entry type

# define conversion set
conversions = []

# add all other units to enable conversion without specifying the flow_type
for unit_from in other_units:
    # iterate over all the commpatible units for the unit_from and
    # unit_to variable to create all possible combinations
    for unit_to in other_units:
        if (unit_from != unit_to):
            conversion = dict(unit_from=unit_from,
                              unit_to=unit_to, flow_type='')
            conversions.append(conversion)

# for reference_unit, all combinations disregarding
# the flow_type limitations are added
# iterate over all flow types
for flow_type in flows.keys():
    # get allowed dimensions for the flow type
    allowed_dims = allowed_flow_dims(flow_type)

    # define a set of all possible units for this flow type
    compatible_units = []
    # add units to the compatible units set depending on
    # whether flow types allowed dimensions
    if ('[mass]' in allowed_dims):

        compatible_units += mass_units

    if ('[length] ** 2 * [mass] / [time] ** 2' in allowed_dims):

        compatible_units += energy_units
    if ('[length] ** 3' in allowed_dims):

        compatible_units += volume_units

    # iterate over all the commpatible units for the unit_from
    # and unit_to variable to create all possible combinations
    for unit_from in compatible_units:
        for unit_to in compatible_units:
            if (unit_from != unit_to):
                # add each combination to the conversions set
                conversion = dict(unit_from=unit_from,
                                  unit_to=unit_to, flow_type=flow_type)
                conversions.append(conversion)

# ----- Add combinations of units that are not contained in the data
conversions.append(dict(
    unit_from='percent',
    unit_to='dimensionless',
    flow_type='',
))
conversions.append(dict(
    unit_from='dimensionless',
    unit_to='percent',
    flow_type='',
))
conversions.append(dict(
    unit_from='pct',
    unit_to='dimensionless',
    flow_type='',
))
conversions.append(dict(
    unit_from='dimensionless',
    unit_to='pct',
    flow_type='',
))
conversions.append(dict(
    unit_from='percent',
    unit_to='pct',
    flow_type='',
))
conversions.append(dict(
    unit_from='pct',
    unit_to='percent',
    flow_type='',
))
conversions.append(dict(
    unit_from='hour',
    unit_to='h',
    flow_type='',
))
conversions.append(dict(
    unit_from='h',
    unit_to='hour',
    flow_type='',
))
conversions.append(dict(
    unit_from='a',
    unit_to='h',
    flow_type='',
))
conversions.append(dict(
    unit_from='h',
    unit_to='a',
    flow_type='',
))
# ----- Call convUnit for each of the conversions and
# save the result in the cache dataframe

# use dictionary list to temporarily store data for better performance
new_row_list = []

for conversion in conversions:
    unit_from = conversion['unit_from']
    unit_to = conversion['unit_to']
    flow_type = ''
    # use try except block to catch Dimensionality errors, only valid
    # combinations will end up in cache and
    #  no logic is needed here to check validity
    try:
        if conversion['flow_type'] == '':
            result = unit_convert(unit_from, unit_to)
        else:
            flow_type = conversion['flow_type']
            result = unit_convert(unit_from, unit_to, flow_type)
        # TODO: check if there should be a specific error as in previous
        # version: pint.errors.DimensionalityError: skip this conversion and
        # dont add it to cache
    except:
        continue
    new_row = {
        'from': unit_from,
        'to': unit_to,
        'ft': flow_type,
        'factor': f"{result:.9f}"
    }

    # Append the new row to the dictionary list.
    new_row_list.append(new_row)

# Generate dataframe.
df_cache = pd.DataFrame.from_dict(new_row_list)

# Save dataframe to CSV file.
path = DATA_PATH / 'R_unit_cache.csv'
df_cache.to_csv(
    path,
    index=False,
    sep=',',
    quotechar='"',
    encoding='utf-8',
    na_rep='',
)
