import pandas as pd


def fullMerge(left: pd.DataFrame, right: pd.DataFrame) -> pd.DataFrame:
    # determine indexes
    leftIndexes = [n for n in left.index.names if n is not None]
    rightIndexes = [n for n in right.index.names if n is not None]
    commonIndexes = [n for n in leftIndexes if n in rightIndexes]
    allIndexes = [n for n in set(leftIndexes + rightIndexes)]

    # merge datatable with assumptions
    mergeMode = dict(on=commonIndexes, how='outer') if commonIndexes else dict(how='cross')
    ret = pd.merge(
        left.reset_index() if leftIndexes else left,
        right.reset_index() if rightIndexes else right,
        **mergeMode
    )

    return ret.set_index(allIndexes) if allIndexes else ret
