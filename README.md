# zoti
ZOTI (Zero Overhead Topology Infrastructure) is a collection of tools
for describing code synthesis flows towards heterogeneous platforms.

Documentation hub is found at <ericsson.github.io/zoti/>.

For installation and usage instructions check the `README.md` files in
each project root.

Currently developed tools are:

[ZOTI-YAML](zoti-yaml)
: a YAML language extension to enable describing serialized files in
  modules, and other convenience features.

[ZOTI-Graph](zoti-graph)
: an graph-based internal representation format and API for describing
  and manipulation system models.
  
  
[ZOTI-FTN](zoti-ftn)
: a format for describing data types and tool for generating
  target-specific glue code for those types.

[ZOTI-Tran](zoti-tran)
: a minimal set of utilities to jump-start the description of custom
  model-to-model transformation scripts.
  
[ZOTI-Gen](zoti-gen)
: a template-based engine for generating target code based on 1) a
  library of code templates; 2) a library of type glue code; 3) a
  structural description defining how templates and glue are placed.
