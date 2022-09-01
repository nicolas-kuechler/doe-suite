from abc import ABC, abstractmethod
from typing import List, Dict, Union
from typing import ClassVar

import warnings
import yaml
import json
import csv

import sys
import inspect

from pydantic import BaseModel


class Extractor(BaseModel, ABC):

    file_regex: Union[str, List[str]] = None

    class Config:
        extra = "forbid"

    @property
    @abstractmethod
    def file_regex_default(self):
        pass

    def regex(self):
        if self.file_regex:
            if isinstance(self.file_regex, str):
                return [self.file_regex]
            else:
                return self.file_regex
        else:
            return self.file_regex_default()

    #@abstractmethod
    #def file_regex_default():
    #    """Define regex patterns for matching files based on their name.
    #        All files with a matching name are fed to `extract(..)`
#
    #    Returns:
    #        List[str]: list of regex patterns as raw strings
    #    """
    #    pass
#
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
        pass

# TODO [nku] add docstrings to classes to automatically generate documentation


class YamlExtractor(Extractor):

    file_regex_default:  ClassVar[List[str]] = [r".*\.yaml$", r".*\.yml$"]

    r"""The `YamlExtractor` reads result files as YAML.
    The YAML file can contain either a single object (result)
    or a list of objects (results).

    :param file_regex: The regex list to match result files, defaults to ``[r".*\.yaml$", r".*\.yml$"]``

    .. code-block:: yaml
       :caption: Example ETL Pipeline Design

        $ETL$:
            extractors:
                YamlExtractor: {}         # with default file_regex
                YamlExtractor:            # with custom file_regex
                    file_regex: [out.yml]
    """

    #def file_regex_default(self):
    #    # by default, all files ending in .yaml or .yml are "extracted"
    #    return [r".*\.yaml$", r".*\.yml$"]

    def extract(self, path: str, options: Dict) -> List[Dict]:
        # load file as yaml: if top level element is object -> return one element list
        with open(path, "r") as f:
            data = yaml.load(f, yaml.SafeLoader)
        if not isinstance(data, list):
            data = [data]
        return data


class JsonExtractor(Extractor):

    file_regex_default:  ClassVar[List[str]] = [r".*\.json$"]

    r"""The `JsonExtractor` reads result files as JSON.
    The JSON file can contain either a single object (result)
    or a list of objects (results).

    :param file_regex: The regex list to match result files, defaults to `` [r".*\.json$"]``

    .. code-block:: yaml
       :caption: Example ETL Pipeline Design

        $ETL$:
            extractors:
                JsonExtractor: {}         # with default file_regex
                JsonExtractor:            # with custom file_regex
                    file_regex: [out.json]
    """

    #def file_regex_default(self):
    #    # by default, all files ending in .json are "extracted"
    #    return [r".*\.json$"]

    def extract(self, path: str, options: Dict) -> List[Dict]:
        # load file as json: if top level element is object -> return one element list
        with open(path, "r") as f:
            data = json.load(f)

        if not isinstance(data, list):
            data = [data]

        return data


class CsvExtractor(Extractor):

    file_regex_default:  ClassVar[List[str]] = [r".*\.csv$"]

    delimiter: str = ","

    has_header: bool = True

    fieldnames: List[str] = None


    r"""The `CsvExtractor` reads result files as CSV.
    The CSV file contains a result per line and by default starts with a header row,
    see ``has_header`` and ``fieldnames`` for CSV files without header.

    :param file_regex: The regex list to match result files, defaults to ``[r".*\.csv$"]``

    :param delimiter: The separator between columns, defaults to ``,``

    :param has_header: Indicates whether the first CSV row is a header, defaults to ``True``

    :param fieldnames: The names of the CSV columns if ``has_header`` is set to `False``, defaults to ``[]``

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

    #def file_regex_default(self):
    #    # by default, all files ending in .json are "extracted"
    #    return [r".*\.csv$"]

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

    file_regex_default:  ClassVar[List[str]] = ["^stderr.log$"]

    r"""The `ErrorExtractor` provides a mechanism to detect potential errors in an experiment job.
    For experiments with a large number of jobs, it is easy to overlook an error
    because there are many output folders and files e.g., the stderr.log of each job.
    The `ErrorExtractor` raises a warning if matching files are not empty.

    :param file_regex: The regex list to match result files, defaults to ``["^stderr.log$"]``

    .. code-block:: yaml
       :caption: Example ETL Pipeline Design

        $ETL$:
            extractors:
                ErrorExtractor: {}         # checking stderr.log
                ErrorExtractor:            # checking custom files
                    file_regex: [stderr.log, error.log]

    """

    #def file_regex_default(self):
    #    # by default, matches the filename `stderr.log`
    #    return ["^stderr.log$"]

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

    file_regex_default:  ClassVar[List[str]] = ["^stdout.log$"]

    r"""The `IgnoreExtractor` provides a mechanism to detect potential errors in an experiment job.
    For experiments with a large number of jobs, it is easy to overlook an error
    indicted by the presence of an unexpected file.
    As a result, the ETL requires that every file in the results folder of the job
    must be matched by exactly one Extractor.
    The `IgnoreExtractor` can be used to ignore certain files on purpose, e.g., stdout.log.

    :param file_regex: The regex list to match result files, defaults to ``["^stdout.log$"]``

    .. code-block:: yaml
       :caption: Example ETL Pipeline Design

        $ETL$:
            extractors:
                IgnoreExtractor: {}        # ignore stdout.log
                IgnoreExtractor:           # custom ignore list
                    file_regex: [stdout.log, other.txt]

    """

    #def file_regex_default(self):
    #    # by default, matches the filename `stdout.log`
    #    return ["^stdout.log$"]

    def extract(self, path: str, options: Dict) -> List[Dict]:
        # ignore this file
        #  -> every file produced by an experiment run needs to be matched to exactly one extractor.
        #       the ignore extractor can be used to ignore some files
        return []


__all__ = [name for name, cl in inspect.getmembers(sys.modules[__name__], inspect.isclass) if name!="Extractor" and issubclass(cl, Extractor) ]
