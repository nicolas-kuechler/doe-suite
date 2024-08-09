does_config_dir=$(DOES_PROJECT_DIR)/doe-suite-config
does_results_dir=$(DOES_PROJECT_DIR)/doe-suite-results

# default output path for super etl
DOES_SUPERETL_OUT?=$(DOES_PROJECT_DIR)/doe-suite-results-super
out?=$(DOES_SUPERETL_OUT)

DOES_CLOUD?=aws
cloud?=$(DOES_CLOUD) # env variable with default (aws)

test_delay?=0

DOES_CLOUD_STATE?=terminate
state?=$(DOES_CLOUD_STATE) # env variable with default (terminate)


epoch=$(shell date +%s)

# if id=last -> need to find the last suite id (based on suite name)
_suite_id= $(shell [ $(id) = last ] && (cd $(does_results_dir) && find . -type d -regex './$(suite)_[0-9]+' | sort | tail -n 1 | grep -o '[0-9]*$$') || echo $(id))
suite_id= $(shell [ $(id) = new ] && echo $(epoch) || echo $(_suite_id))

ansible_inventory=$(does_results_dir)/$(suite)_$(suite_id)/.inventory

# add prefix if defined for playbook run cmd
ifdef expfilter
	myexpfilter=expfilter=$(expfilter)
endif

# TODO [nku] would it be possible if suite not defined and required to show available suites and take number input?
ifdef suite
	mysuite=--suite $(suite)
endif

ifdef id
	myid=--id $(id)
endif

ifdef pipelines
	mypipelines=--pipelines $(pipelines)
endif

ifdef custom-suite-id # custom-suite-id="<suite>=<id> <suite>=<id>"
	mycustomsuiteid=--suite_id $(custom-suite-id)
endif

# on `make` and `make help` list all targets with information
help:
	@echo 'Running Experiments'
	@echo '  make run suite=<SUITE> id=new                       - run the experiments in the suite'
	@echo '  make run suite=<SUITE> id=<ID>                      - continue with the experiments in the suite with <ID> (often id=last)'
	@echo '  make run suite=<SUITE> id=<ID> cloud=<CLOUD>        - run suite on non-default cloud ([aws], euler)'
	@echo '  make run suite=<SUITE> id=<ID> expfilter=<REGEX>    - run only subset of experiments in suite where name matches the <REGEX> (suite must be valid)'
	@echo '  make run-keep suite=<SUITE> id=new                  - does not terminate instances at the end, otherwise works the same as run target'
	@echo 'Clean'
	@echo '  make clean                                          - terminate running cloud instances belonging to the project and local cleanup'
	@echo '  make clean-result                                   - delete all inclomplete results in doe-suite-results'
	@echo 'Running ETL Locally'
	@echo '  make etl suite=<SUITE> id=<ID>                      - run the etl pipeline of the suite (locally) to process results (often id=last)'
	@echo '  make etl-design suite=<SUITE> id=<ID>               - same as `make etl ...` but uses the pipeline from the suite design instead of results'
	@echo '  make etl-all                                        - run etl pipelines of all results'
	@echo '  make etl-super config=<CONFIG> out=<PATH>           - run the super etl to combine results of multiple suites  (for <CONFIG> e.g., demo_plots)'
	@echo '  make etl-super ... pipelines="<P1> <P2>"            - run only a subset of pipelines in the super etl'
	@echo 'Clean ETL'
	@echo '  make etl-clean suite=<SUITE> id=<ID>                - delete etl results from specific suite (can be regenerated with make etl ...)'
	@echo '  make etl-clean-all                                  - delete etl results from all suites (can be regenerated with make etl-all)'
	@echo 'Gather Information'
	@echo '  make info                                           - list available suite designs'
	@echo '  make status suite=<SUITE> id=<ID>                   - show the status of a specific suite run (often id=last)'
	@echo 'Design of Experiment Suites'
	@echo '  make design suite=<SUITE>                           - list all the run commands defined by the suite'
	@echo '  make design-validate suite=<SUITE>                  - validate suite design and show with default values'
	@echo 'Setting up a Suite'
	@echo '  make new                                            - initialize doe-suite-config from a template'
	@echo 'Running Tests'
	@echo '  make test                                           - running all suites (seq) and comparing results to expected (on aws)'
	@echo '  make euler-test cloud=euler                         - running all single instance suites on euler and compare results to expected'
	@echo '  make etl-test-all                                   - re-run all etl pipelines and compare results to current state (useful after update of etl step)'


#################################
#  ___ ___ _____ _   _ ___
# / __| __|_   _| | | | _ \
# \__ \ _|  | | | |_| |  _/
# |___/___| |_|  \___/|_|
#
#################################
# https://patorjk.com/software/taag/#p=display&h=2&v=2&f=Small&t=SETUP

# initialize a doe-suite-config from cookiecutter template (use defaults + ask user for inputs)
new:
	@if [ ! -f $(does_config_dir)/pyproject.toml ]; then \
		poetry -C doespy install && \
		poetry -C doespy run cookiecutter cookiecutter-doe-suite-config -o $(DOES_PROJECT_DIR); \
	fi

# depending on`cloud` variable, check if connection can be established
cloud-check:
	@if [ $(cloud) = aws ]; then aws sts get-caller-identity > /dev/null || aws configure; fi
	@if [ $(cloud) = euler ]; then ping -c 1 -W 1 login.euler.ethz.ch > /dev/null || (echo "\nCannot reach login.euler.ethz.ch, are you connected to the ETHZ network, e.g., via VPN?" && exit 1); fi

# install dependenicies to ensure that suites can be run + etl
install: new
	@cd $(does_config_dir) && \
	poetry install && \
	poetry run ansible-galaxy install -r $(PWD)/requirements-collections.yml


install-silent: new
	@cd $(does_config_dir) && \
	poetry install > /dev/null && \
	poetry run ansible-galaxy install -r $(PWD)/requirements-collections.yml > /dev/null


#################################
#  ___ _   _ _  _
# | _ \ | | | \| |
# |   / |_| | .` |
# |_|_\\___/|_|\_|
#
#################################
# https://patorjk.com/software/taag/#p=display&h=2&v=2&f=Small&t=RUN

# run a all experiments in a suite
.PHONY: run
run: install cloud-check
	@cd $(does_config_dir) && \
	ANSIBLE_CONFIG=$(PWD)/ansible.cfg \
	ANSIBLE_INVENTORY=$(ansible_inventory) \
	poetry run ansible-playbook $(PWD)/src/experiment-suite.yml -e "suite=$(suite) id=$(id) epoch=$(epoch) cloud=$(cloud) $(myexpfilter)"

.PHONY: run
run-keep: install cloud-check
	@cd $(does_config_dir) && \
	ANSIBLE_CONFIG=$(PWD)/ansible.cfg \
	ANSIBLE_INVENTORY=$(ansible_inventory) \
	poetry run ansible-playbook $(PWD)/src/experiment-suite.yml -e "suite=$(suite) id=$(id) epoch=$(epoch) cloud=$(cloud) $(myexpfilter) awsclean=False"

# TODO [nku] integrate them into run target when they are available
#
#run-keep: state=keep
#run-keep: run
#
#run-stop: state=stop
#run-stop: run
#
#run-terminate: state=terminate
#run-terminate: run


#################################
#  ___ _____ _
# | __|_   _| |
# | _|  | | | |__
# |___| |_| |____|
#
#################################
# https://patorjk.com/software/taag/#p=display&h=2&v=2&f=Small&t=ETL

# run etl pipelines from a specific suite run
.PHONY: etl
etl: install
	@cd $(does_config_dir) && \
	poetry run python $(PWD)/doespy/doespy/etl/etl.py --suite $(suite) --id $(id)

# can be used for remote debugging with e.g., vs code
etl-debug: install
	@cd $(does_config_dir) && \
	poetry run python -m debugpy --listen 5678 --wait-for-client $(PWD)/doespy/doespy/etl/etl.py --suite $(suite) --id $(id)

# instead of using the etl pipeline defined in the results folder, it uses the pipeline from the design
# useful for developing an etl pipeline
etl-design: install
	@cd $(does_config_dir) && \
	poetry run python $(PWD)/doespy/doespy/etl/etl.py --suite $(suite) --id $(id) --load_from_design

# run etl pipelines for all available results
etl-all: install
	@cd $(does_config_dir) && \
	poetry run python $(PWD)/doespy/doespy/etl/etl.py --all

# run the etl pipelines defined in the doe-suite-config/super_etl/$(config)
#  write the etl results into $(out)
# e.g., make etl-super config=demo_plots out=/home/kuenico/dev/doe-suite/tmp
etl-super: install
	@cd $(does_config_dir) && \
	poetry run python $(PWD)/doespy/doespy/etl/super_etl.py --config $(config) --output_path $(out) $(mypipelines) $(mycustomsuiteid)

etl-super-debug: install
	@cd $(does_config_dir) && \
	poetry run python -m debugpy --listen 5678 --wait-for-client $(PWD)/doespy/doespy/etl/super_etl.py --config $(config) --output_path $(out) $(mypipelines)


# delete etl results for a specific `suite` and `id`  (can be regenerated with `make etl suite=<SUITE> id=<ID>`)
etl-clean: install
	@cd $(does_config_dir) && \
	poetry run python $(PWD)/doespy/doespy/etl/etl_clean.py --suite $(suite) --id $(id)

# delete all etl results  (can be regenerated with `make etl-all`)
etl-clean-all: install
	@cd $(does_config_dir) && \
	poetry run python $(PWD)/doespy/doespy/etl/etl_clean.py --all

# reruns all etl pipelines of all suite runs and compares the results
#   -> can be used to check that a change in an ETL step did not break another earlier suite
etl-test-all: install
	@cd $(does_config_dir) && \
	poetry run pytest $(PWD)/doespy -q -k 'test_etl_pipeline' -s



#################################
#    ___ _    ___   _   _  _
#  / __| |  | __| /_\ | \| |
# | (__| |__| _| / _ \| .` |
#  \___|____|___/_/ \_\_|\_|
#
#################################
# https://patorjk.com/software/taag/#p=display&h=2&v=2&f=Small&t=CLEAN


# delete surplus python files: https://gist.github.com/lumengxi/0ae4645124cd4066f676
clean-local-py:
	@find . -name '*.pyc' -exec rm -f {} +
	@find . -name '*.pyo' -exec rm -f {} +
	@find . -name '*~' -exec rm -f {} +
	@find . -name '__pycache__' -exec rm -fr {} +
	@find . -name '.pytest_cache' -exec rm -fr {} +

# delete all incomplete results
clean-result: install
	@echo -n "Are you sure to delete all the incomplete results in $(does_results_dir)? [y/N] " && read ans && [ $${ans:-N} = y ]
	@cd $(does_config_dir) && \
	poetry run python $(PWD)/doespy/doespy/result_clean.py --incomplete

# only keep one suite run per suite (the last complete)
clean-result-full: install
	@echo -n "Are you sure to delete all the results in $(does_results_dir) except for the ones with the highest id? [y/N] " && read ans && [ $${ans:-N} = y ]
	@cd $(does_config_dir) && \
	poetry run python $(PWD)/doespy/doespy/result_clean.py --keeplast

clean-cloud: install
	@cd $(does_config_dir) && \
	ANSIBLE_CONFIG=$(PWD)/ansible.cfg \
	poetry run ansible-playbook $(PWD)/src/clear.yml -e "cloud=$(cloud)"


.PHONY: confirm
confirm:
	@echo -n 'Are you sure? [y/N] ' && read ans && [ $${ans:-N} = y ]

clean-docker:
	@echo "Terminating all doe-suite related docker containers..."
	@if $(MAKE) confirm ; then  $(MAKE) clean-cloud cloud=docker; else echo "skipping clean-docker"; fi

clean-aws:
	@echo "Terminating all doe-suite related aws ec2 instances (+vpc)..."
	@if $(MAKE) confirm ; then  $(MAKE) clean-cloud cloud=aws; else echo "skipping clean-aws"; fi

clean:  clean-local-py clean-docker clean-aws


#################################
#  ___ _  _ ___ ___
# |_ _| \| | __/ _ \
#  | || .` | _| (_) |
# |___|_|\_|_| \___/
#
#################################
# https://patorjk.com/software/taag/#p=display&h=2&v=2&f=Small&t=INFO

# list infos about the doe-suite-config (config + designs)
info: install-silent
	@cd $(does_config_dir) && \
	poetry run python $(PWD)/doespy/doespy/info.py

# show status info of a suite (how much progress)
status: install-silent
	@cd $(does_config_dir) && \
	poetry run python $(PWD)/doespy/doespy/status.py $(mysuite) $(myid)


#################################
#  _____ ___ ___ _____
# |_   _| __/ __|_   _|
#   | | | _|\__ \ | |
#   |_| |___|___/ |_|
#
#################################
# https://patorjk.com/software/taag/#p=display&h=2&v=2&f=Small&t=TEST

# compares the result directory from a suite run, with the expected result directory (ignoring some run-specific aspects)
rescomp: install
	@cd $(does_config_dir) && \
	poetry run pytest $(PWD)/doespy -q -k 'test_does_results' -s --suite $(suite) --id $(id)



# Uses GNU parallel to execute the tests:
testid?=$(epoch)
does_test_run_dir=$(DOES_PROJECT_DIR)/doe-suite-tests/$@_$(testid)
PARGS = --progress --jobs 4 --delay 8s --joblog $(does_test_run_dir)/progress.log --results $(does_test_run_dir)/
PARALLEL = mkdir -p /$(does_test_run_dir) && parallel $(PARGS)
E2ETEST = echo "Running doe-suite e2e test: \n  cloud= $${TEST_CLOUD}\n  suites= $${TEST_SUITES}\n  results= $(does_test_run_dir) \n"; $(PARALLEL) make test-{} cloud=$${TEST_CLOUD} ::: $${TEST_SUITES} ; cat $(does_test_run_dir)/progress.log

docker-minimal-test:
	@TEST_SUITES="example01-minimal example02-single"; TEST_CLOUD="docker" ;\
	$(E2ETEST)

docker-mini-test:
	@TEST_SUITES="example01-minimal example02-single example05-complex"; TEST_CLOUD="docker" ;\
	$(E2ETEST)

docker-test:
	@TEST_SUITES="example01-minimal example02-single example03-format example04-multi example06-vars example07-etl example08-superetl example05-complex"; TEST_CLOUD="docker" ;\
	$(E2ETEST)

aws-mini-test:
	@TEST_SUITES="example01-minimal example02-single example05-complex"; TEST_CLOUD="aws" ;\
	$(E2ETEST)

aws-test:
	@TEST_SUITES="example01-minimal example02-single example03-format example04-multi example05-complex example06-vars example07-etl example08-superetl"; TEST_CLOUD="aws" ;\
	$(E2ETEST)

euler-mini-test:
	@TEST_SUITES="example01-minimal example02-single"; TEST_CLOUD="euler" ;\
	$(E2ETEST)

euler-test:
	@TEST_SUITES="example01-minimal example02-single example03-format example06-vars example07-etl example08-superetl"; TEST_CLOUD="euler" ;\
	$(E2ETEST)


# runs the suite and then compares the results
test-%:
	@$(MAKE) run suite=$* id=new
	@$(MAKE) rescomp suite=$* id=last


# convert a results dir to the expected results dir
convert-to-expected:
	@echo -n "Are you sure to make the results in $(does_results_dir)/$(suite)_$(id) to the expected results of the suite? [y/N] " && read ans && [ $${ans:-N} = y ]
	cd $(does_results_dir)/$(suite)_$(id) && \
	find . -type f -exec sed -i 's/$(id)/$$expected/g' {} +
	mv $(does_results_dir)/$(suite)_$(id) $(does_results_dir)/$(suite)_\$$expected


#################################
#   ___  ___ ___ ___ ___ _  _
# |   \| __/ __|_ _/ __| \| |
# | |) | _|\__ \| | (_ | .` |
# |___/|___|___/___\___|_|\_|
#
#################################

design: install-silent
	@cd $(does_config_dir) && \
	poetry run python $(PWD)/doespy/doespy/design/validate_extend.py --suite $(suite) --ignore-undefined-vars


design-validate: install-silent
	@cd $(does_config_dir) && \
	poetry run python $(PWD)/doespy/doespy/design/validate_extend.py --suite $(suite) --ignore-undefined-vars --only-validate


#################################
#  ___   ___   ___ ___
# |   \ / _ \ / __/ __|
# | |) | (_) | (__\__ \
# |___/ \___/ \___|___/
#
#################################

docs-build: install
	@cd doespy && \
	poetry install && \
	poetry run make html -C ../docs

docs: docs-build
	@open docs/build/html/index.html
