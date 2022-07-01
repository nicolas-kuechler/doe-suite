does_config_dir=$(DOES_PROJECT_DIR)/does_config
does_results_dir=$(DOES_PROJECT_DIR)/does_results

DOES_CLOUD?=aws
cloud?=$(DOES_CLOUD) # env variable with default (aws)


DOES_CLOUD_STATE?=terminate
state?=$(DOES_CLOUD_STATE) # env variable with default (terminate)

# add prefix if defined for playbook run cmd
ifdef expfilter
	myexpfilter='expfilter=$(expfilter)'
endif

# TODO [nku] would it be possible if suite not defined and required to show available suites and take number input?
ifdef suite
	mysuite=--suite $(suite)
endif

ifdef id
	myid=--id $(id)
endif

# on `make` and `make help` list all targets with information
help:
	@echo 'Running Experiments'
	@echo '  make run suite=<SUITE> id=new                       - run the experiments in the suite'
	@echo '  make run suite=<SUITE> id=<ID>                      - continue with the experiments in the suite with <ID> (often id=last)'
	@echo '  make run suite=<SUITE> id=<ID> cloud=<CLOUD>        - run suite on non-default cloud ([aws], euler)'
	@echo '  make run suite=<SUITE> id=<ID> expfilter=<REGEX>    - run only subset of experiments in suite where name matches the <REGEX>'
	@echo 'Clean'
	@echo '  make clean                                          - terminate running cloud instances belonging to the project and local cleanup'
	@echo '  make clean-result                                   - delete all results in does_results except for one suite run per suite (the last complete)'
	@echo 'Running ETL'
	@echo '  make etl suite=<SUITE> id=<ID>                      - run the etl pipeline of the suite (locally) to process results (often id=last)'
	@echo '  make etl-all                                        - run etl pipelines of all results'
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
	@echo '  make new                                            - initialize does_config from a template'
	@echo 'Running Tests'
	@echo '  make test                                           - running all suites sequentially and comparing results to expected'
	@echo '  make etl-test-all                                   - re-run all etl pipelines and compare results to current state (useful after update of etl step)'

# TODO: add super etl + clean commands
# TODO: extend run commands with state (if available)

#################################
#  ___ ___ _____ _   _ ___
# / __| __|_   _| | | | _ \
# \__ \ _|  | | | |_| |  _/
# |___/___| |_|  \___/|_|
#
#################################
# https://patorjk.com/software/taag/#p=display&h=2&v=2&f=Small&t=SETUP

# initialize a does_config from cookiecutter template (use defaults + ask user for inputs)
new:
	@if [ ! -f $(does_config_dir)/pyproject.toml ]; then \
		cookiecutter cookiecutter-does_config -o $(DOES_PROJECT_DIR); \
	fi

# depending on`cloud` variable, check if connection can be established
cloud-check:
	@if [ $(cloud) = aws ]; then aws sts get-caller-identity > /dev/null || aws configure; fi
	@if [ $(cloud) = euler ]; then timeout 1 ping -c 1 login.euler.ethz.ch > /dev/null || echo "\nCannot reach login.euler.ethz.ch, are you connected to the ETHZ network, e.g., via VPN?" && exit 1; fi

# install dependenicies to ensure that suites can be run + etl
install: new
	@cd $(does_config_dir) && \
	poetry install && \
	poetry run ansible-galaxy install -r $(PWD)/requirements-collections.yml


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
	poetry run ansible-playbook $(PWD)/src/experiment-suite.yml -e "suite=$(suite) id=$(id) cloud=$(cloud) $(myexpfilter)"

# TODO [nku] integrate them into run target when they are available
#run2 :
#	@echo "suite=$(suite) id=$(id) cloud=$(cloud)   state=$(state)   $(myexpfilter)"
#
#run-keep: state=keep
#run-keep: run2
#
#run-stop: state=stop
#run-stop: run2
#
#run-terminate: state=terminate
#run-terminate: run2


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

# run etl pipelines for all available results
etl-all: install
	@cd $(does_config_dir) && \
	poetry run python $(PWD)/doespy/doespy/etl/etl.py --all

# TODO: define running the super etl with its arguments
etl-super: install
	@cd $(does_config_dir) && \

# delete etl results for a specific `suite` and `id`  (can be regenerated with `make etl suite=<SUITE> id=<ID>`)
etl-clean:
	@cd $(does_config_dir) && \
	poetry run python $(PWD)/doespy/doespy/etl/etl_clean.py --suite $(suite) --id $(id)

# delete all etl results  (can be regenerated with `make etl-all`)
etl-clean-all:
	@cd $(does_config_dir) && \
	poetry run python $(PWD)/doespy/doespy/etl/etl_clean.py --all

# reruns all etl pipelines of all suite runs and compares the results
#   -> can be used to check that a change in an ETL step did not break another earlier suite
etl-test-all:
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
clean-result-incomplete:
	@echo -n "Are you sure to delete all the incomplete results in $(does_results_dir)? [y/N] " && read ans && [ $${ans:-N} = y ]
	@cd $(does_config_dir) && \
	poetry run python $(PWD)/doespy/doespy/result_clean.py --incomplete

# only keep one suite run per suite (the last complete)
clean-result:
	@echo -n "Are you sure to delete all the results in $(does_results_dir) except for the ones with the highest id? [y/N] " && read ans && [ $${ans:-N} = y ]
	@cd $(does_config_dir) && \
	poetry run python $(PWD)/doespy/doespy/result_clean.py --keeplast

clean-cloud :
	echo execute command to clean (terminate) the cloud

clean: clean-local-py clean-cloud


#################################
#  ___ _  _ ___ ___
# |_ _| \| | __/ _ \
#  | || .` | _| (_) |
# |___|_|\_|_| \___/
#
#################################
# https://patorjk.com/software/taag/#p=display&h=2&v=2&f=Small&t=INFO

# list infos about the does_config (config + designs)
info:
	@cd $(does_config_dir) && \
	poetry run python $(PWD)/doespy/doespy/info.py

# show status info of a suite (how much progress)
status:
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


rescomp:
	@cd $(does_config_dir) && \
	poetry run pytest $(PWD)/doespy -q -k 'test_does_results' -s --suite $(suite) --id $(id)

# matches
test-%:
	@make run suite=$* id=new
	@make rescomp suite=$* id=last

# runs the listed suites and compares the result with the expected result under `does_results`
test: test-example01-minimal test-example02-single


#################################
#   ___  ___ ___ ___ ___ _  _
# |   \| __/ __|_ _/ __| \| |
# | |) | _|\__ \| | (_ | .` |
# |___/|___|___/___\___|_|\_|
#
#################################

design:
	@cd $(does_config_dir) && \
	poetry run python $(PWD)/doespy/doespy/design/validate_extend.py --suite $(suite) --ignore-undefined-vars


design-validate:
	@cd $(does_config_dir) && \
	poetry run python $(PWD)/doespy/doespy/design/validate_extend.py --suite $(suite) --ignore-undefined-vars --only-validate
