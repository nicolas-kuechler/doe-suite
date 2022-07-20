from abc import ABC, abstractmethod
from typing import List, Dict

import warnings, yaml, json, csv
from dataclasses import dataclass, field


@dataclass
class Extractor(ABC):

    file_regex: List[str] = field(default=None)

    @property
    def regex(self):
        if self.file_regex:
            return self.file_regex
        else:
            return self.file_regex_default()

    @property
    @abstractmethod
    def file_regex_default(self):
        pass

    @abstractmethod
    def extract(self, path: str, options: Dict) -> List[Dict]:
        pass

# TODO [nku] add docstrings


class YamlExtractor(Extractor):

    def file_regex_default(self):
        return ['.*\.yaml$', '.*\.yml$']

    def extract(self, path: str, options: Dict) -> List[Dict]:
       with open(path, 'r') as f:
           data = yaml.load(f, yaml.SafeLoader)
       if not isinstance(data, list):
           data = [data]
       return data

class JsonExtractor(Extractor):

    def file_regex_default(self):
        return ['.*\.json$']

    def extract(self, path: str, options: Dict) -> List[Dict]:
        with open(path, 'r') as f:
            data = json.load(f)

        if not isinstance(data, list):
            data = [data]

        return data

class CsvExtractor(Extractor):

    def file_regex_default(self):
        return ['.*\.csv$']

    def extract(self, path: str, options: Dict) -> List[Dict]:
        data = []

        delimiter = options.get("delimiter", ",")
        has_header = options.get("has_header", True)
        fieldnames = options.get("fieldnames", None)

        with open(path, 'r') as f:

            if has_header or fieldnames is not None:
                reader = csv.DictReader(f, delimiter=delimiter, fieldnames=fieldnames)
            else:
                reader = csv.reader(f, delimiter=delimiter)
            for row in reader:
                data.append(row)

        return data


class ErrorExtractor(Extractor):

    def file_regex_default(self):
        return ['^stderr.log$']

    # if the file is present and not empty, then throws a warning
    def extract(self, path: str, options: Dict) -> List[Dict]:
        with open(path, 'r') as f:
            content = f.read().replace('\n', ' ')

        if content.strip() and not content.strip().isspace(): # ignore empty error files
            warnings.warn(f"found error file: {path}")
            warnings.warn(f"   {content}")
        return []


class IgnoreExtractor(Extractor):

    def file_regex_default(self):
        return ['^stdout.log$']

    # ignores a file
    def extract(self, path: str, options: Dict) -> List[Dict]:
        # ignore this file
        return []
