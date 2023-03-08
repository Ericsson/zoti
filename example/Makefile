############################################################################
## Testing provided variables and environment
############################################################################

ifndef APP
$(error "APP variable not set. Run the make command with APP in [$(shell ls -I kernels apps)]")
endif

include apps/$(APP)/Makefile.in

ifndef MAIN
$(error "MAIN not loaded from apps/$(APP)/Makefile.in")
endif

ifndef NODES
$(error "NODES not loaded from apps/$(APP)/Makefile.in")
endif


############################################################################
## Setting path variables
############################################################################

APP_PATH	= apps/$(APP)
SCRIPT_PATH 	= scripts
GRAPH_LIB	= $(APP_PATH) graphlib
TYPE_LIB	= typelib
TEMPLATE_LIB	= templatelib
GEN_PATH	= gen/$(APP)
GEN_GRAPH_PATH	= $(GEN_PATH)/graph
GEN_TYPES_PATH	= $(GEN_PATH)/types
GEN_SPEC_PATH	= $(GEN_PATH)/genspec
GEN_CODE_PATH	= $(GEN_PATH)/code
GEN_TRANS_PATH	= $(GEN_PATH)/trans_dbg
GEN_PATHS 	= $(GEN_PATH) $(GEN_GRAPH_PATH) $(GEN_TYPES_PATH) $(GEN_SPEC_PATH) $(GEN_CODE_PATH) $(GEN_TRANS_PATH)

############################################################################
## Finding sources and setting targets
############################################################################

APP_SRCS 	:= $(shell find $(APP_PATH) -name '*.zog')
NATIVE_SRCS 	:= $(shell find apps -name '*.dfc') 
TYPE_SRCS 	:= $(sort $(shell find $(TYPE_LIB) -name '*.ftn')) # TODO: better way for deps

GRAPH_IN 	:= $(GEN_GRAPH_PATH)/$(MAIN).raw.yaml
TYPES_IN 	:= $(patsubst $(TYPE_LIB)/%.ftn, $(GEN_TYPES_PATH)/%.yaml, $(TYPE_SRCS))
GENSPECS	:= $(patsubst %, $(GEN_SPEC_PATH)/%.zoc, $(NODES))
GEN_CODE	:= $(patsubst $(GEN_SPEC_PATH)/%.zoc, $(GEN_CODE_PATH)/%.c, $(GENSPECS))

############################################################################
## Main rules
############################################################################

all: graph types genspecs code

graph: $(GEN_GRAPH_PATH) $(GRAPH_IN)

types: $(GEN_TYPES_PATH) $(TYPES_IN)

genspecs: $(GEN_CODE_PATH) $(GEN_SPEC_PATH) $(GEN_TRANS_PATH) $(GENSPECS)

code: $(GEN_CODE_PATH) $(GEN_CODE)

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
	python -m zoti_yaml --verbose --pathvar $(GRAPH_LIB) -s graph \
		-o $(@D)/inter.yaml -- $(MAIN) 
	python -m zoti_graph --verbose --dump-graph --dump-tree --dump-out $(GEN_GRAPH_PATH)\
		-o $@ -i $(@D)/inter.yaml
else          # normal rule: pipe result of zoti-yaml to zoti-graph as JSON
	python -m zoti_yaml --pathvar $(GRAPH_LIB) -s graph -- $(MAIN) | python -m zoti_graph -o $@
endif

## types: ##
# Parse the FTN sources and dump zoti-yaml-enhanced structure as YAML files
$(GEN_TYPES_PATH)/%.yaml: $(TYPE_LIB)/%.ftn
	python -m zoti_ftn parse $< | python -m zoti_yaml --pathvar $(GEN_TYPES_PATH) -s ftn -o $@

## genspecs: ##
# Transform the previously generated representations into a genspec for each target node
$(GENSPECS): $(GRAPH_IN) $(TYPES_IN)
ifdef DEBUG   # debug rule: dump intermediate graphs for each transformation
	python scripts/unix_c/g2b.py --verbose --debug -p $(GEN_TRANS_PATH) \
		-g $(GRAPH_IN) -o $(GEN_SPEC_PATH) -c $(GEN_CODE_PATH) -f $(TYPES_IN) 
else          # normal rule: just generate genspec
	python scripts/unix_c/g2b.py \
		 -o $(GEN_SPEC_PATH) -g $(GRAPH_IN) -c $(GEN_CODE_PATH) -f $(TYPES_IN) 
endif

## code: ##
# Generate C code files for each genspec from the previous step
$(GEN_CODE_PATH)/%.c: $(GEN_SPEC_PATH)/%.zoc
ifdef DEBUG   # debug rule: dump intermediate graphs for each transformation
	python -m zoti_yaml --verbose -s gen --pathvar=$(GEN_SPEC_PATH) \
		-o $(basename $(@)).yaml -- $*
	python -m zoti_gen --verbose --dump-graph=$(GEN_DEBUG_PATH) --lib=$(TEMPLATE_LIB) \
		--deps=$(basename $<).deps.json -i $(basename $(@)).yaml -o $@ $*
else          # normal rule: pipe result of zoti-yaml to zoti-gen as JSON
	python -m zoti_yaml --pathvar $(GEN_SPEC_PATH) -s gen -- $* | \
		python -m zoti_gen --deps=$(basename $<).deps.json -o $@ $*
endif
	clang-format --style="{SortIncludes: false}" -i $@
	python scripts/unix_c/postproc.py -d $(basename $<).deps.json -f $@
