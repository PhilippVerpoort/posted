from src.path import pathOfBATFile
from src.read.file_read import readYAMLDataFile


# load list of technologies and specifications
techs = readYAMLDataFile('technologies')


# make sure BAT files exist
techs_missing = [t for t in techs if not pathOfBATFile(t).exists()]
if techs_missing:
    raise Exception(f"BAT files missing for technologies: {techs_missing}")
