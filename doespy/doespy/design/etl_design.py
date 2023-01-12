from typing import List
from typing import Dict
from typing import Optional, Any
from typing import Union

from pydantic import Field
from pydantic import BaseModel
from pydantic import root_validator
from pydantic import validator
from pydantic import ValidationError
from pydantic import PydanticValueError


import warnings
import os
import re
import inspect
import sys
import yaml
import jinja2
import json
import enum
import pandas as pd

from doespy import util
from doespy import info
from doespy.etl.etl_base import _load_available_processes



class MyETLBaseModel(BaseModel):
    class Config:
        extra = "forbid"
        smart_union = True
        use_enum_values = True

class ETLContext(MyETLBaseModel):

    prj_id: str
    suite_name: str

    experiment_names: List[str]

    etl_pipeline_names: List[str]

    my_etl_pipeline_name: str = None


class IncludeEtlSource(MyETLBaseModel):
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

    @root_validator(skip_on_failure=True)
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

        #try:
        values["etl_pipeline"] = ETLPipelineBase(**etl_pipeline)
        if "experiments" in values["etl_pipeline"]:
            del values["etl_pipeline"]["experiments"]
            # TODO [nku] not sure this custom error reporting is worth to explore
        #except ValidationError as e:
            #print(e.json())
         #   raise EtlIncludeError(suite=values.get("suite"), template=values.get("template"), pipeline=values.get("pipeline"))
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



avl_extractors, avl_transformers, avl_loaders = _load_available_processes()

extractors = {ext: ext for ext in avl_extractors.keys()}
extractors["INCLUDE_STEPS"] = "$INCLUDE_STEPS$"
ExtractorId = enum.Enum("ExtractorId", extractors)

transformers = {tr: tr for tr in avl_transformers.keys()}
TransformerId = enum.Enum("TransformerId", transformers)

loaders = {ld: ld for ld in avl_loaders.keys()}
loaders["INCLUDE_STEPS"] = "$INCLUDE_STEPS$"
LoaderId = enum.Enum("LoaderId", loaders)



class Extractor(MyETLBaseModel):

    file_regex: Optional[Union[str, List[str]]]

    class Config:
        extra = "allow"
        smart_union = True

    @root_validator(pre=True, skip_on_failure=True)
    def build_extra(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        _build_extra(cls, values)
        return values


class Transformer(MyETLBaseModel):
    pass

class IncludeStepTransformer(Transformer):
    include_steps: IncludeEtlSource = Field(alias="$INCLUDE_STEPS$")

    class Config:
        extra = "forbid"


class NamedTransformer(Transformer):
    name: TransformerId

    class Config:
        extra = "allow"

    @root_validator(pre=True, skip_on_failure=True)
    def build_extra(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        _build_extra(cls, values)
        return values


avl_df_functions = set()
for name, _ in inspect.getmembers(pd.DataFrame, predicate=inspect.isfunction):
    if not name.startswith("_"):
        avl_df_functions.add(f"df.{name}")


class DfTransformer(Transformer):

    class Config:
        extra = "allow"

    @root_validator(skip_on_failure=True)
    def check_df_function(cls, values: Dict[str, Any]) -> Dict[str, Any]:

        for v in values.keys():
            assert v in avl_df_functions, f"{v} is unknown df function"

        return values

class Loader(MyETLBaseModel):
    include_steps: Optional[List[IncludeEtlSource]] = Field(alias="$INCLUDE_STEPS$")

    class Config:
        extra = "allow"

    extra: Dict[str, Any]

    @root_validator(pre=True, skip_on_failure=True)
    def build_extra(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        _build_extra(cls, values)
        return values


class ETLPipelineBase(MyETLBaseModel):

    include_pipeline: Optional[IncludeEtlSource] = Field(alias="$INCLUDE_PIPELINE$", exclude=True)

    extractors: Dict[ExtractorId, Union[Extractor, List[IncludeEtlSource]]] = {}

    transformers: List[Union[IncludeStepTransformer, NamedTransformer, DfTransformer]] = []

    loaders: Dict[LoaderId, Union[Loader, List[IncludeEtlSource]]] = {}

    class Config:
        smart_union = True
        extra = "forbid"

    @root_validator(skip_on_failure=True)
    def inc_pipeline(cls, values):

        if values.get("include_pipeline") is not None:
            for k in ["extractors", "transformers", "loaders"]:
                assert len(values[k]) == 0

            values["extractors"] = values["include_pipeline"].etl_pipeline.extractors
            values["transformers"] = values["include_pipeline"].etl_pipeline.transformers
            values["loaders"] = values["include_pipeline"].etl_pipeline.loaders
            values["include_pipeline"] = None  # mark as complete

        return values

    @root_validator(skip_on_failure=True)
    def inc_extractors(cls, values):
        assert "extractors" in values
        if ExtractorId.INCLUDE_STEPS.value in values['extractors']:
            for include_etl_source in values['extractors'][ExtractorId.INCLUDE_STEPS.value]:
                for k, v in include_etl_source.etl_pipeline.extractors.items():
                    values['extractors'][k] = v
            del values['extractors'][ExtractorId.INCLUDE_STEPS.value]

        return values


    @root_validator(skip_on_failure=True)
    def inc_transformer(cls, values):
        assert "transformers" in values
        steps = []
        for t in values["transformers"]:
            if isinstance(t, IncludeStepTransformer):
                for step in t.include_steps.etl_pipeline.transformers:
                    steps.append(step)
            else:
                steps.append(t)
        values["transformers"] = steps
        return values


    @root_validator(skip_on_failure=True)
    def inc_loader(cls, values):
        assert "loaders" in values
        if LoaderId.INCLUDE_STEPS.value in values['loaders']:
            for include_etl_source in values['loaders'][LoaderId.INCLUDE_STEPS.value]:
                for k, v in include_etl_source.etl_pipeline.loaders.items():
                    values['loaders'][k] = v
            del values['loaders'][LoaderId.INCLUDE_STEPS.value]
        return values


class ExperimentNames(MyETLBaseModel):
    __root__: Union[str, List[str]]

    @validator("__root__")
    def check_exp(cls, v):
        assert v == "*" or isinstance(v, list), f"experiments must be a list of strings or * but is: {v}"
        return v

class ETLPipeline(ETLPipelineBase):

    ctx: ETLContext = Field(alias="_CTX", exclude=True)
    """:meta private:"""

    experiments: ExperimentNames

    etl_vars: Optional[Dict[str, Any]] = Field(alias="$ETL_VARS$")


    class Config:
        smart_union = True
        extra = "forbid"

    @root_validator(skip_on_failure=True)
    def check_experiments(cls, values):
        """Resolves * in experiments and
        ensures that every experiment listed, also exists in the suite
        """

        experiments = values['experiments'].__root__
        avl_experiments = values['ctx'].experiment_names

        if experiments == "*":
            values['experiments'].__root__ = avl_experiments
        else:
            missing = list(set(experiments).difference(avl_experiments))
            assert len(missing) == 0, f"Non-existing experiments: {missing}   (Ctx={values['ctx']})"

        return values


    @root_validator(skip_on_failure=True)
    def resolve_etl_vars(cls, values):
        """The field ``$ETL_VARS$`` allows defining variables that can be used for
        options of extractors, transformers, and loaders.
        Use the ``[% VAR %]`` syntax to refer to those variables.
        """

        def include_etl_vars(base, etl_vars):
            env = util.jinja2_env(
                loader=None,
                undefined=jinja2.StrictUndefined,
                variable_start_string="[%",
                variable_end_string="%]",
            )
            template = json.dumps(base)
            while "[%" in template and "%]" in template:
                template = env.from_string(template)
                template = template.render(**etl_vars)
            return json.loads(template)

        etl_vars = values.pop("etl_vars", None)
        if etl_vars is not None:

            from itertools import chain

            for step in chain(values["extractors"].values(), values["transformers"], values["loaders"].values()):
                if hasattr(step, 'extra') and len(step.extra) > 0:
                    step.extra = include_etl_vars(step.extra, etl_vars)

        return values


    @root_validator(skip_on_failure=True)
    def check_extractors(cls, values):
        """check that each extractor (also included) defines the correct values"""
        assert "extractors" in values
        d = {}
        for name_enum, extractor in values["extractors"].items():
            if isinstance(extractor, Extractor):
                ext = avl_extractors[name_enum](**extractor.extra)
                d[name_enum] = ext
            else:
                d[name_enum] = extractor
        values["extractors"] = d

        return values

    @root_validator(skip_on_failure=True)
    def check_transformers(cls, values):
        """check that each transformer (also included) defines the correct values"""
        assert "transformers" in values
        steps = []
        for t in values["transformers"]:
            assert not isinstance(t, IncludeStepTransformer)

            if isinstance(t, NamedTransformer) and t.name is not None:
                trans = avl_transformers[t.name](**t.extra)
                steps.append(trans)
            else:
                steps.append(t)
        values["transformers"] = steps
        return values

    @root_validator(skip_on_failure=True)
    def check_loaders(cls, values):
        """check that each loader (also included) defines the correct values"""
        assert "loaders" in values

        d = {}
        for name_enum, loader in values["loaders"].items():
            if isinstance(loader, Loader):
                ext = avl_loaders[name_enum](**loader.extra)
                d[name_enum] = ext
            else:
                d[name_enum] = loader
        values["loaders"] = d
        return values



SuiteName = enum.Enum("SuiteName", {s.replace("-", "_"): s for s in info.get_suite_designs()})
"""Name of the available experiment suites in `doe-suite-config/designs`."""


class SuperETLContext(MyETLBaseModel):

    class SuperETLSuiteContext(MyETLBaseModel):

        experiment_names: List[str]

        etl_pipeline_names: List[str]


    prj_id: str
    suites: Dict[SuiteName, SuperETLSuiteContext]

    my_etl_pipeline_name: str = None


class SuperETLPipeline(ETLPipeline):

    ctx: SuperETLContext = Field(alias="_CTX", exclude=True)
    """:meta private:"""

    experiments: Dict[SuiteName, ExperimentNames]

    # etl_vars: Note -> inherited from ETLPipeline


    @root_validator(skip_on_failure=True)
    def check_experiments(cls, values):
        """Resolves * in experiments and
        #ensures that every experiment listed, also exists in the suite
        """

        for suite_name, experiments in values.get("experiments", {}).items():

            experiments = experiments.__root__

            # TODO [nku] this may need to be debugged first
            avl_experiments = values['ctx'].suites[suite_name].experiment_names

            if experiments.__root__ == "*":
                # TODO [nku] need to test that the proper things are set
                experiments.__root__ = avl_experiments
            else:
                missing = list(set(experiments.__root__).difference(avl_experiments))
                assert len(missing) == 0, f"Non-existing experiments: {missing}   (Ctx={values['ctx']})"

        return values

# TODO [nku] the super ETL things are untested

class SuperETL(MyETLBaseModel):

    ctx: SuperETLContext = Field(alias="_CTX", exclude=True)
    """:meta private:"""

    suite_id: Dict[SuiteName, Union[List[str], str]] = Field(alias="$SUITE_ID$")

    etl: Dict[str, SuperETLPipeline] = Field(alias="$ETL$")


    @root_validator(pre=True, skip_on_failure=True)
    def context(cls, values):

        suites = {}
        for suite in info.get_suite_designs():
            suites[suite] = {
                "experiment_names": [d["exp_name"] for d in info.get_experiments(suite)],
                "etl_pipeline_names": info.get_etl_pipelines(suite)
            }

        ctx = {
            "prj_id": util.get_project_id(),
            "suites": suites
        }

        values["_CTX"] = ctx

        # ETLContext
        for etl_name, etl_pipeline in values.get("$ETL$", {}).items():
            etl_ctx = ctx.copy()
            etl_ctx["my_etl_pipeline_name"] = etl_name
            etl_pipeline["_CTX"] = etl_ctx

        return values

    @validator("suite_id")
    def check_suite_id(cls, v):
        """Check that all suite id's that the super etl references also actually exist as results.
        """

        # build info on avl suite ids
        existing_suite_ids = {}
        for d in util.get_all_suite_results_dir():
            if d['suite'] not in existing_suite_ids:
                existing_suite_ids[d['suite']] = set()

            existing_suite_ids[d['suite']].add(d['suite_id'])


        for suite_name, suite_id_entry in v.items():
            assert suite_name in existing_suite_ids, f"no results for suite={suite_name} exist"

            if isinstance(suite_id_entry, str):
                suite_id_entry = [suite_id_entry]

            for suite_id in suite_id_entry:
                assert suite_id in existing_suite_ids[suite_name], f"suite_id={suite_id} for suite={suite_name} does not exist"

        return v
