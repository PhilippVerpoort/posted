import unittest


class TEDFiles(unittest.TestCase):
    # importing the TEDataFile class
    def test_import(self):
        from posted.tedf import TEDF
        pass

    # load all ted files
    def test_ted(self):
        from posted.tedf import TEDF
        tedf = TEDF('Tech|ELH2')
        tedf.load()
        tedf.check()
        tedf = TEDF('Tech|DAC')
        tedf.load()
        tedf.check()

    # load all ted files
    def test_ted2(self):
        from posted.nsha import NSHADataSet
        NSHADataSet('Tech|ELH2').normalise()
        NSHADataSet('Tech|ELH2').normalise(override={'Tech|ELH2|Input Capacity|elec': 'kW'})
        NSHADataSet('Tech|DAC').normalise()


if __name__ == '__main__':
    unittest.main()
