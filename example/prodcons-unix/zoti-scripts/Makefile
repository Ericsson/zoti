############################################################################
## Tool invocation commands
############################################################################

PYTHON		:= pipenv run python
ZOTI_YAML	:= $(PYTHON) -m zoti_yaml
ZOTI_GRAPH	:= $(PYTHON) -m zoti_graph
ZOTI_FTN	:= $(PYTHON) -m zoti_ftn
ZOTI_GEN	:= $(PYTHON) -m zoti_gen
C_FORMAT	:= clang-format
CC 		:= gcc

define check-dep
ifeq (, $$(shell which $1))
$$(error "$1 is not installed, Check README to install dependencies.")
endif
endef
$(foreach dep, python3 pipenv $(C_FORMAT) $(CC),$(eval $(call check-dep,$(dep))))

ifeq ($(wildcard ../target/prebuilt/x86_64/*),)
$(error "Did not find x86_64 prebuild libraries. Consider running 'make prepare'.")
endif

############################################################################
## Setting path variables
############################################################################

# base paths
HUB		= ..
TC_PATH		= $(HUB)/apps/$(TC)
SCRIPT_PATH 	= .

#library paths
GRAPH_LIB	= $(TC_PATH) $(HUB)/graphlib
TYPE_LIB	= $(HUB)/typelib
TEMPLATE_LIB	= $(HUB)/templatelib

# target platform libraries
PREBUILT_PATH	= $(HUB)/target/prebuilt/x86_64
PREBUILT_INCL	= $(PREBUILT_PATH)/include
PREBUILT_LIB	= $(PREBUILT_PATH)/lib

# generated artifacts paths
GEN_PATH	= $(HUB)/gen/$(TC)
GEN_IN_PATH	= $(GEN_PATH)/tran_in
GEN_OUT_PATH	= $(GEN_PATH)/tran_out
GEN_PLOT_PATH	= $(GEN_PATH)/plots
GEN_CODE_PATH	= $(GEN_PATH)/code
GEN_BIN_PATH	= $(GEN_PATH)/bin/x86_64
GEN_PATHS 	= $(GEN_IN_PATH) $(GEN_OUT_PATH) $(GEN_PLOT_PATH) $(GEN_CODE_PATH) $(GEN_BIN_PATH)

############################################################################
## Testing variables and loading environment
############################################################################

ifndef TC
$(error TC variable not set. Set TC to one of [$(shell ls -I kernels $(HUB)/apps)])
endif

ifndef DEBUG
$(info INFO: Running in normal mode. For debug mode define the DEBUG variable.)
endif

include $(TC_PATH)/Makefile.in

ifndef MAIN
$(error MAIN not loaded from app $(TC)/Makefile.in)
endif

ifndef NODES
$(error NODES not loaded from app $(TC)/Makefile.in)
endif

############################################################################
## Finding sources and setting targets
############################################################################

TC_SRCS 	:= $(shell find $(TC_PATH) -name '*.zog')
GLIB_SRCS 	:= $(shell find $(HUB)/graphlib -name '*.zog')
NATIVE_SRCS 	:= $(shell find $(HUB)/apps -name '*.dfc') 
TYPE_SRCS 	:= $(shell find $(TYPE_LIB) -name '*.ftn')

GYAML_IN 	:= $(GEN_IN_PATH)/$(MAIN)_preparse.yaml
GRAPH_IN 	:= $(GEN_IN_PATH)/$(MAIN).raw.yaml
TYPES_IN 	:= $(GEN_IN_PATH)/types.yaml
GEN_SPEC	:= $(patsubst %, $(GEN_OUT_PATH)/%.zoc, $(NODES))
GEN_TYPE	:= $(GEN_CODE_PATH)/types.h
GEN_DEPL	:= $(GEN_OUT_PATH)/$(MAIN)-depl.dfg
GEN_CODE	:= $(patsubst $(GEN_OUT_PATH)/%.zoc, $(GEN_CODE_PATH)/%.c, $(GEN_SPEC))
GEN_OBJS	:= $(patsubst $(GEN_CODE_PATH)/%.c, $(GEN_CODE_PATH)/%.o, $(GEN_CODE))
GEN_BINS	:= $(patsubst $(GEN_CODE_PATH)/%.o, $(GEN_BIN_PATH)/%.bin, $(GEN_OBJS))

############################################################################
## C compilation flags
############################################################################

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

############################################################################
## Main rules
############################################################################


all: graph types genspecs code bins

graph: $(GEN_IN_PATH) $(GEN_PLOT_PATH) $(GRAPH_IN)

types: $(GEN_IN_PATH) $(TYPES_IN)

genspecs: $(GEN_CODE_PATH) $(GEN_OUT_PATH) $(GEN_PLOT_PATH) $(GEN_SPEC)

code: $(GEN_CODE_PATH) $(GEN_CODE)

bins: $(GEN_BIN_PATH) $(GEN_TYPE) $(GEN_OBJS) $(GEN_BINS)

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
$(GRAPH_IN): $(NATIVE_SRCS) $(TC_SRCS) $(GLIB_SRCS)
ifdef DEBUG   # debug rule: dump intermediate zoti-yaml format as YAML file
	$(ZOTI_YAML) --verbose --pathvar $(GRAPH_LIB) -s graph -o $(GYAML_IN) -- $(MAIN) 
	$(ZOTI_GRAPH) --verbose --dump-graph --dump-tree --dump-out $(GEN_PLOT_PATH)\
		-o $@ -i $(GYAML_IN)
else          # normal rule: pipe result of zoti-yaml to zoti-graph as JSON
	$(ZOTI_YAML) --pathvar $(GRAPH_LIB) -s graph -- $(MAIN) | $(ZOTI_GRAPH) -o $@
endif

## types: ##
$(TYPES_IN): $(TYPE_SRCS)
	$(ZOTI_FTN) -o $@ $^

## genspecs: ##
# Transform the previously generated representations into a genspec for each target node
$(GEN_SPEC) $(GEN_TYPE) $(GEN_DEPL): $(GRAPH_IN) $(TYPES_IN)
ifdef DEBUG   # debug rule: dump intermediate graphs for each transformation
	$(PYTHON) $(SCRIPT_PATH)/unix_c/graph2block.py --verbose --debug -p $(GEN_PLOT_PATH) \
		-g $(GRAPH_IN) -f $(TYPES_IN) -o $(GEN_OUT_PATH) \
		--typeshdr $(GEN_TYPE) --depl $(GEN_DEPL)
else          # normal rule: just generate genspec
	$(PYTHON) $(SCRIPT_PATH)/unix_c/graph2block.py \
		-g $(GRAPH_IN) -f $(TYPES_IN) -o $(GEN_OUT_PATH) \
		--typeshdr $(GEN_TYPE) --depl $(GEN_DEPL)
endif

## code: ##
# Generate C code files for each genspec from the previous step
$(GEN_CODE_PATH)/%.c: $(GEN_OUT_PATH)/%.zoc
ifdef DEBUG   # debug rule: dump intermediate graphs for each transformation
	$(ZOTI_YAML) --verbose -s gen --pathvar=$(GEN_OUT_PATH) -o $(basename $(<)).yaml -- $*
	$(ZOTI_GEN) --verbose --dump-graph=$(GEN_PLOT_PATH) --lib=$(TEMPLATE_LIB) \
		--deps=$(basename $<).deps.json -i $(basename $(<)).yaml -o $@ $*
else          # normal rule: pipe result of zoti-yaml to zoti-gen as JSON
	$(ZOTI_YAML) --pathvar $(GEN_OUT_PATH) -s gen -- $* | \
		$(ZOTI_GEN) --lib=$(TEMPLATE_LIB) --deps=$(basename $<).deps.json -o $@ $*
endif
	$(C_FORMAT) --style="{SortIncludes: false}" -i $@
	$(PYTHON) $(SCRIPT_PATH)/unix_c/postproc.py -d $(basename $<).deps.json -f $@


## bins: ##
$(GEN_CODE_PATH)/%.o: $(GEN_CODE_PATH)/%.c 
	$(CC) $(GENCFLAGS) $(INCLUDES) -c $< -o $@

$(GEN_BIN_PATH)/%.bin: $(GEN_CODE_PATH)/%.o
	$(CC) $(LINKFLAGS) $(INCLUDES) -o $@ $^ $(LIBS)
