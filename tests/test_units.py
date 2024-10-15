import unittest


class Units(unittest.TestCase):
    # importing all components of the units module
    def test_import(self):
        pass

    # using the unit registry to create some standard units
    def test_ureg(self):
        from posted.units import ureg
        ureg('kg')
        ureg('MWh')
        ureg('m**3')
        ureg('USD_2005')

    # check which units are allowed in the context of dimensions and flowIDs
    def test_allowed(self):
        from posted.units import unit_allowed

        # mass flows are allowed without variant for all materials but not for electricity or heat
        self.assertTrue(unit_allowed('t', 'Hydrogen', '[flow]')[0])
        self.assertTrue(unit_allowed('t', 'Ammonia', '[flow]')[0])
        self.assertFalse(unit_allowed('t', 'Electricity', '[flow]')[0])
        self.assertFalse(unit_allowed('t',  'Heat', '[flow]')[0])

        # energy flows of materials must be accompanied by a variant
        self.assertFalse(unit_allowed('MWh', 'Hydrogen', '[flow]')[0])
        self.assertFalse(unit_allowed('MW', 'Hydrogen', '[flow]/[time]')[0])
        self.assertTrue(unit_allowed('MWh;LHV', 'Hydrogen', '[flow]')[0])
        self.assertTrue(unit_allowed('MWh;HHV', 'Hydrogen', '[flow]')[0])
        self.assertTrue(unit_allowed('MW;LHV', 'Hydrogen', '[flow]/[time]')[0])
        self.assertTrue(unit_allowed('MW;HHV', 'Hydrogen', '[flow]/[time]')[0])

    def test_convert(self):
        from posted.units import unit_convert
        self.assertEqual(unit_convert('kWh', 'MWh', 'Electricity'), 0.001)
        self.assertAlmostEqual(unit_convert('MWh;HHV', 'm**3;std', 'Hydrogen'), 282.24994983007144, 5)
        self.assertAlmostEqual(unit_convert('MWh/a;HHV', 'kg/a', 'Hydrogen'), 25.374270489723422, 5)
        self.assertAlmostEqual(unit_convert('MW;LHV', 't/a', 'Hydrogen'), 262.82628262826285, 5)


if __name__ == '__main__':
    unittest.main()
