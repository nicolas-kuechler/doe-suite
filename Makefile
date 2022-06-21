does_config_dir=$(DOES_PROJECT_DIR)/does_config


DOES_CLOUD?=aws
cloud?=$(DOES_CLOUD) # env variable with default (aws)


DOES_CLOUD_STATE?=terminate
state?=$(DOES_CLOUD_STATE) # env variable with default (terminate)



# add prefix if defined for playbook run cmd
ifdef expfilter
	myexpfilter='expfilter=$(expfilter)'
endif

ifdef suite
	mysuite=--suite $(suite)
endif

ifdef id
	myid=--id $(id)
endif
# TODO: potentially check for pre-requesits (poetry, cookiecutter-> only if new)

new:
	@if [ ! -f $(does_config_dir)/pyproject.toml ]; then \
		cookiecutter cookiecutter-does_config -o $(DOES_PROJECT_DIR); \
	fi

install: new
	@cd $(does_config_dir) && \
	poetry install && \
	poetry run ansible-galaxy install -r $(PWD)/requirements-collections.yml

.PHONY: run
run: install
	@cd $(does_config_dir) && \
	ANSIBLE_CONFIG=$(PWD)/ansible.cfg \
	poetry run ansible-playbook $(PWD)/src/experiment-suite.yml -e "suite=$(suite) id=$(id) $(myexpfilter)"

# TODO [nku] integrate them into run target when they are available
run2 :
	@echo "suite=$(suite) id=$(id) cloud=$(cloud)   state=$(state)   $(myexpfilter)"

run-keep: state=keep
run-keep: run2

run-stop: state=stop
run-stop: run2

run-terminate: state=terminate
run-terminate: run2

.PHONY: etl
etl: install
	@cd $(does_config_dir) && \
	poetry run python $(PWD)/doespy/doespy/etl/etl.py --suite $(suite) --id $(id)

# TODO: define running the super etl with its arguments
etl-super: install
	@cd $(does_config_dir) && \

# TODO: setup clean commands local -> delete python cache files + results etc.
clean-cloud :
	echo hello

# TODO: idea is to have these as part of install depending on which cloud is used ensure that it's setup
cloud-setup:
	@if [ $(cloud) = aws ]; then aws sts get-caller-identity > /dev/null || aws configure; fi
	@if [ $(cloud) = leonhard ]; then echo "here would do leonhard setup"; fi




info:
	@cd $(does_config_dir) && \
	poetry run python $(PWD)/doespy/doespy/info.py

status:
	@cd $(does_config_dir) && \
	poetry run python $(PWD)/doespy/doespy/status.py $(mysuite) $(myid)

# make install
# -> ensure env variables are set
# -> ensure aws cli v2 installed + poetry installed
# -> configure ssh + ssh-agent
# -> aws configure
# -> poetry install
# -> install ansible-galaxy collections


# make run suite=example id=new/last/<id>
# make run suite=example id=new cloud=aws

# cloud could also be via ENV_VARIABLE

# make run suite=example id=new cloud=aws clean=keep/stop/[TERMINATE]

# make run suite=example id=new [cloud=aws]   -> defaults to run-terminate
# make run-keep suite=example id=new [cloud=aws]
# make run-stop suite=example id=new [cloud=aws]
# make run-terminate suite=example id=new [cloud=aws]

# make run suite=example id=new expfilter=XYZ

# make reproduce suite=example id=12345  -> uses version of the code + design + etl config from job

# make clean-all -> both local and cloud
# make clean-local -> remove results
# make clean-cloud -> ensure cloud setup terminated
# make clean-cloud stop/[TERMINATE]-> ensure cloud setup terminated
# make clean-cloud-stop
# make clean-cloud-terminate


# make etl suite=example id=new
# make etl-super config=<path>   -> other params, load defaults from super etl config?


rescomp:
	@cd $(does_config_dir) && \
	poetry run pytest $(PWD)/doespy -q -s --suite $(suite) --id $(id)

# matches
test-%:
	@make run suite=$* id=new
	@make rescomp suite=$* id=last

# TODO: can add other examples here that we want to test
test: test-example01-minimal test-example02-single
