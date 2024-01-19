import unittest


class TEDSelect(unittest.TestCase):
    # load all ted files
    def test_select(self):
        from posted.noslag import DataSet
        DataSet('Tech|ELH2').normalise()
        DataSet('Tech|ELH2').select()
        DataSet('Tech|ELH2').aggregate()
        DataSet('Tech|DAC').normalise()
        DataSet('Tech|DAC').select()
        DataSet('Tech|DAC').aggregate()


if __name__ == '__main__':
    unittest.main()
