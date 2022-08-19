
from typing import List
from typing import Dict
from typing import Optional, Any
#rom doespy.etl.steps.extractors import JsonExtractor, YamlExtractor, ErrorExtractor, IgnoreExtractor, CsvExtractor
#from doespy.etl.steps.loaders import CsvSummaryLoader, LatexTableLoader
from pydantic import Field
from typing import Union
from pydantic import BaseModel
from pydantic import root_validator
from pydantic import validator

from pydantic import PrivateAttr


import inspect
import sys


from doespy import util
from doespy import info


class IncludeEtlSource(BaseModel):
    suite: str = None
    template: str = None
    pipeline: str = None

    @validator("suite", "template")
    def check_suite_xor_template(cls, v, values):
        """checks that either suite or template is used"""
        if "suite" in values:
            count = 0
            if values["suite"] is None:
                count += 1
            if v is None:  # template
                count += 1

            if count != 1:
                raise ValueError(f"IncludeSource needs to have either suite or template (suite={values['suite']} xor template={v})")

        return v

    @validator("suite")
    def check_suite_available(cls, v):
        """checks that referenced suite exists"""
        if v is not None:
            avl_suites = info.get_suite_designs()
            if v not in avl_suites:
                raise ValueError(f"source not found: suite={v}")

        return v

    @validator("template")
    def check_template_available(cls, v):
        """checks that referenced etl template exists"""
        if v is not None:
            designs_dir = util.get_suite_design_etl_template_dir()
            avl_suites = info.get_suite_designs(designs_dir=designs_dir)
            if v not in avl_suites:
                raise ValueError(f"source not found: suite={v}")

        return v

    @validator("pipeline")
    def check_pipeline_available(cls, v, values):
        """checks that referenced pipeline in suite or template exists"""
        if values["suite"] is not None:
            avl_pipelines = info.get_etl_pipelines(values["suite"])
        elif values["template"] is not None:
            dir = util.get_suite_design_etl_template_dir()
            avl_pipelines = info.get_etl_pipelines(values["template"], designs_dir=dir)
        else:
            raise ValueError()

        if v not in avl_pipelines:
            raise ValueError(f"source not found: suite={values['suite']}  template={values['template']}  pipeline={v}")

        return v

    @root_validator
    def include_etl_pipeline(cls, values: Dict[str, Any]) -> Dict[str, Any]:

        if values["suite"] is not None:
            design = util.get_suite_design(values["suite"])
        elif values["template"] is not None:
            templ_dir = util.get_suite_design_etl_template_dir()
            design = util.get_suite_design(suite=values["template"], folder=templ_dir)

        values['etl_pipeline'] = design["$ETL$"][values["pipeline"]]

        if "experiments" in values['etl_pipeline']:
            del values['etl_pipeline']["experiments"]

        return values


def _build_extra(cls, values: Dict[str, Any]):
    all_required_field_names = {field.alias for field in cls.__fields__.values() if field.alias != 'extra'}  # to support alias

    extra: Dict[str, Any] = {}
    for field_name in list(values):
        if field_name not in all_required_field_names:
            extra[field_name] = values.pop(field_name)
    values['extra'] = extra
    return values





class Extractor(BaseModel):


    file_regex: Optional[Union[str, List[str]]]

    #include_steps: Optional[List[IncludeEtlSource]] = Field(alias="$INCLUDE_STEPS$")

    class Config:
        extra = "allow"
        smart_union = True

    @root_validator(pre=True)
    def build_extra(cls, values: Dict[str, Any]) -> Dict[str, Any]:

        _build_extra(cls, values)
        return values



class Transformer(BaseModel):
    # TODO does not deal with df.x syntax
    name: Optional[str] = None

    # TODO [nku] add validation that it's present with name, and df. syntax
    include_steps: Optional[IncludeEtlSource] = Field(alias="$INCLUDE_STEPS$")

    class Config:
        extra = "allow"

    @root_validator(pre=True)
    def build_extra(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        _build_extra(cls, values)
        return values

    @root_validator
    def check_transformers(cls, values):

        # TODO [nku] check named transformers
        #if values["name"] is not None:
        #    avl_transformers[values["name"]](**values["extra"])

        # TODO [nku] check the df.X syntax

        # TODO [nku] would be great to resolve the include syntax

        return values


class Loader(BaseModel):
    include_steps: Optional[List[IncludeEtlSource]] = Field(alias="$INCLUDE_STEPS$")

    class Config:
        extra = "allow"

    extra: Dict[str, Any]

    @root_validator(pre=True)
    def build_extra(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        _build_extra(cls, values)
        return values


from doespy.etl.etl_base import _load_available_processes
avl_extractors, avl_transformers, avl_loaders  = _load_available_processes()


#class Extractors(BaseModel):
#
#    include_steps: Optional[List[IncludeEtlSource]] = Field(alias="$INCLUDE_STEPS$")
#
#
#
#    class Config:
#        extra = "allow"
#

import enum

# TODO [nku] would build this dynamically based on available extractors
ExtractorId = enum.Enum('ExtractorId', {'INCLUDE_STEPS': '$INCLUDE_STEPS$',
                                        'YamlExtractor': 'YamlExtractor',
                                        'JsonExtractor': 'JsonExtractor',
                                        "CsvExtractor": "CsvExtractor",
                                        "ErrorExtractor": "ErrorExtractor",
                                        "IgnoreExtractor": "IgnoreExtractor"})

ExtractorId.YamlExtractor.__doc__ = "hello"


class ETLPipeline(BaseModel):
    experiments: Union[str, List[str]]

    include_pipeline: Optional[IncludeEtlSource] = Field(alias="$INCLUDE_PIPELINE$")

    #extractors_include_steps: Optional[List[IncludeEtlSource]] = []
    extractors: Dict[ExtractorId, Union[Extractor, List[IncludeEtlSource]]] = {}


    #extractors: Dict[str, construct_union([ErrorExtractor, IgnoreExtractor, CsvExtractor, YamlExtractor, JsonExtractor])] = {}

    transformers: List[Transformer] = []
    #loaders: Dict[str, Loader] = {}

    loaders: Dict[str, Loader] = {}

    class Config:
        smart_union = True

    #@root_validator(pre=True)
    #def build_extra(cls, values: Dict[str, Any]) -> Dict[str, Any]:
    #    print(f"preeeee={values}")
    #    for k in ["extractors"]: #, "loaders"
    #        if k in values and "$INCLUDE_STEPS$" in values[k]:
    #            values[k]["$INCLUDE_STEPS$"] = {"$INCLUDE_STEPS$": values[k]["$INCLUDE_STEPS$"]}
    #            #values["extractors_include_steps"] = values[k].pop("$INCLUDE_STEPS$")
#
    #    return values
#
    @validator("experiments")
    def check_experiments(cls, v):
        if v == "*" or isinstance(v, list):
            return v
        raise ValueError(f"experiments must be a list of strings or * but is: {v}")

    @root_validator
    def inc_extractors(cls, values):
        print(f"v???? \nvalues={values}")

        if values["include_pipeline"] is not None:
            pass # TODO [nku] would do the replacement
            #values["extractors"] = values["include_pipeline"].etl_pipeline["extractors"]

        if "extractors" in values and "$INCLUDE_STEPS$" in values["extractors"]:
            # TODO [nku] there is something wrong with extra functionality on Extractor -> the idea here would be to include the extractors loaded externally
            print(f"FOUND INCLUDE STEPS   {values['extractors']['$INCLUDE_STEPS$']}")

        print(f"\n\n")
        return values

    @root_validator
    def check_extractors(cls, values):
        print(f"check extractors")
        assert "extractors" in values

        return values # TODO fix

        for name, extractor in values["extractors"].items():

            if name == "$INCLUDE_STEPS$": # after inc_extractor the idea is that this is not present anymore
                continue  # TODO [nku] would be nice if Extractor could resolve include steps by itself

            avl_extractors[name](**extractor.extra)

        return values

    @root_validator
    def inc_transformer(cls, values):
        # TODO [nku] include functionality (slighlty different than for loader extractor)
        return values

    @root_validator
    def inc_loader(cls, values):
        # TODO [nku] same functionality as for extractors
        return values

    @root_validator
    def check_loaders(cls, values):
        for name, loader in values["loaders"].items():

            if name == "$INCLUDE_STEPS$": # after inc_loader the idea is that this is not present anymore
                continue  # TODO [nku] would be nice if Loader could resolve include steps by itself


            avl_loaders[name](**loader.extra)

        return values




class HostType(BaseModel):
    n: int = 1
    check_status: bool = True
    init_roles: Union[str, List[str]] = []
    cmd: Union[str, List[str], List[Dict[str, str]]] = Field(alias="$CMD$")

    class Config:
        extra = "forbid"


class BaseExperiment(BaseModel):

    include_vars: Optional[Union[str, List[str]]] = Field(alias="$INCLUDE_VARS$")

    class Config:
        extra = "allow"

    @validator("*")
    def check_factor_syntax(cls, v):
        return v
        #pass
        # TODO [nku] if $FACTOR$ is key -> then value must be a list


class Experiment(BaseModel):
    n_repetitions: int = 1
    """number of repetitions"""

    common_roles: Union[str, List[str]] = []
    """ansible roles executed during the setup of all host types"""

    host_types: Dict[str, HostType]
    """host types"""

    base_experiment: BaseExperiment
    """experiment run configuration"""

    factor_levels: List[Dict] = []
    """list of factors"""

    class Config:
        extra = "forbid"

    @root_validator
    def check_factor_levels(cls, values):
        base_experiment, factor_levels = values.get('base_experiment'), values.get('factor_levels')
        #if pw1 is not None and pw2 is not None and pw1 != pw2:
        #    raise ValueError('passwords do not match')

        # TODO: extract factors from base_experiment

        # TODO: check that factor_levels is of this format

        return values

    @validator("common_roles")
    def check_common_roles(cls, v):

        if isinstance(v, str):
            v = [v]

        roles = util.get_setup_roles()
        unknown_roles = [role for role in v if role not in roles]

        if len(unknown_roles) > 0:
            raise ValueError(f"roles not found: {unknown_roles}")

    @validator("host_types")
    def check_host_types(cls, v):

        avl_host_types = util.get_host_types()
        unknown_host_types = [ht for ht in v.keys() if ht not in avl_host_types]

        if len(unknown_host_types) > 0:
            raise ValueError(f"host types not found: {unknown_host_types}")


class SuiteDesign(BaseModel):
    suite_vars: BaseExperiment = Field(alias="$SUITE_VARS$", default={})
    experiment_designs: Dict[str, Experiment]
    etl: Dict[str, ETLPipeline] = Field(alias="$ETL$", default={})

    class Config:
        extra = "forbid"

    @validator("experiment_designs")
    def check_exp_names(cls, v):
        # TODO [nku] check min length and forbidden keywords

        return v

    @root_validator
    def check_experiments(cls, values):
        """Checks that ETL Pipelines only reference existing experiments and replaces "*" with all experiments.
        """

        avl_experiments = set(values["experiment_designs"].keys())

        print(f"vals={values}")

        if "etl" not in values:
            raise ValueError("failure in etl")

        for pipeline_name, config in values["etl"].items():

            if config.experiments == "*":
                config.experiments = list(avl_experiments)
            else:
                missing = list(set(config.experiments).difference(avl_experiments))

                if len(missing) > 0:
                    raise ValueError(f"pipeline={pipeline_name} references non-existing experiments: {missing}")

        return values

class Suite(BaseModel):

    suite_vars: BaseExperiment = Field(alias="$SUITE_VARS$", default={})

    exp1: Experiment
    """A suite needs to contain at least one experiment."""

    exp2: Optional[Experiment]
    """Further experiments are optional."""

    etl: Dict[str, ETLPipeline] = Field(alias="$ETL$", default={})
    """ETL Pipeline to process the result files."""

def check_suite(suite):

    print(f"Checking Suite  {suite}")

    suite = util.get_suite_design(suite=suite)
    suite_design = {"experiment_designs": {}}

    for exp_name, design in suite.items():
        if exp_name not in ["$ETL$", "$SUITE_VARS$"]:
            suite_design["experiment_designs"][exp_name] = design

        elif exp_name == "$ETL$":
            suite_design["$ETL$"] = design

        elif exp_name == "$SUITE_VARS$":
            suite_design["$SUITE_VARS$"] = design

    _model = SuiteDesign(**suite_design)

    #print(_model.etl)


def get_keywords():
    keywords = set()
    for name, cl in inspect.getmembers(sys.modules[__name__], inspect.isclass):
        if issubclass(cl, BaseModel):
            for k in cl.__fields__.keys():
                keywords.add(k)
    return keywords


if __name__ == "__main__":

    #check_suite(suite="example01-minimal")
    #check_suite(suite="example02-single")
    #check_suite(suite="example03-format")
    #check_suite(suite="example04-multi")
    #check_suite(suite="example05-complex")
    #check_suite(suite="example06-vars")
    check_suite(suite="example07-etl")


    #model = Experiment(**exp)
