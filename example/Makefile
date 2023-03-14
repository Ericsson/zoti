 ifeq (, $(shell which pipenv))
 $(error "pipenv not installed, Check README to install dependencies.")
 endif

TARGET_LIB	:= targetlib
ZOTI_SCRIPTS 	:= zoti-scripts
GEN_PATH	:= gen

build:
	$(MAKE) APP=$(APP) -C $(ZOTI_SCRIPTS)

debug:
	$(MAKE) APP=$(APP) DEBUG=1 -C $(ZOTI_SCRIPTS)

prepare:
	$(MAKE) -C $(TARGET_LIB) clean
	$(MAKE) -C $(TARGET_LIB) all
	$(MAKE) -C $(TARGET_LIB) install
	cd $(ZOTI_SCRIPTS) && pipenv install

clean:
	rm -rf $(GEN_PATH)/*

clean-all: clean
	$(MAKE) -C $(TARGET_LIB) clean
	rm -rf prebuilt
