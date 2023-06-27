A Producer-Consumer Example in ZOTI
============================================

This project is the complete end-to-end example accompanying the first
[online tutorial](https://ericsson.github.io/zoti/example/prod-cons/)
on building a synthesis flow with ZOTI. It contains the source files,
sripts and libraries that generate both the executable binaries and
their deployment, but also intermediate files used for study purposes.

Running the examples
-------------------------

The target platform for this tutorial example is a custom deployment
of Unix processes communicating through UDP sockets, so you should be
able to run the examples on any Linux distribution as long as the
dependencies are satisfied.

To list the useful commands type in

	make help
	
from this working directory.

Taking care of dependencies
---------------------------------

As documented in the
[tutorial](https://ericsson.github.io/zoti/example/prod-cons/), this
example has been developed during release [0.1.0](TBA) of the ZOTI
tools. This means that since the last time this file has been written,
the main ZOTI repo might have introduced API-breaking changes. To
avoid unpleasant crashes, please make sure you download the specified
release version for running this example.

This example is dependent on various basic Linux tools, such as [GNU
Make](https://www.gnu.org/software/make/) [Python
3](https://www.python.org/) and [GCC](https://gcc.gnu.org/), along
with other more specific dependencies. If any of these dependencies
are not met the Makefile scripts will throw an error with a
descriptive message, in which case you need to install it on your
Linux platform. Some particular installation instruction can be found
for ZOTI tools (e.g. for [ZOTI-YAML](../../zoti-yaml/README.md)) in
the improbable event that your favourite search engine does not help.

While not explicitly propmped during installation or operation, while
going through this tutorial it is also good to have:

- a practical IDE with user-controlled code highlighting (e.g. [GNU
  Emacs](https://www.gnu.org/software/emacs/) with modes for C,
  Python, YAML, JSON, TOML, Jinja2).
  
- a [Graphviz](https://graphviz.org/) format viewer for plotting
  intermediate graphs (e.g. [xdot](https://pypi.org/project/xdot/)).
