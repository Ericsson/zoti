 ifeq (, $(shell which pipenv))
 $(error "pipenv not installed, Check README to install dependencies.")
 endif

TOPDIR		:= $(shell pwd)
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

download start stop cfg run traffic trig stats agents:
	$(MAKE) GEN_DIR=$(TOPDIR)/$(GEN_PATH)/$(APP) -C $(DEPLOY_SCRIPTS) $@

define make-build-tgt
.PHONY: build-$1
build-$1:
	$(MAKE) APP=$1 -C $(ZOTI_SCRIPTS)
endef

define make-debug-tgt
.PHONY: debug-$1
debug-$1:
	$(MAKE) APP=$1 DEBUG=1 -C $(ZOTI_SCRIPTS)
endef

$(foreach tc,$(APP_LIST),$(eval $(call make-build-tgt,$(tc))))
$(foreach tc,$(APP_LIST),$(eval $(call make-debug-tgt,$(tc))))
