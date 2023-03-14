############################################################################
## Tool invocation commands
############################################################################

 ifeq (, $(shell which clang-format))
 $(error "clang-format not installed, Consider installing it.")
 endif

ifeq ($(wildcard ../prebuilt/x86_64/*),)
$(error "Did not found x86_64 prebuild libraries. Consider running 'make prepare'.")
endif

PYTHON		= pipenv run python
ZOTI_YAML	= $(PYTHON) -m zoti_yaml
ZOTI_GRAPH	= $(PYTHON) -m zoti_graph
ZOTI_FTN	= $(PYTHON) -m zoti_ftn
ZOTI_GEN	= $(PYTHON) -m zoti_gen
C_FORMAT	= clang-format

############################################################################
## Setting path variables
############################################################################

APP_PATH	= ../apps/$(APP)
SCRIPT_PATH 	= .
GRAPH_LIB	= $(APP_PATH) ../graphlib
TYPE_LIB	= ../typelib
TEMPLATE_LIB	= ../templatelib
PREBUILT_PATH	= ../prebuilt/x86_64
PREBUILT_INCL	= $(PREBUILT_PATH)/include
PREBUILT_LIB	= $(PREBUILT_PATH)/lib
GEN_PATH	= ../gen/$(APP)
GEN_GRAPH_PATH	= $(GEN_PATH)/graph
GEN_TYPES_PATH	= $(GEN_PATH)/types
GEN_SPEC_PATH	= $(GEN_PATH)/genspec
GEN_TRANS_PATH	= $(GEN_PATH)/trans_dbg
GEN_CODE_PATH	= $(GEN_PATH)/code
GEN_BIN_PATH	= $(GEN_PATH)/bin
GEN_PATHS 	= $(GEN_PATH) $(GEN_GRAPH_PATH) $(GEN_TYPES_PATH) $(GEN_SPEC_PATH) $(GEN_CODE_PATH) $(GEN_TRANS_PATH) $(GEN_BIN_PATH)

############################################################################
## Testing variables and loading environment
############################################################################

ifndef APP
$(error APP variable not set. Set APP to one of [$(shell ls -I kernels ../apps)])
endif

ifndef DEBUG
$(info INFO: Running in normal mode. For debug mode define the DEBUG variable.)
endif

include $(APP_PATH)/Makefile.in

ifndef MAIN
$(error MAIN not loaded from app $(APP)/Makefile.in)
endif

ifndef NODES
$(error NODES not loaded from app $(APP)/Makefile.in)
endif

############################################################################
## Finding sources and setting targets
############################################################################

APP_SRCS 	:= $(shell find $(APP_PATH) -name '*.zog')
NATIVE_SRCS 	:= $(shell find apps -name '*.dfc') 
TYPE_SRCS 	:= $(sort $(shell find $(TYPE_LIB) -name '*.ftn')) # TODO: better way for deps

GRAPH_IN 	:= $(GEN_GRAPH_PATH)/$(MAIN).raw.yaml
TYPES_IN 	:= $(patsubst $(TYPE_LIB)/%.ftn, $(GEN_TYPES_PATH)/%.yaml, $(TYPE_SRCS))
GENSPECS	:= $(patsubst %, $(GEN_SPEC_PATH)/%.zoc, $(NODES))
GEN_TYPE_HDR	:= $(GEN_CODE_PATH)/types.h
GEN_CODE	:= $(patsubst $(GEN_SPEC_PATH)/%.zoc, $(GEN_CODE_PATH)/%.c, $(GENSPECS))
GEN_OBJS	:= $(patsubst $(GEN_CODE_PATH)/%.c, $(GEN_CODE_PATH)/%.o, $(GEN_CODE))
GEN_BINS	:= $(patsubst $(GEN_CODE_PATH)/%.o, $(GEN_BIN_PATH)/%.bin, $(GEN_OBJS))

############################################################################
## C compilation flags
############################################################################

CC := gcc
#OPT_CFLAGS := -O2

ifndef DEBUG
DBG_CFLAGS 	:= -g
else
DBG_CFLAGS	:= -g -DDFL_DEBUG_PRINT=$(DEBUG)
endif

CFLAGS 		:= -Wall $(DBG_CFLAGS) $(OPT_CFLAGS) -D_GNU_SOURCE
GENCFLAGS 	:= $(CFLAGS) -Wno-unused-function
LINKFLAGS 	:= $(CFLAGS)
#LINKFLAGS 	:= -static $(CFLAGS)
# LINKFLAGS 	:= $(CFLAGS) -Wl,-rpath $(PREBUILT_LIB)
INCLUDES 	:= -I$(GEN_CODE_PATH) -I$(PREBUILT_INCL)
LIBS 		:= -L$(PREBUILT_LIB) -ldflrtl -lm

$(info $(INCLUDES))

############################################################################
## Main rules
############################################################################

all: graph types genspecs code bins

graph: $(GEN_GRAPH_PATH) $(GRAPH_IN)

types: $(GEN_TYPES_PATH) $(TYPES_IN)

genspecs: $(GEN_CODE_PATH) $(GEN_SPEC_PATH) $(GEN_TRANS_PATH) $(GENSPECS)

code: $(GEN_CODE_PATH) $(GEN_CODE)

bins: $(GEN_BIN_PATH) $(GEN_TYPE_HDR) $(GEN_OBJS) $(GEN_BINS)

clean:
	rm -rf $(GEN_PATH)

############################################################################
## Target rules
############################################################################

## MAKE DIRECTORIES
$(GEN_PATHS):
	mkdir -p $@

## graph: ##
# Parse graph (project) input files and dumps a raw ZOTI-Graph object
$(GRAPH_IN): $(NATIVE_SRCS) $(APP_SRCS)
ifdef DEBUG   # debug rule: dump intermediate zoti-yaml format as YAML file
	$(ZOTI_YAML) --verbose --pathvar $(GRAPH_LIB) -s graph -o $(@D)/inter.yaml -- $(MAIN) 
	$(ZOTI_GRAPH) --verbose --dump-graph --dump-tree --dump-out $(GEN_GRAPH_PATH)\
		-o $@ -i $(@D)/inter.yaml
else          # normal rule: pipe result of zoti-yaml to zoti-graph as JSON
	$(ZOTI_YAML) --pathvar $(GRAPH_LIB) -s graph -- $(MAIN) | $(ZOTI_GRAPH) -o $@
endif

## types: ##
# Parse the FTN sources and dump zoti-yaml-enhanced structure as YAML files
$(GEN_TYPES_PATH)/%.yaml: $(TYPE_LIB)/%.ftn
	$(ZOTI_FTN) parse $< | $(ZOTI_YAML) --pathvar $(GEN_TYPES_PATH) -s ftn -o $@

## genspecs: ##
# Transform the previously generated representations into a genspec for each target node
$(GENSPECS) $(GEN_TYPE_HDR): $(GRAPH_IN) $(TYPES_IN)
ifdef DEBUG   # debug rule: dump intermediate graphs for each transformation
	$(PYTHON) $(SCRIPT_PATH)/unix_c/g2b.py --verbose --debug -p $(GEN_TRANS_PATH) \
		-g $(GRAPH_IN) -o $(GEN_SPEC_PATH) -c $(GEN_CODE_PATH) -f $(TYPES_IN) 
else          # normal rule: just generate genspec
	$(PYTHON) $(SCRIPT_PATH)/unix_c/g2b.py \
		 -o $(GEN_SPEC_PATH) -g $(GRAPH_IN) -c $(GEN_CODE_PATH) -f $(TYPES_IN) 
endif

## code: ##
# Generate C code files for each genspec from the previous step
$(GEN_CODE_PATH)/%.c: $(GEN_SPEC_PATH)/%.zoc
ifdef DEBUG   # debug rule: dump intermediate graphs for each transformation
	$(ZOTI_YAML) --verbose -s gen --pathvar=$(GEN_SPEC_PATH) -o $(basename $(@)).yaml -- $*
	$(ZOTI_GEN) --verbose --dump-graph=$(GEN_DEBUG_PATH) --lib=$(TEMPLATE_LIB) \
		--deps=$(basename $<).deps.json -i $(basename $(@)).yaml -o $@ $*
else          # normal rule: pipe result of zoti-yaml to zoti-gen as JSON
	$(ZOTI_YAML) --pathvar $(GEN_SPEC_PATH) -s gen -- $* | \
		$(ZOTI_GEN) --lib=$(TEMPLATE_LIB) --deps=$(basename $<).deps.json -o $@ $*
endif
	$(C_FORMAT) --style="{SortIncludes: false}" -i $@
	$(PYTHON) $(SCRIPT_PATH)/unix_c/postproc.py -d $(basename $<).deps.json -f $@


## bins: ##
$(GEN_CODE_PATH)/%.o: $(GEN_CODE_PATH)/%.c 
	$(CC) $(GENCFLAGS) $(INCLUDES) -c $< -o $@

$(GEN_BIN_PATH)/%.bin: $(GEN_CODE_PATH)/%.o
	$(CC) $(LINKFLAGS) $(INCLUDES) -o $@ $^ $(LIBS)
