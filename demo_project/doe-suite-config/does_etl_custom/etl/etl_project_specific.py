
from doespy.etl.steps.transformers import Transformer


import pandas as pd
from typing import Dict, List
import matplotlib.pyplot as plt


class MyTransformer(Transformer):

    # transformer specific parameters with default values (see pydantic)
    arg: str = None

    def transform(self, df: pd.DataFrame, _options: Dict) -> pd.DataFrame:
        print(f"MyTransformer: do nothing with arg={self.arg} ({df.info()})")
        return df
