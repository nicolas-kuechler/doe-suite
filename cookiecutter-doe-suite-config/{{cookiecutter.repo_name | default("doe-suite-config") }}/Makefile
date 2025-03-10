run?=0
rep?=0
file?=stdout.log
exp?=$$(ls -d */ | head -n 1)


help-custom:
	@echo 'Euler Progress Update'
	@echo '  make peek suite=<SUITE> id=<ID>     - peek at a file on euler'
	@echo '            [file=<FILE>]                 select file (default: stdout.log)'
	@echo '            [exp=<EXP>]                   select experiment (default: first)'
	@echo '            [run=<RUN>]                   select run (default: 0)'

# Example: for the euler cloud peek at results.
peek:
	@ssh euler.ethz.ch 'cd ~/doe-suite-results/$(suite)_$(suite_id) && cd $(exp) && less run_$(run)/rep_$(rep)/results/$(file)'