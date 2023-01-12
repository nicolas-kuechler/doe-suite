from typing import List
from typing import Dict
from typing import Optional, Any
from typing import Literal
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
import enum
import json

from doespy import util
from doespy.design import dutil
from doespy.design import etl_design



# TODO [nku] because of yaml parsing problems we should switch to ruaml which supports yaml 1.2 -> also look at ruamel.yaml.jinja2
# or use strictyaml as an alternative


class MyBaseModel(BaseModel):
    class Config:
        extra = "forbid"
        smart_union = True
        use_enum_values = True


HostTypeId = enum.Enum("HostTypeId", {ht.replace("-", "_"): ht for ht in util.get_host_types()})
"""Name of a host type and corresponds to folder in `doe-suite-config/group_vars`."""

SetupRoleId = enum.Enum("SetupRoleId", {x.replace("-", "_"):  x for x in util.get_setup_roles()})
"""Name of an Ansible role to setup a host. The role is located in folder: `doe-suite-config/roles`."""


class HostType(MyBaseModel):
    n: int = 1
    check_status: bool = True
    init_roles: Union[SetupRoleId, List[SetupRoleId]] = []
    cmd: Union[str, List[str], List[Dict[str, str]]] = Field(alias="$CMD$")

    class Config:
        extra = "forbid"


class ExperimentConfigDict(MyBaseModel):

    class Config:
        extra = "allow"

    @root_validator(skip_on_failure=True)
    def include_vars(cls, values):
        """At any depth of the config dict, we can include variables from another file.

        ``$INCLUDE_VARS$: Optional[Union[str, List[str]]]``

        Where str corresponds to the file name, e.g., ``test.yml``, in ``doe-suite-config/designs/design_vars``

        All the variables in the external file, are included at the level of where ``$INCLUDE_VARS$`` is located.
        If a variable is already present, then the variable is skipped.
        """

        info = []
        info_len = None

        while info_len != len(info):

            info_len = len(info) # mark initial len -> if change -> len changes

            if len(info) > 100:
                raise warnings.warn("More than 100 $INCLUDE_VARS$, are you sure you did not define an infinite loop of includes?")

            for path, value in dutil.nested_dict_iter(values):

                assert "$INCLUDE_VARS$" not in path[:-1], f"Illegal $INCLUDE_VARS$ formatting: {'.'.join(['d'] + path)}  (must be a string or a list of strings)"

                if path[-1] == "$INCLUDE_VARS$":
                    d = values
                    for p in path[:-1]:
                        d = d[p]

                    del d["$INCLUDE_VARS$"]
                    if isinstance(value, str):
                        value = [value]

                    assert isinstance(value, list) and all(isinstance(s, str) for s in value),  f"Illegal $INCLUDE_VARS$ formatting: {'.'.join(['d'] + path)}  (must be a string or a list of strings)"

                    for external_file in value:
                        # value is the path relative to external dir
                        info_str = f"{'.'.join(['d'] + path)}: {external_file}"
                        file = os.path.join(util.get_suite_design_vars_dir(), external_file)

                        assert os.path.exists(file), f"File not found: {file} for {info_str}"

                        with open(file, "r") as f:
                            vars = yaml.load(f, Loader=yaml.SafeLoader)
                        skipped_info, included_info = dutil.include_vars(d, vars)

                        info += [(info_str, {"skipped": skipped_info, "included": included_info})]

                    # break after every include because include can change "values"
                    # and thus we need to change the nested dict iter process
                    break


        # TODO [nku] could try to properly log this or move away from validation
        # output info on which files where included
        for include_info, details in info:
            print(f"  $INCLUDE_VARS$: {include_info}")
            print(f"    SKIPPED (already present):")
            for s in details["skipped"]:
                print(f"      {s}:")
            print(f"    INCLUDED:")
            for s in details["included"]:
                print(f"      {s}:")

        return values


class SuiteVarsConfigDict(ExperimentConfigDict):
    pass


class Context(MyBaseModel):

    prj_id: str
    suite_name: str

    suite_vars: SuiteVarsConfigDict = None

    experiment_names: List[str]

    etl_pipeline_names: List[str]

    my_experiment_name: str = None

    my_experiment_factor_paths_levellist: List[str] = []
    my_experiment_factor_paths_cross: List[str] = []






class BaseExperimentConfigDict(ExperimentConfigDict):

    # TODO [later] Can we define custom schemas for project and then enforce
    # that they must be present in a certain form across all suites/experiments?
    # (maybe should always be marked as optional but if present, than in that form)

    ctx: Context = Field(alias="_CTX", exclude=True)
    """:meta private:"""

    @root_validator(skip_on_failure=True)
    def merge_suite_vars(cls, values):
        """The ``$SUITE_VARS$`` can define a config that belongs to every experiment of the suite.
        Each experiment defines it's own config in ``base_experiment`` but also inherits config from ``$SUITE_VARS$``.

        When merging the config from ``$SUITE_VARS$`` into the ``base_experiment``, the config in ``base_experiment`` takes precedence, i.e., is not overwritten.
        (Config in the ``base_experiment`` can overwrite config defined in ``$SUITE_VARS$``)
        """

        # at this point, both the suite_vars and the vars here resolved all the $INCLUDE_VARS$ individually
        # -> now need to merge them and the base_experiment vars have precedence

        ctx = values["ctx"]

        if ctx.suite_vars is not None:

            suite_vars_d = ctx.suite_vars.dict()
            if len(suite_vars_d) > 0:

                skipped_info, included_info = dutil.include_vars(values, suite_vars_d)

                # TODO [nku] could try to properly log this or move away from validation
                print(f"  $MERGE_SUITE_VARS$")
                print(f"    SKIPPED (already present):")
                for s in skipped_info:
                    print(f"      {s}:")
                print(f"    INCLUDED:")
                for s in included_info:
                    print(f"      {s}:")

        return values

    @root_validator(skip_on_failure=True)
    def identify_factors(cls, values):
        """Validates the ``$FACTOR$`` syntax.

        Case 1: A ``$FACTOR$`` can be a value, and thus requires an entry in the ``factor_levels`` of the experiment.

        Case 2: A ``$FACTOR$`` can be a key, but then the corresponding value must be a list of factor levels for this factor.
        """
        factors_levellist = []
        factors_cross = []
        # extract `path`of all factors from base experiment

        info = []

        for path, value in dutil.nested_dict_iter(values):

            if value == "$FACTOR$":
                info += [f"$FACTOR$ (Level Syntax) -> {'.'.join(['d'] + path)}: $FACTOR$"]
                factors_levellist.append(path)

            if path[-1] == "$FACTOR$":
                if not isinstance(value, list):
                    raise ValueError(
                        "if $FACTOR$ is the key, then value must be a list of levels",
                        f"(path={path} value={value})",
                    )
                info += [f"$FACTOR$ (Cross Syntax) -> {'.'.join(['d'] + path)}: {value}"]
                factors_cross.append(path)

        values["ctx"].my_experiment_factor_paths_levellist = factors_levellist
        values["ctx"].my_experiment_factor_paths_cross = factors_cross

        # TODO [nku] could try to properly log this or move away from validation
        for i in info:
            print(f"  {i}")
        return values



class Experiment(MyBaseModel):
    """An experiment is composed of a set of runs, each with its own unique configuration.
    The configurations of the runs vary different experiment factors, e.g., number of clients.
    Additionally, an experiment also specifies the hosts responsible for executing the runs.
    """

    ctx: Context = Field(None, alias="_CTX", exclude=True)
    """:meta private:"""

    n_repetitions: int = 1
    """Number of repetitions with the same experiment run configuration."""

    common_roles: Union[SetupRoleId, List[SetupRoleId]] = []
    """Ansible roles executed during the setup of all host types."""

    host_types: Dict[HostTypeId, HostType]
    """The different :ref`host types<Host Type>` involved in the experiment."""

    base_experiment: BaseExperimentConfigDict
    """Defines constants and factors of an experiment."""

    factor_levels: List[Dict] = [{}]
    """For the factors of an experiment, lists the different levels.
    For example, `n_clients` can be a factor with two levels: 1 and 100."""


    class Config:
        extra = "forbid"

    @root_validator(pre=True, skip_on_failure=True)
    def context(cls, values):

        base_experiment = values.get("base_experiment")

        # we remove the ctx because it becomes out of date (due to setting factors in base_experiment)
        ctx = values.pop("_CTX")

        if base_experiment:
            base_experiment["_CTX"] = ctx

        return values


    @root_validator(skip_on_failure=True)
    def check_factor_levels(cls, values):
        """The ``base_experiment`` defines a set of $FACTOR$s that use the level list syntax.
        (i.e., $FACTOR$ is value).
        This validator checks that this set of $FACTOR$s matches each list entry of ``factor_levels``.
        """

        # after setting factor fields in base_experiment, the ctx is here up to date again
        values['ctx'] = values["base_experiment"].ctx
        values["base_experiment"].ctx = None

        expected_factor_paths = values['ctx'].my_experiment_factor_paths_levellist

        for run in values.get("factor_levels"):

            actual_factors = []
            for path, _value in dutil.nested_dict_iter(run):
                actual_factors.append(path)

            assert sorted(expected_factor_paths) == sorted(actual_factors), \
                f"expected factors do not match actual factors: \
                    expected={expected_factor_paths} actual={actual_factors}"
        return values

# TODO [nku] could also extract some of them automatically from pydantic models?
RESERVED_KEYWORDS = ["state", "$FACTOR$", "is_controller_yes", "is_controller_no", "check_status_yes", "check_status_no", "localhost", "n_repetitions", "common_roles", "host_types", "base_experiment", "factor_levels", "n", "init_roles", "check_status", "$CMD$"]
def get_keywords():
    keywords = set()
    for name, cl in inspect.getmembers(sys.modules[__name__], inspect.isclass):
        if issubclass(cl, BaseModel):
            for k in cl.__fields__.keys():
                keywords.add(k)
    return keywords


class SuiteDesign(MyBaseModel):

    ctx: Context = Field(alias="_CTX", exclude=True)
    """:meta private:"""

    suite_vars: SuiteVarsConfigDict = Field(alias="$SUITE_VARS$", default={})
    experiment_designs: Dict[str, Experiment]
    etl: Dict[str, etl_design.ETLPipeline] = Field(alias="$ETL$", default={})

    class Config:
        extra = "forbid"

    @root_validator(pre=True, skip_on_failure=True)
    def context(cls, values):

        ctx = values["_CTX"]


        ctx["experiment_names"] = list(values["experiment_designs"].keys())
        ctx["etl_pipeline_names"] = list(values.get("$ETL$", {}).keys())


        # ETLContext
        for etl_name, etl_pipeline in values.get("$ETL$", {}).items():
            etl_ctx = ctx.copy()
            etl_ctx["my_etl_pipeline_name"] = etl_name
            etl_pipeline["_CTX"] = etl_ctx

        # EXPContext
        ctx["suite_vars"] = values.get("$SUITE_VARS$", None)
        for exp_name, exp in values.get("experiment_designs").items():
            exp_ctx = ctx.copy()
            exp_ctx["my_experiment_name"] = exp_name
            exp["_CTX"] = exp_ctx

        return values





    @validator("experiment_designs")
    def check_exp_names(cls, v):
        # TODO [nku] check min length and forbidden keywords
        for exp_name in v.keys():
             assert exp_name not in RESERVED_KEYWORDS, f'experiment name: "{exp_name}" is not allowed (reserved keyword)'

             assert len(exp_name) <= 200, f'experiment name: "{exp_name}" is not allowed (too long, limit=200)'

             assert re.match(r"^[A-Za-z0-9_]+$", exp_name), f'experiment name: "{exp_name}" is not allowed (must consist of alphanumeric chars or _)'
        return v


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

    suite_vars: SuiteVarsConfigDict = Field(alias="$SUITE_VARS$", default={})
    """Shared variables belonging to every experiment of the suite."""

    # TODO [nku] add a link

    exp1: Experiment = Field(alias="<EXP1>")
    """A suite needs to contain at least one :ref:`experiment<Experiment>`.
    Choose a descriptive experiment name for the placeholder `<EXP1>`."""

    exp2: Optional[Experiment] = Field(alias="<EXP2>")
    """Further :ref:`experiments<Experiment>` are optional.
    Choose a descriptive experiment name for the placeholder `<EXP2>`, `<EXP3>`, etc."""

    etl: Dict[str, etl_design.ETLPipeline] = Field(alias="$ETL$", default={})
    """:ref:`ETL Pipeline` to process the result files."""





# TODO [nku] move to extend the extend case
class Cmd(MyBaseModel):
    __root__: str

    @root_validator(skip_on_failure=True)
    def check_cmd_syntax(cls, values):
        print(f"COMMAND={values}")

        cmd = values.get("__root__")

        import subprocess

        # echo "printf 'x: 1\\ny: 5' > results/coordinates.yaml" | poetry run  shellcheck --shell=bash  /dev/stdin
        # TODO [nku] We have the difficulty of relying on {{ }} commands => here is not possible to verify this
        # -> can only verify this in context of the suite
        result = subprocess.run([f'echo "{cmd}" | shellcheck --shell=bash /dev/stdin'], check=True, text=True, capture_output=True, shell=True)
        print('output: ', result.stdout)
        print('error: ', result.stderr)

        return values

class RunConfig(MyBaseModel):

    cmd: Dict[HostTypeId, Union[Cmd, List[Cmd], List[Dict[Literal['main'], Cmd]]]] = Field(alias="$CMD$")

    class Config:
        extra = "allow"
        arbitrary_types_allowed = True

    @validator("cmd")
    def check_cmd_syntax(cls, v):
        print(f"COMMAND in RUN ={v}")
        return v

class SuiteExt(MyBaseModel):
    __root__: List[RunConfig]



def dict_to_pydantic(suite_name, suite_design_raw):
    suite_design = {"experiment_designs": {}}

    for exp_name, design in suite_design_raw.items():
        if exp_name not in ["$ETL$", "$SUITE_VARS$"]:
            suite_design["experiment_designs"][exp_name] = design

        elif exp_name == "$ETL$":
            suite_design["$ETL$"] = design

        elif exp_name == "$SUITE_VARS$":
            suite_design["$SUITE_VARS$"] = design

    ctx = {
        "prj_id": util.get_project_id(),
        "suite_name": suite_name
    }
    suite_design["_CTX"] = ctx

    # check the pydantic model to check
    model = SuiteDesign(**suite_design)

    return model

def pydantic_to_dict(model):

    suite_design = {}

    for name, exp in model.experiment_designs.items():

        exp_design = exp.json(by_alias=True, exclude_none=True)

        suite_design[name] = json.loads(exp_design)

    suite_design["$ETL$"] = {}
    for name, pipeline in model.etl.items():

        etl_pipeline = pipeline.json(by_alias=True, exclude_none=True)
        suite_design["$ETL$"][name] = json.loads(etl_pipeline)

    return suite_design


if __name__ == "__main__":

    print(get_keywords())
