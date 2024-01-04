import unittest


class TEDSelect(unittest.TestCase):
    # load all ted files
    def test_select(self):
        from posted.ted.TEDataSet import TEDataSet
        TEDataSet('Tech|ELH2').prepare()
        TEDataSet('Tech|ELH2').select()


if __name__ == '__main__':
    unittest.main()
