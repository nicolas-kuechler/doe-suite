from typing import List
from typing import Dict
from typing import Optional, Any
from doespy.design import etl_design

from pydantic import Field
from typing import Union
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
from doespy import info
from doespy.design import dutil
from doespy.design import extend

# TODO [nku] shoudl never access values["abc"] in root_validator because if abc failed -> will not be there
# TODO [nku] root validators should maybe use skip_on_failure=True because as soon as the first thing failed we don't want to conitnue?

class MyBaseModel(BaseModel):
    class Config:
        extra = "forbid"
        smart_union = True
        use_enum_values = True #TODO [nku] could think about this


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

class BaseExperimentConfigDict(ExperimentConfigDict):

    # TODO [later] Can we define custom schemas for project and then enforce
    # that they must be present in a certain form across all suites/experiments?
    # (maybe should always be marked as optional but if present, than in that form)

    # TODO [nku] try PrivateAttr() instead of Field()
    _inherited_suite_vars: SuiteVarsConfigDict = Field(None, alias="$INHERITED_SUITE_VARS$", hidden=True)

    _paths_require_factor_level: List[List[str]] = Field(None, alias="$PATHS_REQUIRE_FACTOR_LEVEL$", hidden=True, exclude=True)

    @root_validator(skip_on_failure=True)
    def merge_suite_vars(cls, values):
        """The ``$SUITE_VARS$`` can define a config that belongs to every experiment of the suite.
        Each experiment defines it's own config in ``base_experiment`` but also inherits config from ``$SUITE_VARS$``.

        When merging the config from ``$SUITE_VARS$`` into the ``base_experiment``, the config in ``base_experiment`` takes precedence, i.e., is not overwritten.
        (Config in the ``base_experiment`` can overwrite config defined in ``$SUITE_VARS$``)
        """

        # at this point, both the suite_vars and the vars here resolved all the $INCLUDE_VARS$ individually
        # -> now need to merge them and the base_experiment vars have precedence

        suite_vars = values.pop("$INHERITED_SUITE_VARS$", None)

        if suite_vars is not None and len(suite_vars) > 0:
            skipped_info, included_info = dutil.include_vars(values, suite_vars)

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
        factors = []
        # extract `path`of all factors from base experiment

        info = []

        for path, value in dutil.nested_dict_iter(values):

            if value == "$FACTOR$":
                info += [f"$FACTOR$ (Level Syntax) -> {'.'.join(['d'] + path)}: $FACTOR$"]
                factors.append(path)

            if path[-1] == "$FACTOR$":
                if not isinstance(value, list):
                    raise ValueError(
                        "if $FACTOR$ is the key, then value must be a list of levels",
                        f"(path={path} value={value})",
                    )
                info += [f"$FACTOR$ (Cross Syntax) -> {'.'.join(['d'] + path)}: {value}"]

        values["$PATHS_REQUIRE_FACTOR_LEVEL$"] = factors

        # TODO [nku] could try to properly log this or move away from validation
        for i in info:
            print(f"  {i}")
        return values



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

    base_experiment: BaseExperimentConfigDict
    """Defines constants and factors of an experiment."""

    factor_levels: List[Dict] = [{}]
    """For the factors of an experiment, lists the different levels.
    For example, `n_clients` can be a factor with two levels: 1 and 100."""

    inherited_suite_vars: SuiteVarsConfigDict = Field(None, alias="$INHERITED_SUITE_VARS$")
    """:meta private:"""


    class Config:
        extra = "forbid"


    @root_validator(pre=True, skip_on_failure=True)
    def _propagate_suite_vars(cls, values):



        # this is only a utility validator that sets the inherited suite vars in the base experiment
        # where they are merged

        base_experiment = values.get("base_experiment")

        if base_experiment:
            base_experiment["$INHERITED_SUITE_VARS$"] = values.get("$INHERITED_SUITE_VARS$")

        #raise ValueError(f"blocker={values}")
        return values


    @root_validator(skip_on_failure=True)
    def check_factor_levels(cls, values):
        """The ``base_experiment`` defines a set of $FACTOR$s that use the level list syntax.
        (i.e., $FACTOR$ is value).
        This validator checks that this set of $FACTOR$s matches each list entry of ``factor_levels``.
        """
        base_experiment = values.get("base_experiment")
        factor_levels_raw =  values.get("factor_levels")

        if base_experiment is None or factor_levels_raw is None:
            # nothing for this validator to check (another validator must have failed before)
            return values

        expected_factor_paths = base_experiment.dict().get("$PATHS_REQUIRE_FACTOR_LEVEL$")

        for run in factor_levels_raw:

            actual_factors = []
            for path, _value in dutil.nested_dict_iter(run):
                actual_factors.append(path)

            assert sorted(expected_factor_paths) == sorted(actual_factors), \
                f"expected factors do not match actual factors: \
                    expected={expected_factor_paths} actual={actual_factors}"
        return values

# TODO [nku] could also extract some of them automatically from pydantic models?
RESERVED_KEYWORDS = ["state", "$FACTOR$", "is_controller_yes", "is_controller_no", "check_status_yes", "check_status_no", "localhost", "n_repetitions", "common_roles", "host_types", "base_experiment", "factor_levels", "n", "init_roles", "check_status", "$CMD$"]

class SuiteDesign(MyBaseModel):
    suite_vars: SuiteVarsConfigDict = Field(alias="$SUITE_VARS$", default={})
    experiment_designs: Dict[str, Experiment]
    etl: Dict[str, etl_design.ETLPipeline] = Field(alias="$ETL$", default={})

    class Config:
        extra = "forbid"

    @root_validator(pre=True, skip_on_failure=True)
    def distribute_suite_vars(cls, values):

        # set the suite vars as a field in all experiment designs
        suite_vars = values.get("$SUITE_VARS$")

        for _, exp in values.get("experiment_designs").items():
            exp["$INHERITED_SUITE_VARS$"] = suite_vars

        #raise ValueError(f"BLOCKER!!!!!!!!! values={values}\n\n")
        return values

    @validator("experiment_designs", pre=True)
    def demo(cls, v, values):
        #print(f"\n\ndemo v={v} \n\n\nvalues={values}")
        return v

    @validator("experiment_designs")
    def check_exp_names(cls, v):
        # TODO [nku] check min length and forbidden keywords
        for exp_name in v.keys():
             assert exp_name not in RESERVED_KEYWORDS, f'experiment name: "{exp_name}" is not allowed (reserved keyword)'

             assert len(exp_name) <= 200, f'experiment name: "{exp_name}" is not allowed (too long, limit=200)'

             assert re.match(r"^[A-Za-z0-9_]+$", exp_name), f'experiment name: "{exp_name}" is not allowed (must consist of alphanumeric chars or _)'
        return v

    @root_validator(skip_on_failure=True)
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



def check_suite(suite):
    suite = util.get_suite_design(suite=suite)
    validate(suite_design_raw=suite, exp_filter=None)


    #model = SuiteExt.parse_obj(exp_design_ext)




    print("=======================")
    #print(f"\n\nDesign={_model.experiment_designs}")



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

    from typing import Literal

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

def get_keywords():
    keywords = set()
    for name, cl in inspect.getmembers(sys.modules[__name__], inspect.isclass):
        if issubclass(cl, BaseModel):
            for k in cl.__fields__.keys():
                keywords.add(k)
    return keywords


def dict_to_pydantic(suite_design_raw):
    suite_design = {"experiment_designs": {}}

    for exp_name, design in suite_design_raw.items():
        if exp_name not in ["$ETL$", "$SUITE_VARS$"]:
            suite_design["experiment_designs"][exp_name] = design

        elif exp_name == "$ETL$":
            suite_design["$ETL$"] = design

        elif exp_name == "$SUITE_VARS$":
            suite_design["$SUITE_VARS$"] = design


    # check the pydantic model to check
    model = SuiteDesign(**suite_design)

    return model

def pydantic_to_dict(model):

    suite_design = {}

    # TODO [nku] do we even want to keep them separately? -> they are already included into the base experiment?
    #suite_vars = model.suite_vars.json()
    #suite_design["$SUITE_VARS$"] = json.loads(suite_vars)

    for name, exp in model.experiment_designs.items():

        # TODO [nku] not sure why I need to exclude those specifically here
        exp_design = exp.json(by_alias=True, exclude={"base_experiment": {"$PATHS_REQUIRE_FACTOR_LEVEL$", "inherited_suite_vars"}, "inherited_suite_vars": True})

        suite_design[name] = json.loads(exp_design)


    print(model.etl)
    suite_design["$ETL$"] = {}
    for name, pipeline in model.etl.items():

        etl_pipeline = pipeline.json(by_alias=True, exclude_none=True, exclude={"$INCLUDE_PIPELINE$"})

        suite_design["$ETL$"][name] = json.loads(etl_pipeline)


    #etl = model.etl

    #suite_design["$ETL$"] = model.etl #json.loads(etl)


    return suite_design

# TODO [nku] continue structure
def validate(suite_design_raw, exp_filter):



    model = dict_to_pydantic(suite_design_raw)

    suite_design = pydantic_to_dict(model)

    print(f"Suite Design:")
    print("================================")
    print(suite_design)
    print("================================")

    #if exp_filter is not None:
    #    _apply_experiment_re_filter(design_raw=suite_design, exp_filter=exp_filter)

if __name__ == "__main__":


    #suite = util.get_suite_design(suite="example02-single")
    #validate(suite_design_raw=suite, exp_filter=None)

    #check_suite(suite="example01-minimal")
    #check_suite(suite="example02-single")
    #check_suite(suite="example03-format")
    #check_suite(suite="example04-multi")
    #check_suite(suite="example05-complex")
    #check_suite(suite="example06-vars")
    check_suite(suite="example07-etl") #TODO [nku] at the moment this does not work yet

    # model = Experiment(**exp)