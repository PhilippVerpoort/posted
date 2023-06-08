from pathlib import Path


# determine data path
BASE_PATH = Path(__file__).parent.resolve()
if (BASE_PATH.parent.parent / 'inst' / 'extdata' / '.anchor').exists():
    DATA_PATH = BASE_PATH.parent.parent / 'inst' / 'extdata'
elif (BASE_PATH / 'data' / '.anchor').exists():
    DATA_PATH = BASE_PATH / 'data'
else:
    raise Exception("Could not find data anchor.")


def pathOfFile(dname, fname: str):
    return (BASE_PATH / dname / fname).resolve()


def pathOfDataFile(fname: str):
    return (DATA_PATH / fname).resolve()


def pathOfTEDFile(tid: str):
    return (DATA_PATH / 'teds' / f"{tid}.csv").resolve()


def pathOfOutputFile(fname: str):
    return (BASE_PATH / 'output' / fname).resolve()
