from shutil import rmtree, copytree


def attach_data(setup_kwargs):
    rmtree('python/posted/data', ignore_errors=True)
    copytree('inst/extdata/', 'python/posted/data/')
    return setup_kwargs


if __name__ == '__main__':
    attach_data({})
