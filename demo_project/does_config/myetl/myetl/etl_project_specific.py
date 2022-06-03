from doespy.etl.etl_base import Extractor, Transformer, Loader, PlotLoader
import pandas as pd
from typing import Dict, List
import matplotlib.pyplot as plt


class MyTransformer(Transformer):

    def transform(self, df: pd.DataFrame, options: Dict) -> pd.DataFrame:
        print(f"MyTransformer: do nothing  ({df.info()})")
        return df
