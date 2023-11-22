import unittest


class Units(unittest.TestCase):
    # importing the TEDataFile class
    def test_import(self):
        from posted.ted.TEDataFile import TEDataFile

    # load all ted files
    def test_ted(self):
        from posted.ted.TEDataFile import TEDataFile
        TEDataFile('Tech|ELH2').load().check()

    # load all ted files
    def test_ted2(self):
        from posted.ted.TEDataSet import TEDataSet
        TEDataSet('Tech|ELH2')


if __name__ == '__main__':
    unittest.main()
