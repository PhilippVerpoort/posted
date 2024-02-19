import unittest


class tedf(unittest.TestCase):
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


if __name__ == '__main__':
    unittest.main()
