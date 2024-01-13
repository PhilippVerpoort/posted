import unittest


class TEDSelect(unittest.TestCase):
    # load all ted files
    def test_select(self):
        from posted.nsha import NSHADataSet
        NSHADataSet('Tech|ELH2').normalise()
        NSHADataSet('Tech|ELH2').select()
        NSHADataSet('Tech|ELH2').harmonise()
        NSHADataSet('Tech|ELH2').aggregate()


if __name__ == '__main__':
    unittest.main()
