import unittest


class tedf(unittest.TestCase):
    # importing the TEDataFile class
    def test_import(self):
        from posted.tedf import TEDF
        pass

    # load all ted files
    def test_ted(self):
        from posted.tedf import TEDF
        tedf = TEDF('Tech|Electrolysis')
        tedf.load()
        tedf.check()
        tedf = TEDF('Tech|Direct Air Capture')
        tedf.load()
        tedf.check()


if __name__ == '__main__':
    unittest.main()
