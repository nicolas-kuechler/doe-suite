from typing import Annotated, List
from typing import Dict
from typing import Optional, Any
from typing import Union

from pydantic import Discriminator, RootModel, Tag, field_validator, model_validator, ConfigDict, Field
from pydantic import BaseModel


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
    model_config = ConfigDict(extra="forbid", use_enum_values=True)

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


    model_config = ConfigDict(extra="forbid", allow_reuse=True)

    etl_pipeline: 'ETLPipelineBase' = Field(None, alias="_ETL_PIPELINE", exclude=True)
    """:meta private:"""

    @field_validator("suite")
    @classmethod
    def check_suite_available(cls, v):
        """checks that referenced suite exists"""
        if v is not None:
            avl_suites = info.get_suite_designs()
            if v not in avl_suites:
                raise ValueError(f"source not found: suite={v}")

        return v


    @field_validator("config")
    def check_config_available(cls, v, values):
        """checks that referenced config exists"""
        if v is not None:

            avl_configs = util.get_all_super_etl_configs()
            #avl_suites = info.get_suite_designs()
            if v not in avl_configs:
                raise ValueError(f"source not found: suite={v}")

        return v

    @field_validator("template")
    @classmethod
    def check_template_available(cls, v):
        """checks that referenced etl template exists"""
        if v is not None:
            designs_dir = util.get_suite_design_etl_template_dir()
            avl_suites = info.get_suite_designs(designs_dir=designs_dir)
            if v not in avl_suites:
                raise ValueError(f"source not found: suite={v}")

        return v


    @field_validator("pipeline")
    def check_suite_xor_template(cls, v, values):

        """checks that either suite or template or config is used"""

        count = 0

        if values.data.get("suite", None) is not None:
            count += 1

        if values.data.get("config", None) is not None:
            count += 1

        if values.data.get("template", None) is not None:
            count += 1

        assert count == 1, f"IncludeSource malformed: suite, config, and template are mutually exclusive but are: suite={values.get('suite')}  config={values.get('config')}  template={values.get('template')}"

        return v


    @field_validator("pipeline")
    def check_pipeline_available(cls, v, values):
        """checks that referenced pipeline in suite or template exists"""

        if values.data.get("suite") is not None:
            avl_pipelines = info.get_etl_pipelines(values.data["suite"])
        elif values.data.get("config") is not None:
            dir = util.get_super_etl_dir()
            avl_pipelines = info.get_etl_pipelines(values.data["config"], designs_dir=dir)
        elif values.data.get("template") is not None:
            dir = util.get_suite_design_etl_template_dir()
            avl_pipelines = info.get_etl_pipelines(values.data["template"], designs_dir=dir)
        else:
            raise ValueError("no suite, config, or template found")

        if v not in avl_pipelines:
            raise ValueError(
                f"source not found: suite={values.data['suite']}  template={values.data['template']}  pipeline={v}"
            )

        return v

    @model_validator(mode="after")
    def include_etl_pipeline(self):
        """loads the external etl source (and checks that the name of extractor, transformer, and loader are ok)"""


        if self.suite is not None:
            design = util.get_suite_design(self.suite)

        elif self.config is not None:
            dir = util.get_super_etl_dir()
            design = util.get_suite_design(suite=self.config, folder=dir)

        elif self.template is not None:
            templ_dir = util.get_suite_design_etl_template_dir()
            design = util.get_suite_design(suite=self.template, folder=templ_dir)


        etl_pipeline = design["$ETL$"][self.pipeline]
        if "experiments" in etl_pipeline:
            del etl_pipeline["experiments"]

        self.etl_pipeline = ETLPipelineBase(**etl_pipeline)
        return self



def _build_extra(cls, values: Dict[str, Any]):

    extra = {}
    keys = list(values.keys())
    for k in keys:
        if k not in cls.model_fields:
            v = values.pop(k)
            extra[k] = v
    values["extra"] = extra



avl_extractors, avl_transformers, avl_loaders = _load_available_processes()

extractors = {ext: ext for ext in avl_extractors.keys()}
extractors["INCLUDE_STEPS"] = "$INCLUDE_STEPS$"
ExtractorId = enum.Enum("ExtractorId", extractors)

transformers = {tr: tr for tr in avl_transformers.keys()}
TransformerId = enum.Enum("TransformerId", transformers)

loaders = {ld: ld for ld in avl_loaders.keys()}
loaders["INCLUDE_STEPS"] = "$INCLUDE_STEPS$"
LoaderId = enum.Enum("LoaderId", loaders)



class ExtractorDesign(MyETLBaseModel):

    file_regex: Optional[Union[str, List[str]]] = None
    model_config = ConfigDict(extra="allow")

    @model_validator(mode="before")
    @classmethod
    def build_extra(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        _build_extra(cls, values)
        return values


class TransformerDesign(MyETLBaseModel):
    pass

class IncludeStepTransformer(TransformerDesign):
    include_steps: IncludeEtlSource = Field(alias="$INCLUDE_STEPS$")
    model_config = ConfigDict(extra="forbid")


class NamedTransformer(TransformerDesign):
    name: TransformerId
    model_config = ConfigDict(extra="allow")

    @model_validator(mode="before")
    @classmethod
    def build_extra(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        _build_extra(cls, values)
        return values


avl_df_functions = set()
for name, _ in inspect.getmembers(pd.DataFrame, predicate=inspect.isfunction):
    if not name.startswith("_"):
        avl_df_functions.add(f"df.{name}")


class DfTransformer(TransformerDesign):
    model_config = ConfigDict(extra="allow")

    @model_validator(mode="after")
    def check_df_function(self) -> Dict[str, Any]:

        for v in self.model_dump().keys():
            assert v in avl_df_functions, f"{v} is unknown df function"

        return self

class LoaderDesign(MyETLBaseModel):
    include_steps: Optional[List[IncludeEtlSource]] = Field(None, alias="$INCLUDE_STEPS$")
    model_config = ConfigDict(extra="allow")

    extra: Dict[str, Any]

    @model_validator(mode="before")
    @classmethod
    def build_extra(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        _build_extra(cls, values)
        return values



def get_transformer_disc_value(v: Any) -> str:
    if "name" in v:
        return "named"

    if all(k == "$INCLUDE_STEPS$"  for k in v.keys()):
        return "include"

    if all(k.startswith("df.") for k in v.keys()):
        return "df"

    assert False, f"unknown transformer type: {v}"



def get_extractor_disc_value(v: Any) -> str:
    if isinstance(v, list):
        return "include"
    else:
        return "extractor"


def get_loader_disc_value(v: Any) -> str:
    if isinstance(v, list):
        return "include"
    else:
        return "loader"

class ETLPipelineBase(MyETLBaseModel):

    include_pipeline: Optional[IncludeEtlSource] = Field(default=None, alias="$INCLUDE_PIPELINE$", exclude=True)

    extractors: Dict[ExtractorId, Annotated[Union[Annotated[List[IncludeEtlSource], Tag("include")], Annotated[ExtractorDesign, Tag("extractor")], Annotated[Any, Tag("EXTERNAL")]], Discriminator(get_extractor_disc_value), ]] = {}

    transformers: List[Annotated[Union[Annotated[NamedTransformer, Tag('named')], Annotated[DfTransformer, Tag('df')], Annotated[IncludeStepTransformer, Tag('include')], Annotated[Any, Tag('EXTERNAL')]],Discriminator(get_transformer_disc_value),]] = []

    # TODO [nku] loaders should also be possible to be a list because may want to use same loader id multiple times
    loaders: Dict[LoaderId, Annotated[Union[Annotated[List[IncludeEtlSource], Tag("include")], Annotated[LoaderDesign, Tag("loader")], Annotated[Any, Tag("EXTERNAL")]], Discriminator(get_loader_disc_value), ]] = {}
    model_config = ConfigDict(extra="forbid", use_enum_values=False)



    @model_validator(mode="after")
    def inc_pipeline(self):


        if self.include_pipeline is not None:


            assert len(self.extractors) == 0
            assert len(self.transformers) == 0
            assert len(self.loaders) == 0

            self.extractors = self.include_pipeline.etl_pipeline.extractors
            self.transformers = self.include_pipeline.etl_pipeline.transformers
            self.loaders = self.include_pipeline.etl_pipeline.loaders
            self.include_pipeline = None  # mark as complete

        return self

    @model_validator(mode="after")
    def inc_extractors(self):
        if ExtractorId.INCLUDE_STEPS in self.extractors:
            for include_etl_source in self.extractors[ExtractorId.INCLUDE_STEPS]:
                for k, v in include_etl_source.etl_pipeline.extractors.items():
                    self.extractors[k] = v
            del self.extractors[ExtractorId.INCLUDE_STEPS]
        return self


    @model_validator(mode="after")
    def inc_transformer(self):

        steps = []
        for t in self.transformers:
            if isinstance(t, IncludeStepTransformer):
                for step in t.include_steps.etl_pipeline.transformers:
                    steps.append(step)
            else:
                steps.append(t)
        self.transformers = steps

        return self


    @model_validator(mode="after")
    def inc_loader(self):

        if LoaderId.INCLUDE_STEPS in self.loaders:
            for include_etl_source in self.loaders[LoaderId.INCLUDE_STEPS]:
                for k, v in include_etl_source.etl_pipeline.loaders.items():
                    self.loaders[k] = v
            del self.loaders[LoaderId.INCLUDE_STEPS]

        return self


class ExperimentNames(RootModel):
    root: Union[str, List[str]]

    @field_validator("root")
    @classmethod
    def check_exp(cls, v):
        assert v == "*" or isinstance(v, list), f"experiments must be a list of strings or * but is: {v}"
        return v

class ETLPipeline(ETLPipelineBase):

    ctx: ETLContext = Field(alias="_CTX", exclude=True, )
    """:meta private:"""

    experiments: ExperimentNames

    etl_vars: Optional[Dict[str, Any]] = Field(None, alias="$ETL_VARS$")
    model_config = ConfigDict(extra="forbid")



    @model_validator(mode="after")
    def check_experiments(self):
        """Resolves * in experiments and
        ensures that every experiment listed, also exists in the suite
        """

        experiments = self.experiments.root
        avl_experiments = self.ctx.experiment_names

        if experiments == "*":
            self.experiments.root = avl_experiments
        else:
            missing = list(set(experiments).difference(avl_experiments))
            assert len(missing) == 0, f"Non-existing experiments: {missing}   (Ctx={self.ctx})"

        return self


    @model_validator(mode="after")
    def resolve_etl_vars(self):
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

        etl_vars = self.etl_vars
        if etl_vars is not None:

            from itertools import chain

            for step in chain(self.extractors.values(), self.transformers, self.loaders.values()):
                if hasattr(step, 'extra') and len(step.extra) > 0:
                    step.extra = include_etl_vars(step.extra, etl_vars)
        self.etl_vars = None
        return self


    @model_validator(mode="after")
    def check_extractors(self):
        """check that each extractor (also included) defines the correct values"""
        #print(f"Create Extractor from ExtractorDesign (and check Extractor fields)")

        d = {}
        for name_enum, extractor in self.extractors.items():
            assert isinstance(name_enum, ExtractorId), f"invalid extractor id: {name_enum}"

            if isinstance(extractor, ExtractorDesign):
                args = extractor.model_dump()
                if "extra" in args:
                    del args["extra"]

                if "file_regex" in args and args["file_regex"] is None:
                    del args["file_regex"]

                args = {**extractor.extra, **args}

                ext = avl_extractors[name_enum.value](**args)

                d[name_enum] = ext
            else:
                d[name_enum] = extractor
        self.extractors = d
        return self

    @model_validator(mode="after")
    def check_transformers(self):
        """check that each transformer (also included) defines the correct values"""

        #print(f"Create Transformer from TransformerDesign (and check Transformer fields)")
        steps = []
        for t in self.transformers:
            assert not isinstance(t, IncludeStepTransformer)

            if isinstance(t, NamedTransformer) and t.name is not None:
                trans = avl_transformers[t.name](**t.extra, name=t.name)
                steps.append(trans)
            else:
                steps.append(t)
        self.transformers = steps
        return self

    @model_validator(mode="after")
    def check_loaders(self):
        """check that each loader (also included) defines the correct values"""
        #print(f"Create Loader from LoaderDesign (and check Loader fields)")

        d = {}
        for name_enum, loader in self.loaders.items():

            assert isinstance(name_enum, LoaderId), f"invalid loader id: {name_enum}"
            if isinstance(loader, LoaderDesign):
                ext = avl_loaders[name_enum.value](**loader.extra)
                d[name_enum] = ext
            else:
                d[name_enum] = loader
        self.loaders = d
        return self


suite_names = dict()
for s in util.get_does_results():
    suite_names[s["suite"].replace("-","_")] = s["suite"]
for s in info.get_suite_designs():
    suite_names[s.replace("-","_")] = s

SuiteName = enum.Enum("SuiteName", suite_names)
"""Name of the available experiment suites in `doe-suite-config/designs`."""


class SuperETLContext(MyETLBaseModel):

    model_config = ConfigDict(use_enum_values=False)

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


    @model_validator(mode="after")
    def check_experiments(self):
        """Resolves * in experiments and
        #ensures that every experiment listed, also exists in the suite
        """

        for suite_name, experiments in self.experiments.items():
            avl_experiments = self.ctx.suites[suite_name].experiment_names

            if experiments.root == "*":
                experiments.root = avl_experiments
            else:
                missing = list(set(experiments.root).difference(avl_experiments))
                assert len(missing) == 0, f"Non-existing experiments: {missing}   (Ctx={self.ctx})"

        return self


class SuperETL(MyETLBaseModel):

    ctx: SuperETLContext = Field(alias="_CTX", exclude=True)
    """:meta private:"""

    suite_id: Dict[SuiteName, Union[str, Dict[str, str]]] = Field(alias="$SUITE_ID$")

    etl: Dict[str, SuperETLPipeline] = Field(alias="$ETL$")


    @model_validator(mode="before")
    @classmethod
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
