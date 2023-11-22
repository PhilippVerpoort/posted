from pathlib import Path


# determine base path and data path
BASE_PATH = Path(__file__).parent.resolve()
if (BASE_PATH.parent.parent / 'inst' / 'extdata' / '.anchor').exists():
    DATA_PATH = BASE_PATH.parent.parent / 'inst' / 'extdata'
elif (BASE_PATH / 'data' / '.anchor').exists():
    DATA_PATH = BASE_PATH / 'data'
else:
    raise Exception("Could not find data anchor for DATA_PATH.")


# databases and associated paths
databases = {
    'public': DATA_PATH / 'database',
}
