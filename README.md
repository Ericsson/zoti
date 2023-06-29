# zoti

This is the monorepo associated with the ZOTI (Zero Overhead Topology
Infrastrcture) project ongoing at Ericsson. It is a collection of
open-source tools for developing code synthesis flows towards
heterogeneous platforms, together with demo examples. All tools and
examples are developed under an MIT license (see [LICENSE](LICENSE)
file).

Documentation hub is found at <ericsson.github.io/zoti/>.

For installation and usage instructions check the `README.md` files in
each tool root folder.

Currently featured tools are:

[ZOTI-YAML](zoti-yaml)
: a YAML language extension to enable describing serialized files in
  modules, and other convenience features.

[ZOTI-FTN](zoti-ftn)
: a format for describing data types and tool for generating
  target-specific glue code for those types.
  
[ZOTI-Graph](zoti-graph)
: an graph-based internal representation format and API for describing
  and manipulation system models.
  
[ZOTI-Gen](zoti-gen)
: a template-based engine for generating target code based on 1) a
  library of code templates; 2) a library of type glue code; 3) a
  structural description defining how templates and glue are placed.
