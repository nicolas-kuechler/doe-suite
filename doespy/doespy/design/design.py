from typing import List
from typing import Dict
from typing import Optional, Any

from pydantic import Field
from typing import Union
from pydantic import BaseModel
from pydantic import root_validator
from pydantic import validator
from pydantic import ValidationError
from pydantic import PydanticValueError




import re
import inspect
import sys

from doespy import util
from doespy import info

# TODO [nku] shoudl never access values["abc"] in root_validator because if abc failed -> will not be there

class MyBaseModel(BaseModel):
    class Config:
        extra = "forbid"
        smart_union = True
        #use_enum_values = True TODO [nku] could think about this

class IncludeEtlSource(MyBaseModel):
    suite: str = None
    template: str = None
    pipeline: str = None

    class Config:
        extra = "forbid"
        allow_reuse=True

    @validator("suite", "template")
    def check_suite_xor_template(cls, v, values):
        """checks that either suite or template is used"""
        if "suite" in values:
            count = 0
            if values.get("suite") is None:
                count += 1
            if v is None:  # template
                count += 1

            if count != 1:
                raise ValueError(
                    f"IncludeSource needs to have either suite or template (suite={values.get('suite')} xor template={v})"
                )

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

        if values.get("suite") is not None:
            avl_pipelines = info.get_etl_pipelines(values["suite"])
        elif values.get("template") is not None:
            dir = util.get_suite_design_etl_template_dir()
            avl_pipelines = info.get_etl_pipelines(values["template"], designs_dir=dir)
        else:
            raise ValueError()

        if v not in avl_pipelines:
            raise ValueError(
                f"source not found: suite={values['suite']}  template={values['template']}  pipeline={v}"
            )

        return v

    @root_validator
    def include_etl_pipeline(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """loads the external etl source (and checks that the name of extractor, transformer, and loader are ok)"""

        if values.get("suite") is not None:
            design = util.get_suite_design(values["suite"])
        elif values.get("template") is not None:
            templ_dir = util.get_suite_design_etl_template_dir()
            design = util.get_suite_design(suite=values["template"], folder=templ_dir)

        assert "pipeline" in values, "include etl pipeline requires pipeline field"
        etl_pipeline = design["$ETL$"][values["pipeline"]]
        if "experiments" in etl_pipeline:
            del etl_pipeline["experiments"]

        try:
            values["etl_pipeline"] = ETLPipelineBase(**etl_pipeline)
            if "experiments" in values["etl_pipeline"]:
                del values["etl_pipeline"]["experiments"]
            # TODO [nku] not sure this custom error reporting is worth to explore
        except ValidationError as e:
            print(e.json())
            raise EtlIncludeError(suite=values.get("suite"), template=values.get("template"), pipeline=values.get("pipeline"))

        return values


class EtlIncludeError(PydanticValueError):
    code = 'etl_include'
    msg_template = 'failed to include etl pipeline (suite={suite} template={template} pipeline={pipeline})'

def _build_extra(cls, values: Dict[str, Any]):
    all_required_field_names = {
        field.alias for field in cls.__fields__.values() if field.alias != "extra"
    }  # to support alias

    extra: Dict[str, Any] = {}
    for field_name in list(values):
        if field_name not in all_required_field_names:
            extra[field_name] = values.pop(field_name)
    values["extra"] = extra
    return values


from doespy.etl.etl_base import _load_available_processes

avl_extractors, avl_transformers, avl_loaders = _load_available_processes()


import enum

extractors = {ext: ext for ext in avl_extractors.keys()}
extractors["INCLUDE_STEPS"] = "$INCLUDE_STEPS$"
ExtractorId = enum.Enum("ExtractorId", extractors)

transformers = {tr: tr for tr in avl_transformers.keys()}
TransformerId = enum.Enum("TransformerId", transformers)

loaders = {ld: ld for ld in avl_loaders.keys()}
loaders["INCLUDE_STEPS"] = "$INCLUDE_STEPS$"
LoaderId = enum.Enum("LoaderId", loaders)



#print(f"loaders={loaders}   avl_loaders={avl_loaders}")

#raise ValueError("blockers")

HostTypeId = enum.Enum("HostTypeId", {ht.replace("-", "_"): ht for ht in util.get_host_types()})
"""Name of a host type and corresponds to folder in `doe-suite-config/group_vars`."""

SetupRoleId = enum.Enum("SetupRoleId", {x.replace("-", "_"):  x for x in util.get_setup_roles()})
"""Name of an Ansible role to setup a host. The role is located in folder: `doe-suite-config/roles`."""

class Extractor(MyBaseModel):

    file_regex: Optional[Union[str, List[str]]]

    class Config:
        extra = "allow"
        smart_union = True

    @root_validator(pre=True)
    def build_extra(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        _build_extra(cls, values)
        return values


class Transformer(MyBaseModel):
    # TODO does not deal with df.x syntax
    name: Optional[TransformerId] = None

    # TODO [nku] add validation that it's present with name, and df. syntax
    include_steps: Optional[IncludeEtlSource] = Field(alias="$INCLUDE_STEPS$")

    class Config:
        extra = "allow"

    @root_validator(pre=True)
    def build_extra(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        _build_extra(cls, values)
        return values


class Loader(MyBaseModel):
    include_steps: Optional[List[IncludeEtlSource]] = Field(alias="$INCLUDE_STEPS$")

    class Config:
        extra = "allow"

    extra: Dict[str, Any]

    @root_validator(pre=True)
    def build_extra(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        _build_extra(cls, values)
        return values


class ETLPipelineBase(MyBaseModel):

    include_pipeline: Optional[IncludeEtlSource] = Field(alias="$INCLUDE_PIPELINE$")

    extractors: Dict[ExtractorId, Union[Extractor, List[IncludeEtlSource]]] = {}

    transformers: List[Transformer] = []

    loaders: Dict[LoaderId, Union[Loader, List[IncludeEtlSource]]] = {}

    class Config:
        smart_union = True
        extra = "forbid"

    @root_validator
    def inc_pipeline(cls, values):

        if values.get("include_pipeline") is not None:
            for k in ["extractors", "transformers", "loaders"]:
                assert len(values[k]) == 0

            values["extractors"] = values["include_pipeline"].etl_pipeline.extractors
            values["transformers"] = values["include_pipeline"].etl_pipeline.transformers
            values["loaders"] = values["include_pipeline"].etl_pipeline.loaders
            values["include_pipeline"] = None  # mark as complete

        return values

    @root_validator
    def inc_extractors(cls, values):
        assert "extractors" in values
        if ExtractorId.INCLUDE_STEPS in values['extractors']:
            for include_etl_source in values['extractors'][ExtractorId.INCLUDE_STEPS]:
                for k, v in include_etl_source.etl_pipeline.extractors.items():
                    values['extractors'][k] = v
            del values['extractors'][ExtractorId.INCLUDE_STEPS]

        return values

    @root_validator
    def check_extractors(cls, values):
        """check that each extractor (also included) defines the correct values"""
        assert "extractors" in values
        d = {}
        for name_enum, extractor in values["extractors"].items():
            if isinstance(extractor, Extractor):
                ext = avl_extractors[name_enum.value](**extractor.extra)
                d[name_enum] = ext
            else:
                d[name_enum] = extractor
        values["extractors"] = d
        return values

    @root_validator
    def inc_transformer(cls, values):
        assert "transformers" in values
        steps = []
        for t in values["transformers"]:
            # TODO [nku] could also deal with df. syntax here?
            if t.include_steps is not None:
                for step in t.include_steps.etl_pipeline.transformers:
                    steps.append(step)
            else:
                steps.append(t)
        values["transformers"] = steps
        return values

    @root_validator
    def check_transformers(cls, values):
        """check that each transformer (also included) defines the correct values"""
        assert "transformers" in values
        steps = []
        for t in values["transformers"]:
            assert t.include_steps is None
            # TODO [nku] could also deal with df. syntax here?
            if isinstance(t, Transformer) and t.name is not None:
                trans = avl_transformers[t.name.value](**t.extra)
                steps.append(trans)
            else:
                steps.append(t)
        values["transformers"] = steps
        return values

    @root_validator
    def inc_loader(cls, values):
        assert "loaders" in values
        if LoaderId.INCLUDE_STEPS in values['loaders']:
            for include_etl_source in values['loaders'][LoaderId.INCLUDE_STEPS]:
                for k, v in include_etl_source.etl_pipeline.loaders.items():
                    values['loaders'][k] = v
            del values['loaders'][LoaderId.INCLUDE_STEPS]
        return values

    @root_validator
    def check_loaders(cls, values):
        """check that each loader (also included) defines the correct values"""
        assert "loaders" in values
        d = {}
        for name_enum, loader in values["loaders"].items():
            if isinstance(loader, Loader):
                ext = avl_loaders[name_enum.value](**loader.extra)
                d[name_enum] = ext
            else:
                d[name_enum] = loader
        values["loaders"] = d
        return values


class ETLPipeline(ETLPipelineBase):
    experiments: Union[str, List[str]]

    # TODO [nku] do we need to check something with them?
    etl_vars: Optional[Dict[str, Any]] = Field(alias="$ETL_VARS$")

    class Config:
        smart_union = True
        extra = "forbid"


    @validator("experiments")
    def check_experiments(cls, v):
        if v == "*" or isinstance(v, list):
            return v
        raise ValueError(f"experiments must be a list of strings or * but is: {v}")


class HostType(MyBaseModel):
    n: int = 1
    check_status: bool = True
    init_roles: Union[SetupRoleId, List[SetupRoleId]] = []
    cmd: Union[str, List[str], List[Dict[str, str]]] = Field(alias="$CMD$")

    class Config:
        extra = "forbid"


class BaseExperiment(MyBaseModel):

    """Dictionary with basic experiment config.
    """

    include_vars: Optional[Union[str, List[str]]] = Field(alias="$INCLUDE_VARS$")

    # TODO [nku] Can we define custom schemas for project and then enforce
    # that they must be present in a certain form across all suites/experiments?
    # (maybe should always be marked as optional but if present, than in that form)

    class Config:
        extra = "allow"

    @validator("*")
    def check_factor_syntax(cls, v):
        return v
        # pass
        # TODO [nku] if $FACTOR$ is key -> then value must be a list



class Experiment(MyBaseModel):
    """An experiment is composed of a set of runs, each with its own unique configuration.
    The configurations of the runs vary different experiment factors, e.g., number of clients.
    Additionally, an experiment also specifies the hosts responsible for executing the runs.
    """

    n_repetitions: int = 1
    """Number of repetitions with the same experiment run configuration."""

    common_roles: Union[SetupRoleId, List[SetupRoleId]] = []
    """Ansible roles executed during the setup of all host types."""

    host_types: Dict[HostTypeId, HostType]
    """The different :ref`host types<Host Type>` involved in the experiment."""

    base_experiment: BaseExperiment
    """Defines constants and factors of an experiment."""

    factor_levels: List[Dict] = []
    """For the factors of an experiment, lists the different levels.
    For example, `n_clients` can be a factor with two levels: 1 and 100."""

    inherited_suite_vars: BaseExperiment = Field(None, alias="$INHERITED_SUITE_VARS$", hidden=True)

    # TODO [nku] for variable inheritance: introduce $BLOCKER$ that stops the include vars from going deeper and instead do a replacement. or $INCLUDE_REPLACE$

    class Config:
        extra = "forbid"

    @root_validator
    def check_factor_levels(cls, values):
        base_experiment, factor_levels = values.get("base_experiment"), values.get(
            "factor_levels"
        )
        # if pw1 is not None and pw2 is not None and pw1 != pw2:
        #    raise ValueError('passwords do not match')

        # TODO: extract factors from base_experiment

        # TODO: check that factor_levels is of this format

        return values

# TODO [nku] could also extract some of them automatically from pydantic models?
RESERVED_KEYWORDS = ["state", "$FACTOR$", "is_controller_yes", "is_controller_no", "check_status_yes", "check_status_no", "localhost", "n_repetitions", "common_roles", "host_types", "base_experiment", "factor_levels", "n", "init_roles", "check_status", "$CMD$"]

class SuiteDesign(MyBaseModel):
    suite_vars: BaseExperiment = Field(alias="$SUITE_VARS$", default={})
    experiment_designs: Dict[str, Experiment]
    etl: Dict[str, ETLPipeline] = Field(alias="$ETL$", default={})

    class Config:
        extra = "forbid"

    @root_validator(pre=True)
    def distribute_suite_vars(cls, values):

        # set the suite vars as a field in all experiment designs
        suite_vars = values.get("$SUITE_VARS$")

        for _, exp in values.get("experiment_designs").items():
            exp["$INHERITED_SUITE_VARS$"] = suite_vars
        return values

    @validator("experiment_designs", pre=True)
    def demo(cls, v, values):
        print(f"\n\ndemo v={v} \n\n\nvalues={values}")
        return v

    @validator("experiment_designs")
    def check_exp_names(cls, v):
        # TODO [nku] check min length and forbidden keywords
        for exp_name in v.keys():
             assert exp_name not in RESERVED_KEYWORDS, f'experiment name: "{exp_name}" is not allowed (reserved keyword)'

             assert len(exp_name) <= 200, f'experiment name: "{exp_name}" is not allowed (too long, limit=200)'

             assert re.match(r"^[A-Za-z0-9_]+$", exp_name), f'experiment name: "{exp_name}" is not allowed (must consist of alphanumeric chars or _)'
        return v

    @root_validator
    def check_experiments(cls, values):
        """Checks that ETL Pipelines only reference existing experiments and replaces "*" with all experiments."""
        assert "experiment_designs" in values

        avl_experiments = set(values["experiment_designs"].keys())

        if "etl" not in values:
            raise ValueError("failure in etl")

        for pipeline_name, config in values["etl"].items():

            if config.experiments == "*":
                config.experiments = list(avl_experiments)
            else:
                missing = list(set(config.experiments).difference(avl_experiments))

                if len(missing) > 0:
                    raise ValueError(
                        f"pipeline={pipeline_name} references non-existing experiments: {missing}"
                    )

        return values


class Suite(MyBaseModel):

    """
    A suite is a collection of experiments, denoted as `<EXP1>`, `<EXP2>`, etc.
    Each experiment has its own set of config variables.
    It is also possible to define variables that are shared by
    all experiments in the suite, referred to as `SUITE_VARS`.
    In addition to the experiments, a suite can also define an
    `ETL` (extract, transform, load) pipeline,
    which outlines the steps for processing the resulting files.
    """

    suite_vars: BaseExperiment = Field(alias="$SUITE_VARS$", default={})
    """Shared variables belonging to every experiment of the suite."""

    # TODO [nku] add a link

    exp1: Experiment = Field(alias="<EXP1>")
    """A suite needs to contain at least one :ref:`experiment<Experiment>`.
    Choose a descriptive experiment name for the placeholder `<EXP1>`."""

    exp2: Optional[Experiment] = Field(alias="<EXP2>")
    """Further :ref:`experiments<Experiment>` are optional.
    Choose a descriptive experiment name for the placeholder `<EXP2>`, `<EXP3>`, etc."""

    etl: Dict[str, ETLPipeline] = Field(alias="$ETL$", default={})
    """:ref:`ETL Pipeline` to process the result files."""


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

    # print(_model.etl)


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
    check_suite(suite="example06-vars")
    #check_suite(suite="example07-etl") TODO [nku] at the moment this does not work yet

    # model = Experiment(**exp)