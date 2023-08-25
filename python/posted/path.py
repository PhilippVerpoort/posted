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
    """ Returns the path of a file in a given directory.	

    Parameters
    ----------
    dname : str
        The directory name.
    fname : str
        The file name.

    Returns
    -------
    Path
        The path of the file.
    """
    return (BASE_PATH / dname / fname).resolve()


def pathOfDataFile(fname: str):
    """ Returns the path of a file in the data directory.

    Parameters
    ----------
    fname : str
        The file name.

    Returns
    -------
    Path
        The path of the file.
    """
    return (DATA_PATH / fname).resolve()


def pathOfTEDFile(tid: str):
    """ Returns the path of a TED data file in the TED directory.	

    Parameters
    ----------
    tid : str
        The technology ID.

    Returns
    -------
    Path
        The path of the file.
    """
    return (DATA_PATH / 'teds' / f"{tid}.csv").resolve()


def pathOfOutputFile(fname: str):
    """ Returns the path of a file in the output directory.

    Parameters
    ----------
    fname : str
        The file name.

    Returns
    -------
    Path
        The path of the file.
    """
    return (BASE_PATH / 'output' / fname).resolve()
