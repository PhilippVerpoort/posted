from src.read.file_read import readBATFile


column_list = [
    'Technology',
    'Mode',
    'Type',
    'Component',
    'Subcomponent',
    'Region',
    'Period',
    'Reported value',
    'Reported uncertainty',
    'Reported unit',
    'Non-unit conversion factor',
    'Value and uncertainty comment',
    'Source reference',
    'Source comment'
]


def read_bat(techname: str):
    return readBATFile(techname, column_list)
