 ifeq (, $(shell which pipenv))
 $(error "pipenv not installed, Check README to install dependencies.")
 endif

APP_PATH 	:= apps
APP_LIST	:= $(shell ls -I kernels $(APP_PATH))
TARGET_C_LIB	:= target/c_lib
ZOTI_SCRIPTS 	:= zoti-scripts
GEN_PATH	:= gen
DEPLOY_SCRIPTS	:= target/deploy-scripts

build:
	$(MAKE) APP=$(APP) -C $(ZOTI_SCRIPTS)

debug:
	$(MAKE) APP=$(APP) DEBUG=1 -C $(ZOTI_SCRIPTS)

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

download start stop: check-env
	$(DEPL) -F $(DEPL_FLOW) $(FLOW_IFLAGS) -B $(GEN_DIR) --$@

cfg: check-env
	$(SETUP) -F $(DEPL_FLOW) $(FLOW_IFLAGS) #--csv

traffic:
	misc/udpflood.sh -N trig -c 100000 -s 1

trig:
	misc/udpflood.sh -N trig -c 1 -s 1

stats:
	misc/udpflood.sh -N DFL-flush -c 1 -s 1

run: check-env
	$(MAKE) download
	$(MAKE) start
	sleep 1
	$(MAKE) cfg


define make-build-tgt
.PHONY: build-$1
build-$1:
	$(MAKE) APP=$1 -C $(ZOTI_SCRIPTS)
endef

$(foreach tc,$(APP_LIST),$(eval $(call make-build-tgt,$(tc))))
