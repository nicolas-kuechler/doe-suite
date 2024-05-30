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
    config: str = None # super etl config
    template: str = None
    pipeline: str = None

    class Config:
        extra = "forbid"
        allow_reuse=True



    @validator("suite")
    def check_suite_available(cls, v):
        """checks that referenced suite exists"""
        if v is not None:
            avl_suites = info.get_suite_designs()
            if v not in avl_suites:
                raise ValueError(f"source not found: suite={v}")

        return v

    @validator("config")
    def check_config_available(cls, v, values):
        """checks that referenced config exists"""
        if v is not None:

            avl_configs = util.get_all_super_etl_configs()
            #avl_suites = info.get_suite_designs()
            if v not in avl_configs:
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
    def check_suite_xor_template(cls, v, values):

        """checks that either suite or template or config is used"""

        count = 0

        if values.get("suite", None) is not None:
            count += 1

        if values.get("config", None) is not None:
            count += 1

        if values.get("template", None) is not None:
            count += 1

        assert count == 1, f"IncludeSource malformed: suite, config, and template are mutually exclusive but are: suite={values.get('suite')}  config={values.get('config')}  template={values.get('template')}"

        return v


    @validator("pipeline")
    def check_pipeline_available(cls, v, values):
        """checks that referenced pipeline in suite or template exists"""

        if values.get("suite") is not None:
            avl_pipelines = info.get_etl_pipelines(values["suite"])
        elif values.get("config") is not None:
            dir = util.get_super_etl_dir()
            avl_pipelines = info.get_etl_pipelines(values["config"], designs_dir=dir)
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

        elif values.get("config") is not None:
            dir = util.get_super_etl_dir()
            design = util.get_suite_design(suite=values["config"], folder=dir)

        elif values.get("template") is not None:
            templ_dir = util.get_suite_design_etl_template_dir()
            design = util.get_suite_design(suite=values["template"], folder=templ_dir)

        assert "pipeline" in values, "include etl pipeline requires pipeline field"
        etl_pipeline = design["$ETL$"][values["pipeline"]]
        if "experiments" in etl_pipeline:
            del etl_pipeline["experiments"]

        values["etl_pipeline"] = ETLPipelineBase(**etl_pipeline)
        if "experiments" in values["etl_pipeline"]:
            del values["etl_pipeline"]["experiments"]
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

    extractors: Dict[ExtractorId, Union[List[IncludeEtlSource], Extractor]] = {}

    transformers: List[Union[IncludeStepTransformer, NamedTransformer, DfTransformer]] = []

    # TODO [nku] loaders should also be possible to be a list because may want to use same loader id multiple times
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

    ctx: ETLContext = Field(alias="_CTX", exclude=True, )
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
                args = extractor.dict()
                if "extra" in args:
                    del args["extra"]

                if "file_regex" in args and args["file_regex"] is None:
                    del args["file_regex"]

                args = {**extractor.extra, **args}

                ext = avl_extractors[name_enum](**args)
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


suite_names = dict()
for s in util.get_does_results():
    suite_names[s["suite"].replace("-","_")] = s["suite"]
for s in info.get_suite_designs():
    suite_names[s.replace("-","_")] = s

SuiteName = enum.Enum("SuiteName", suite_names)
"""Name of the available experiment suites in `doe-suite-config/designs`."""


class SuperETLContext(MyETLBaseModel):

    class SuperETLSuiteContext(MyETLBaseModel):

        experiment_names: List[str]


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

            avl_experiments = values['ctx'].suites[suite_name].experiment_names

            if experiments.__root__ == "*":
                experiments.__root__ = avl_experiments
            else:
                missing = list(set(experiments.__root__).difference(avl_experiments))
                assert len(missing) == 0, f"Non-existing experiments: {missing}   (Ctx={values['ctx']})"

        return values


class SuperETL(MyETLBaseModel):

    ctx: SuperETLContext = Field(alias="_CTX", exclude=True)
    """:meta private:"""

    suite_id: Dict[SuiteName, Union[str, Dict[str, str]]] = Field(alias="$SUITE_ID$")

    etl: Dict[str, SuperETLPipeline] = Field(alias="$ETL$")


    @root_validator(pre=True, skip_on_failure=True)
    def context(cls, values):

        # build info on avl suite ids
        existing_suite_ids = {}
        for d in util.get_all_suite_results_dir():
            if d['suite'] not in existing_suite_ids:
                existing_suite_ids[d['suite']] = set()

            existing_suite_ids[d['suite']].add(d['suite_id'])

        # print(f"existing_suite_ids={existing_suite_ids}")

        for suite_name, suite_id_entry in values.get("$SUITE_ID$", {}).items():

            # 1. Check that we have a result for this suite
            assert suite_name in existing_suite_ids, f"no results for suite={suite_name} exist"

            # 2. Convert to dict representation
            if isinstance(suite_id_entry, str) or isinstance(suite_id_entry, int):
                # meaning: every experiment in that suite should be based on this id
                #   -> load all experiments for this suite
                exps = util.get_does_result_experiments(suite=suite_name, suite_id=suite_id_entry)
                values["$SUITE_ID$"][suite_name] = {exp: suite_id_entry for exp in exps}

            # 3. Resolve default suite id
            elif isinstance(suite_id_entry, dict):

                default_suite_id =  suite_id_entry.pop("$DEFAULT$", None)
                assert default_suite_id is None or isinstance(default_suite_id, str) or isinstance(default_suite_id, int), f"default suite id must be string or int but is {default_suite_id}"

                if default_suite_id is not None:
                    # use default suite id for all experiments that are not explicitly set
                    for exp_name in util.get_does_result_experiments(suite=suite_name, suite_id=default_suite_id):
                        if exp_name not in suite_id_entry:
                            suite_id_entry[exp_name] = default_suite_id
            else:
                raise ValueError(f"format of $SUITE_ID$ is invalid for suite={suite_name}")


        # -> now values["$SUITE_ID$"] is a dict of {suite_name: {exp_name: suite_id}}

        suites = {}
        all_exps_d = {}

        for suite_name, suite_id_entry in values.get("$SUITE_ID$", {}).items():
            assert isinstance(suite_id_entry, dict), f"format of $SUITE_ID$ is invalid for suite={suite_name}"

            exps = []
            # we have a dict of {exp_name: suite_id}
            for exp_name, suite_id in suite_id_entry.items():

                if (suite_name, suite_id) not in all_exps_d:
                    all_exps_d[(suite_name, suite_id)] = util.get_does_result_experiments(suite=suite_name, suite_id=suite_id)

                assert exp_name in all_exps_d[(suite_name, suite_id)], f"experiment={exp_name} does not exist in suite={suite_name} suite_id={suite_id_entry}"

                exps.append(exp_name)


            suites[suite_name] = {
                "experiment_names": list(set(exps)),
                # TODO [nku] maybe here load all avaialble etl pipelines from somewhere? -> maybe only from super_etl locally or from templates
               #"etl_pipeline_names": values['ctx'].suites[suite_name].etl_pipeline_names
            }

        #print(f"suites={suites}")

        #print(f"$SUITE_ID$={values.get('$SUITE_ID$', {})}")

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
