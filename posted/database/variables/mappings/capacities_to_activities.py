import pandas as pd

from cet_units import Q

from posted.noslag.mapping import AbstractVariableMapper


class CapacitiesToActivities(AbstractVariableMapper):
    def _condition(self) -> pd.Series:
        pattern = r"^(Input|Output) Capacity\|"
        return (
            self._df["variable"].str.match(pattern) &
            self._df["reference_variable"].str.match(pattern)
        )

    def _map(self, df: pd.DataFrame, cond: pd.Series) -> pd.DataFrame:
        for is_ref, col_id in enumerate(["variable", "reference_variable"]):
            old = df.loc[cond, col_id]
            new = old.str.replace(
                r"^(Input|Output) Capacity\|",
                r"\1|",
                regex=True,
            )
            combined = pd.concat([old, new], axis=1)

            # Insert missing units.
            for _, row in combined.drop_duplicates().iterrows():
                var_old, var_new = row
                if var_new not in self._units:
                    self._units[var_new] = str(
                        Q(self._units[var_old] + " * year")
                        .to_reduced_units()
                        .u
                    )

            conv_factors = (
                combined
                .apply(
                    lambda row: (
                        Q(self._units[row.iloc[0]] + "* year")
                        .to(self._units[row.iloc[1]])
                        .m
                    ),
                    axis=1,
                )
            )
            df.loc[cond, col_id] = new
            if is_ref:
                df.loc[cond, "value"] *= conv_factors
            else:
                df.loc[cond, "value"] /= conv_factors

        return df
