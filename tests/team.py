import unittest


class team(unittest.TestCase):
    # load all ted files
    def test_team(self):
        import pandas as pd
        from posted.noslag import DataSet
        import posted.team

        data = pd.concat([
            DataSet('Tech|ELH2').aggregate(
                period=[2030, 2040], subtech=['AEL', 'PEM'], size=['1 MW', '100 MW'],
                agg=['subtech', 'source'], override={'Tech|ELH2|Output Capacity|h2': 'kW;LHV'},
            ),
            DataSet('Tech|IDR').aggregate(
                period=[2030, 2040], mode='h2',
            ),
            DataSet('Tech|EAF').aggregate(
                period=[2030, 2040], mode='Primary', reheating='w/ reheating',
            ),
        ]).reset_index(drop=True)

        print(data.team.groupby_fields().groups)


if __name__ == '__main__':
    unittest.main()
