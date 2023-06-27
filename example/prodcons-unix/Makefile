ifeq (, $(shell which pipenv))
$(error "pipenv is not installed, Check README to install dependencies.")
endif

TC_LIST		:= $(shell ls -I kernels apps)
TARGET_C_LIB	:= target/c_lib
GEN_PATH	:= $(shell pwd)/gen
ZOTI_SCRIPTS 	:= zoti-scripts
DEPLOY_SCRIPTS	:= target/deploy-scripts

.PHONY: help debug prepare clean clean-all download start stop cfg run traffic trig stats agents

help:
	@echo 'Usage:'
	@echo '- First time setup                               "make prepare".'
	@echo ''
	@echo '- To build an example:'
	@echo '  - in normal mode do                            "make TC=<example> build".'
	@echo '  - in debug mode do                             "make TC=<example> debug".'
	@echo '  (Available examples are: [$(TC_LIST)] )'
	@echo ''
	@echo '- To start the platorm daemon processes          "make agents"'
	@echo ''
	@echo '- To run an example do the following (available examples above):'
	@echo '  - Download binaries to agent:                  "make TC=<example> download"'
	@echo '  - Start the binaries:                          "make TC=<example> start"'
	@echo '  - Configure the running nodes:                 "make TC=<example> cfg"'
	@echo '  - Send a trigger packet through:               "make trig"'
	@echo '  - Send some traffic (100000 trigger packets):  "make traffic"'
	@echo '  - Flush stats (if example contains counters):  "make stats"'
	@echo '  - To stop the nodes:                           "make TC=<example> stop"'
	@echo ''
	@echo '- To run download, start and cfg in one go do    "make TC=<example> run"'
	@echo ''
	@echo '- To clean the generated files do                "make clean"'
	@echo '- To clean everything including initial setup do "make clean-all"'

build:
	$(MAKE) TC=$(TC) -C $(ZOTI_SCRIPTS)

debug:
	$(MAKE) TC=$(TC) DEBUG=1 -C $(ZOTI_SCRIPTS)

prepare:
	$(MAKE) -C $(TARGET_C_LIB) clean
	$(MAKE) -C $(TARGET_C_LIB) all
	$(MAKE) -C $(TARGET_C_LIB) install
	cd $(ZOTI_SCRIPTS) && pipenv install

clean:
	rm -rf $(GEN_PATH)/*

clean-all: clean
	$(MAKE) -C $(TARGET_C_LIB) clean
	rm -rf target/prebuilt

download start stop cfg run traffic trig stats agents:
	$(MAKE) GEN_DIR=$(GEN_PATH)/$(TC) -C $(DEPLOY_SCRIPTS) $@

