import unittest
import os

from posted.tedf import TEDF
from posted.path import databases


database = databases["public"]
tech_directory = f"{database}/tedfs/Tech"

tech_files = os.listdir(tech_directory)
tech_files = [filename.split('.')[0] for filename in tech_files]


class TestTEDFMethods(unittest.TestCase):

    def setUp(self):
        # Setup any necessary resources or state before each test
        self.directory = tech_directory
        self.errors = {
            'load': [],
            'check': [],
        }

    def test_load(self):
        for tech in tech_files:
            try:
                TEDF(f'Tech|{tech}').load()
            except Exception as e:
                self.errors['load'].append(f"Loading failed for file '{tech}': {str(e)}")

        # Assert at the end of the test
        self.assertEqual(len(self.errors['load']), 0, "\n".join(self.errors['load']))

    def test_check(self):
        for tech in tech_files:
            try:
                TEDF(f'Tech|{tech}').check()
            except Exception as e:
                self.errors['check'].append(f"Checking failed for file '{tech}': {str(e)}")

        # Assert at the end of the test
        self.assertEqual(len(self.errors['check']), 0, "\n".join(self.errors['check']))


    def tearDown(self):
        # Clean up any resources after each test
        self.errors = {
            'load': [],
            'check': [],
        }


if __name__ == '__main__':
    unittest.main()
