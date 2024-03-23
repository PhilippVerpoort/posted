import unittest


class noslag(unittest.TestCase):
    # load all ted files
    def test_select(self):
        from posted.noslag import DataSet
        DataSet('Tech|ELH2').normalise()
        DataSet('Tech|ELH2').select()
        DataSet('Tech|ELH2').aggregate()
        DataSet('Tech|DAC').normalise()
        DataSet('Tech|DAC').select()
        DataSet('Tech|DAC').aggregate()
        DataSet('Tech|IDR').normalise()
        DataSet('Tech|IDR').select()
        DataSet('Tech|IDR').aggregate()
        DataSet('Tech|EAF').normalise()
        DataSet('Tech|EAF').select()
        DataSet('Tech|EAF').aggregate()


if __name__ == '__main__':
    unittest.main()
