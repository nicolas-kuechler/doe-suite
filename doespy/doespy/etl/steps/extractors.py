from abc import ABC, abstractmethod, abstractproperty
from typing import List, Dict, Union
from typing import ClassVar

import warnings
import ruamel.yaml
import json
import csv
from dataclasses import dataclass, field

import sys
import inspect

from pydantic import BaseModel, validator


class Extractor(BaseModel, ABC):

    file_regex: Union[str, List[str]] = None

    class Config:
        extra = "forbid"

    @classmethod
    def default_file_regex(cls):
        pass

    @validator("file_regex", pre=True, always=True)
    def set_default_regex(cls, value):

        if value is None:
            value = cls.default_file_regex()

        if not isinstance(value, list):
            value = [value]

        return value

    @abstractmethod
    def extract(self, path: str, options: Dict) -> List[Dict]:
        """Reads the file defined by `path`, and converts it into a list of dicts.
            For example, the CsvExtractor reads a csv and returns a dict for each row.
        Args:
            path (str): absolute path of file to extract
            options (Dict): extractor options as provided in the ETL definition
        Returns:
            List[Dict]: results found in the file
        """

        # NOTE: Extending classes should not use the `options: Dict` and instead use instance variables for parameters


        pass


class YamlExtractor(Extractor):

    """
    The `YamlExtractor` reads result files as YAML.

    The YAML file can contain either a single object (result)
    or a list of objects (results).

    .. code-block:: yaml
        :caption: Example ETL Pipeline Design

        $ETL$:
            extractors:
                YamlExtractor: {}         # with default file_regex
                YamlExtractor:            # with custom file_regex
                    file_regex: [out.yml]

    """

    file_regex: Union[str, List[str]] = [r".*\.yaml$", r".*\.yml$"]

    def extract(self, path: str, options: Dict) -> List[Dict]:
        # load file as yaml: if top level element is object -> return one element list
        with open(path, "r") as f:
            data = ruamel.yaml.safe_load(f)
        if not isinstance(data, list):
            data = [data]
        return data


class JsonExtractor(Extractor):
    """
    The `JsonExtractor` reads result files as JSON.
    The JSON file can contain either a single object (result)
    or a list of objects (results).

    .. code-block:: yaml
        :caption: Example ETL Pipeline Design

        $ETL$:
            extractors:
                JsonExtractor: {}         # with default file_regex
                JsonExtractor:            # with custom file_regex
                    file_regex: [out.json]

    """

    file_regex: Union[str, List[str]] = [r".*\.json$"]


    def extract(self, path: str, options: Dict) -> List[Dict]:
        # load file as json: if top level element is object -> return one element list
        with open(path, "r") as f:
            data = json.load(f)

        if not isinstance(data, list):
            data = [data]

        return data


class CsvExtractor(Extractor):
    """
    The `CsvExtractor` reads result files as CSV.
    The CSV file contains a result per line and by default starts with a header row,
    see ``has_header`` and ``fieldnames`` for CSV files without header.

    .. code-block:: yaml
       :caption: Example ETL Pipeline Design

        $ETL$:
            extractors:
                CsvExtractor: {}         # with default params
                CsvExtractor:            # with custom params
                    file_regex: [out.csv]
                    delimiter: ;
                    has_header: False
                    fieldnames: [col1, col2, col3]
    """

    file_regex: Union[str, List[str]] = [r".*\.csv$"]
    """The regex list to match result files."""

    delimiter: str = ","
    """The separator between columns."""

    has_header: bool = True
    """Indicates whether the first CSV row is a header or not."""

    fieldnames: List[str] = None
    """The names of the CSV columns if ``has_header`` is set to `False`"""


    def extract(self, path: str, options: Dict) -> List[Dict]:
        # load file as csv: by default treats the first line as a header
        #   for each later row, we create a dict and add it to the result list to return

        data = []

        with open(path, "r") as f:

            if self.has_header or self.fieldnames is not None:
                reader = csv.DictReader(f, delimiter=self.delimiter, fieldnames=self.fieldnames)
            else:
                reader = csv.reader(f, delimiter=self.delimiter)
            for row in reader:
                data.append(row)

        return data


class ErrorExtractor(Extractor):
    """
    The `ErrorExtractor` provides a mechanism to detect potential errors in an experiment job.
    For experiments with a large number of jobs, it is easy to overlook an error
    because there are many output folders and files e.g., the stderr.log of each job.

    The `ErrorExtractor` raises a warning if matching files are not empty.

    .. code-block:: yaml
       :caption: Example ETL Pipeline Design

        $ETL$:
            extractors:
                ErrorExtractor: {}         # checking stderr.log
                ErrorExtractor:            # checking custom files
                    file_regex: [stderr.log, error.log]
    """


    file_regex: Union[str, List[str]] = ["^stderr.log$"]
    """The regex list to match result files."""


    def extract(self, path: str, options: Dict) -> List[Dict]:
        # if the file is present and not empty, then throws a warning
        with open(path, "r") as f:
            content = f.read().replace("\n", " ")

        if (
            content.strip() and not content.strip().isspace()
        ):  # ignore empty error files
            # TODO [nku] should we not raise an error in the etl pipeline?
            warnings.warn(f"found error file: {path}")
            warnings.warn(f"   {content}")
        return []


class IgnoreExtractor(Extractor):
    """
    The `IgnoreExtractor` provides a mechanism to detect potential errors in an experiment job.
    For experiments with a large number of jobs, it is easy to overlook an error
    indicted by the presence of an unexpected file.

    As a result, the ETL requires that every file in the results folder of the job
    must be matched by exactly one Extractor.

    The `IgnoreExtractor` can be used to ignore certain files on purpose, e.g., stdout.log.

    .. code-block:: yaml
       :caption: Example ETL Pipeline Design

        $ETL$:
            extractors:
                IgnoreExtractor: {}        # ignore stdout.log
                IgnoreExtractor:           # custom ignore list
                    file_regex: [stdout.log, other.txt]
    """

    file_regex: Union[str, List[str]] = ["^stdout.log$"]
    """The regex list to match result files."""


    def extract(self, path: str, options: Dict) -> List[Dict]:
        # ignore this file
        #  -> every file produced by an experiment run needs to be matched to exactly one extractor.
        #       the ignore extractor can be used to ignore some files
        return []


__all__ = [name for name, cl in inspect.getmembers(sys.modules[__name__], inspect.isclass) if name!="Extractor" and issubclass(cl, Extractor) ]