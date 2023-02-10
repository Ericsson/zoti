TOOLS = zoti-yaml zoti-graph # zoti-ftn zoti-gen zoti-tran

HUB = ..

DOCS = $(shell find $(HUB) -wholename "**/docs/**/*.md") 

TOOL_ROOTS	:= $(patsubst %, $(HUB)/%, $(TOOLS))
TOOL_BUILDS	:= $(patsubst %, %/dist, $(TOOL_ROOTS))
TOOL_DOCS	:= $(patsubst %, %/docs/build, $(TOOL_ROOTS))

all: dists sphinx

# BUILD SDISTS

dists: $(TOOL_BUILDS)

../%/dist: ../%/pyproject.toml
	cd $(@D); pipenv run python -m build 

cleandists:
	rm -rf $(TOOL_BUILDS)

# BUILD SPHINX

sphinx: $(TOOL_DOCS) $(TOOLS) 

../%/docs/build: FORCE
	[ -d $(@D) ] && (cd $(@D); pipenv run sphinx-build -M html source build) || echo 

%: ../%/docs/build/html
	rm -rf $@; cp -rf $< $@

cleansphinx:
	rm -rf $(TOOLS)

.PHONY: dists cleandists sphinx cleansphinx

FORCE:
