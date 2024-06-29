import unittest
import sys

class noslag(unittest.TestCase):
    # load all ted files
    def test_select(self):
        from posted.noslag import DataSet
        DataSet('Tech|Electrolysis').normalise()
        DataSet('Tech|Electrolysis').select()
        DataSet('Tech|Electrolysis').aggregate()
        DataSet('Tech|Direct Air Capture').normalise()
        DataSet('Tech|Direct Air Capture').select()
        DataSet('Tech|Direct Air Capture').aggregate()
        DataSet('Tech|Iron Direct Reduction').normalise()
        DataSet('Tech|Iron Direct Reduction').select()
        DataSet('Tech|Iron Direct Reduction').aggregate()
        DataSet('Tech|Electric Arc Furnace').normalise()
        DataSet('Tech|Electric Arc Furnace').select()
        DataSet('Tech|Electric Arc Furnace').aggregate()


if __name__ == '__main__':
    unittest.main()
