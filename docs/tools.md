# Tools

[ZOTI-YAML]({{ "/zoti-yaml" | prepend: site.baseurl }})
: an extension of the YAML language introducing modules, some crude
  component-like imports and various tree manipulation utilities built
  for conveninence. It outputs standard JSON and YAML, hence it can be
  used to pre-process data for any other tool that uses serialized
  data formats.

[ZOTI-Graph]({{ "/zoti-graph" | prepend: site.baseurl }})
: a graph-based internal representation format and API for describing,
  annotating and manipulating system models.

[ZOTI-FTN]({{ "/zoti-ftn" | prepend: page.nopage_baseurl }})
: a data type representation format and engine focusing on generating
  glue code for various target languages.
  
[ZOTI-Gen]({{ "/zoti-gen" | prepend: page.nopage_baseurl }})
: a template engine that takes care of managing libraries of prebuilt
  component templates and combining them for constructing target
  artifacts. The construction is dictated by a (set of) *code blocks
  spec* model(s) resulted from previous model-to-model transformations.

