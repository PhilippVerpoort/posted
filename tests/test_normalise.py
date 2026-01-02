import unittest


class TestNormalise(unittest.TestCase):

    def test_normalise(self):
        from posted import TEDF
        ely = TEDF.load("Tech|Electrolysis")
        ely.normalise()
