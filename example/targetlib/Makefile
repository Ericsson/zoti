SHELL = /bin/sh

ifndef TOPDIR
  MKDIR:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
  TOPDIR:=$(shell dirname ${MKDIR})
endif

PREBUILT_DIR := $(TOPDIR)/prebuilt

BUILD_HOST_ARCH := $(shell uname -m)
ifndef BIN_TGT_ARCH
  BIN_TGT_ARCH := $(BUILD_HOST_ARCH)
endif
ifeq ($(BIN_TGT_ARCH),$(BUILD_HOST_ARCH))
  CC := gcc
else ifeq ($(BIN_TGT_ARCH),x86_64)
  CC := arm-linux-gnueabihf-gcc
else ifeq ($(BIN_TGT_ARCH),armv7l)
  CC := arm-linux-gnueabihf-gcc
else
  $(error Unsupported architecture '$(BIN_TGT_ARCH')
endif

TGT_ARCH_DIR := $(PREBUILT_DIR)/$(BIN_TGT_ARCH)
INCL_TGT_DIR := $(TGT_ARCH_DIR)/include
LIBS_TGT_DIR := $(TGT_ARCH_DIR)/lib

AR := ar
ARFLAGS := rcs
CP := cp -f

CFLAGS := -Wall -g -D_GNU_SOURCE -I$(INCL_TGT_DIR)

LIB := libdflrtl.a
OBJS := dfl_cfg.o dfl_evt.o
INCLUDES := dfl_cfg.h dfl_evt.h DFL_core.h DFL_util.h

INCL_INSTS := $(addprefix $(INCL_TGT_DIR)/,$(INCLUDES))
LIB_INST := $(addprefix $(LIBS_TGT_DIR)/,$(LIB))


.PHONY: all clean build

all: build

build: $(INCL_TGT_DIR) $(LIBS_TGT_DIR) $(LIB)

install: $(LIB_INST) $(INCL_INSTS)

$(LIB): $(OBJS)
	$(AR) $(ARFLAGS) $@ $^

$(INCL_TGT_DIR)/%: %
	$(CP) $< $@

$(LIBS_TGT_DIR)/%: %
	$(CP) $< $@

clean:
	-rm -rf *.o core *.core $(LIB)

dfl_cfg.o: dfl_cfg.h
dfl_evt.o: dfl_evt.h

%.o: %.c
	$(CC) $(CFLAGS) -c $<


$(INCL_TGT_DIR) $(LIBS_TGT_DIR):
	mkdir -p $@
