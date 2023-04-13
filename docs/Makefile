TOOLS = zoti-yaml zoti-graph zoti-tran zoti-gen

HUB = ..

DOCS = $(shell find $(HUB) -wholename "**/docs/**/*.md") 

TOOL_ROOTS	:= $(patsubst %, $(HUB)/%, $(TOOLS))
TOOL_BUILDS	:= $(patsubst %, %/dist, $(TOOL_ROOTS))
TOOL_DOCS	:= $(patsubst %, %/docs/build, $(TOOL_ROOTS))

EXAMPLES = prod-cons

all: dists sphinx examples

clean: cleandists cleansphinx cleanexamples

serve:
	bundle exec jekyll serve --baseurl='/zoti'

# BUILD SDISTS

dists: $(TOOL_BUILDS)

../%/dist: ../%/pyproject.toml
	cd $(@D); pipenv --venv \
		&& pipenv run python -m build \
		|| (pipenv install --dev; pipenv run python -m build) 

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

# EXAMPLES

examples: examples-prod-cons

cleanexamples: cleanexamples-prod-cons

define make-examples
EXAMPLE_PATH_$1 := example/$1
EXAMPLE_SRCS_$1	:= $(shell find $(HUB)/example/$1/docs -name "*.md")
EXAMPLE_DOCS_$1	:= $$(patsubst ../example/$1/docs/%.md, example/$1/%.md, $$(EXAMPLE_SRCS_$1))
EXAMPLE_IMGS_$1	:= $(shell find $(HUB)/example/$1/docs -name "*.drawio")
EXAMPLE_TGTI_$1	:= $$(patsubst ../example/$1/docs/%.drawio, example/$1/%.png, $$(EXAMPLE_IMGS_$1))


.PHONY: examples-$1 cleanexamples-$1
examples-$1: $$(EXAMPLE_PATH_$1) $$(EXAMPLE_DOCS_$1) $$(EXAMPLE_TGTI_$1)

example/$1:
	mkdir -p $$@

example/$1/%.md: ../example/$1/docs/%.md
	cp -f $$< $$@

example/$1/%.xml: ../example/$1/docs/%.drawio
	drawio --export --format xml -o $$@ --uncompressed $$<

example/$1/%.png: example/$1/%.xml
	for i in $$(shell seq 0 $$(shell echo $$(shell grep -o "<diagram" $$< | wc -l)-1 | bc)); do\
		drawio -x --width 2400 -f png -p $$$$i -o $$(basename .png $$@)-$$$$i.png $$<;\
	done
	rm $$<

cleanexamples-$1:
	rm -rf $$(EXAMPLE_PATH_$1)
endef

$(foreach example,$(EXAMPLES),$(eval $(call make-examples,$(example))))

# SERVE

.PHONY: all clean serve dists cleandists sphinx cleansphinx examples cleanexamples $(EXAMPLE_DOCS)
FORCE:
