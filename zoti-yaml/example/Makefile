MAIN		= ProdCons
NODES		= Src Proc Sink DFL_counter_stat

APP_PATH	= app
SCRIPT_PATH 	= scripts
GRAPH_LIB	= graphlib
TYPE_LIB	= typelib
TEMPLATE_LIB	= templatelib
CONF_FILE	= zoticonf.toml
GEN_PATH	= gen

APP_SRCS 	:= $(shell find $(APP_PATH) -name '*.zog') 
NATIVE_SRCS 	:= $(shell find $(APP_PATH) -name '*.dfc') 
TYPE_SRCS 	:= $(sort $(shell find $(TYPE_PATH) -name '*.ftn')) # TODO: better way for deps

GEN_GRAPH_PATH	:= $(GEN_PATH)/graph
GEN_TYPES_PATH	:= $(GEN_PATH)/types
GEN_SPEC_PATH	:= $(GEN_PATH)/genspec
GEN_CODE_PATH	:= $(GEN_PATH)/code
GEN_PATHS 	:= $(GEN_PATH) $(GEN_GRAPH_PATH) $(GEN_TYPES_PATH) $(GEN_SPEC_PATH) $(GEN_CODE_PATH)

GRAPH_IN 	:= $(GEN_GRAPH_PATH)/$(MAIN).raw.yaml
TYPES_IN 	:= $(patsubst ./$(TYPE_LIB)/%.ftn, ./$(GEN_TYPES_PATH)/%.yaml, $(TYPE_SRCS))
GENSPECS	:= $(patsubst %, $(GEN_SPEC_PATH)/%.zoc, $(NODES))
GEN_CODE	:= $(patsubst $(GEN_SPEC_PATH)/%.zoc, $(GEN_CODE_PATH)/%.c, $(GENSPECS))


all: graph types genspecs code

graph: $(GEN_GRAPH_PATH) $(GRAPH_IN)

types: $(GEN_TYPES_PATH) $(TYPES_IN)

genspecs: $(GEN_CODE_PATH) $(GEN_SPEC_PATH) $(GENSPECS)

code: $(GEN_CODE_PATH) $(GEN_CODE)

clean:
	rm -f $(GRAPH_IN) $(TYPES_IN) $(GENSPECS)
	rm -f $(GEN_CODE_PATH)/* $(GEN_SPEC_PATH)/*.deps.json

### MAKE RULES ###

$(GRAPH_IN): $(NATIVE_SRCS) $(APP_SRCS)
	python -m zoti_yaml -s graph -- $(MAIN) | python -m zoti_graph -o $@

$(GEN_TYPES_PATH)/%.yaml: $(TYPE_LIB)/%.ftn
	python -m zoti_ftn parse $< | python -m zoti_yaml -s ftn_dbg -o $@

$(GENSPECS): $(GRAPH_IN) $(TYPES_IN)
	python scripts/unix_c/g2b.py -o $(GEN_SPEC_PATH) -c $(GEN_CODE_PATH) -g $(GRAPH_IN) \
		-f $(TYPES_IN) 

$(GEN_CODE_PATH)/%.c: $(GEN_SPEC_PATH)/%.zoc
	python -m zoti_yaml -s gen -- $* | \
		python -m zoti_gen --deps=$(basename $<).deps.json -o $@ $*
	clang-format --style="{SortIncludes: false}" -i $@
	python scripts/unix_c/postproc.py -d $(basename $<).deps.json -f $@

### MAKE DIRECTORIES ###

$(GEN_PATHS):
	mkdir -p $@
