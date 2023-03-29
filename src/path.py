import pathlib


BASE_PATH = pathlib.Path(__file__).parent.parent.resolve()

def pathOfFile(dname, fname):
    return (BASE_PATH / dname / fname).resolve()

def pathOfDataFile(fname):
    return (BASE_PATH / 'data' / fname).resolve()

def pathOfBATFile(fname):
    return (BASE_PATH / 'data' / 'bat' / f"{fname}.csv").resolve()

def pathOfOutputFile(fname):
    return (BASE_PATH / 'output' / fname).resolve()
