import unittest
import os
from posted.noslag import DataSet
from posted.path import databases

database = databases["public"]
tech_directory = f"{database}/tedfs/Tech"

tech_files = os.listdir(tech_directory)
tech_files = [filename.split('.')[0] for filename in tech_files]


class TestDataSetMethods(unittest.TestCase):

    def setUp(self):
        # Setup any necessary resources or state before each test
        self.directory = tech_directory
        self.errors = {
            'normalise': [],
            'select': [],
            'aggregate': []
        }

    def test_normalise(self):
        for tech in tech_files:
            try:
                DataSet(f'Tech|{tech}').normalise()
            except Exception as e:
                self.errors['normalise'].append(f"Normalization failed for file '{tech}': {str(e)}")

        # Assert at the end of the test
        self.assertEqual(len(self.errors['normalise']), 0, "\n".join(self.errors['normalise']))

    def test_select(self):
        for tech in tech_files:
            try:
                DataSet(f'Tech|{tech}').select()  # Replace with actual method call
            except Exception as e:
                self.errors['select'].append(f"Selection failed for file '{tech}': {str(e)}")

        # Assert at the end of the test
        self.assertEqual(len(self.errors['select']), 0, "\n".join(self.errors['select']))

    def test_aggregate(self):
        for tech in tech_files:
            try:
                DataSet(f'Tech|{tech}').aggregate()  # Replace with actual method call
            except Exception as e:
                self.errors['aggregate'].append(f"Aggregation failed for file '{tech}': {str(e)}")

        # Assert at the end of the test
        self.assertEqual(len(self.errors['aggregate']), 0, "\n".join(self.errors['aggregate']))

    def tearDown(self):
        # Clean up any resources after each test
        self.errors = {
            'normalise': [],
            'select': [],
            'aggregate': []
        }

class TestCombineUnits(unittest.TestCase):
    def test_combine_units(self):
        from posted.noslag import combine_units
        self.assertEqual(combine_units("m**3", "m**2" ), "m")
        self.assertEqual(combine_units("m", "m"), "m/m")
        self.assertEqual(combine_units("m/s", "km/h"),"m/s/(km/h)")

if __name__ == '__main__':
    unittest.main()



if __name__ == '__main__':
    unittest.main()
