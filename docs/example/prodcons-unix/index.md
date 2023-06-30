---
layout: default
version: 0.1.0
release_url: TBA
root-path: https://github.com/Ericsson/zoti/tree/main/example/prod-cons
---

# Synthesizing code with ZOTI. A Tutorial


This tutorial walks through the main features of the ZOTI framework
and is meant to give a feeling on how to design a synthesis flow using
ZOTI tools. However, before delving into details, there are several
important disclaimers you need to understand and assume when studying
this example:

1. This is the very first end-to-end example developed during the
   pre-alpha stages of ZOTI and last tested with [release
   {{page.version}}]({{page.release_url}}). While API, tools and code might
   change in time, the general design principles should be valid
   regardless of the current state of ZOTI. For this reason this
   tutorial will not focus much on showing code examples instead you
   are supposed to browse through the source files while this document
   only guides you on how to discover the features alone. If you also
   want to compile and execute the examples you need to download and
   install version [{{page.version}}]({{page.release_url}}) of ZOTI.
   
1. Although ZOTI helps with this task, code synthesis is by far
   non-trivial, this is why the (high-level) application itself is
   chosen to be as simple as possible. However, due to the fact that
   we wanted to showcase some advanced usage features (e.g. injecting
   counters in the data flow), as well as the chosen target platform
   is a custom-built and legacy-constrained C-based run-time, the
   transformations and synthesis process (especially the artifact
   creation) might seem difficult to follow and unnecessarily
   complicated. Understanding these assumptions and limitations might
   help when adapting the example to more straightforward and
   automation-friendly target platforms.
   
1. It is recommended to be get acquainted with the ZOTI ecosystem
   before following this tutorial or at least have the tool
   documentations at hand. 

## Overview

### Application

The application in this tutorial a rather straightforward design,
namely a producer-consumer system with three processes:

1. a source process `Src` which generates bursts of data sporadically
   when an external trigger `trig` arrives.
   
1. a data-crunching process `Proc` which performs some operations on
   the generated data, piping it through two stages: `Preproc` and
   `Maincomp`.
   
1. a receiver process `Sink` which collects the processed data and
   periodically prints the system status, with a period determined by
   an external trigger `stat`.
   
{% include image_caption.html url="pc-0.png" 
	relative=true legend="pc-3.png" help=true
	description="The original producer-consumer application." %}

In the picture above black arrows represent *event*-type of data
communication whereas the dashed dark-red lines represent
*storage*-type of data communication. Hence we identify two
"timelines" represented with the trigger chains:

1. `trig` &rarr; `Src/Src` &rarr; `Proc/Preproc` &rarr;
   `Proc/Maincomp` &rarr; `Sink/sink`

2. `stat` &rarr; `Sink/stat`

The second version of the application complicates matters a bit by
introducing two monitoring probes along the output edge from `Src/Src`
and along the edge between `Proc/Preproc` and `Proc/Maincomp`, which
counts how many times these edges are "activated". To print the
counter statuses we use an independent status monitor process which
controls the acquisition and the flushing of the counter values and is
triggered externally
   
{% include image_caption.html url="pc-2.png" 
	relative=true legend="pc-3.png" help=true
	description="The modified producer-consumer application containing
	two counter probes along the data path and an independent stats monitor
	process." %}
   
To describe this setup we use two components imported from a (possibly
external) component library `Lib.Probes`. From the perspective of the
application designer, these are "black boxes", and her only task is to
connect these components consistently within the system. To
understand, however, how the system is being synthesized, we need to
expand these "black boxes" and expose their constituent components, as
shown in the picture below.
   
{% include image_caption.html url="pc-1.png" relative=true
	legend="pc-3.png" help=true description="The modified
	producer-consumer system with exposed library components." %}

As seen in the picture above, each `CounterProbe` consists in two
actors interacting via a "storage"-type of communication, which
implies two separate "timelines":

1. one triggered by the main data flow which increments the counter
   storage (buffer).

2. one triggered by the counter monitor which flushes the counter
   storage (buffer).

### The Target Platform

The target platform for this application represents a set of Unix
processes communicating via UDP sockets. In this case each platform
node is meant to be mapped on one process sending information to each
other on pre-configured ports. The complete target setup is depicted
in the picture below.

{% include image_caption.html url="pc-4.png" relative=true
	legend="pc-5.png" help=true description="The target platform. The
	'platform' part is comprised of daemon processes aiding the system
	orchestration, whereas the 'application' part implements the
	original dataflow application." %}


Apart from the processes running the application, here are two
additional processes which are always present in the background:

* a *deploy agent* that spawns, configures and keeps track of all
  "application" processes.

* a *name server* that keeps an association table between "system
  trigger" port names (e.g. `trig`, `stat`, `flush`) and the currently
  allocated port numbers where the UDP message needs to be directed.
  
Both these auxiliary processes are controlled via user commands which
construct the appropriate requests and messages based on a certain
*deployment specification* document, which reflects the application
design.

### Testing the application

This tutorial document is accompanying the executable example found on
[GitHub]({{root-path}}) at the specified root path. Follow the README
documentation at the provided link as well as in-tool help commands to
install, synthesize deploy and execute both versions of the
application.

As a first trial run the "non-debug" versions of the applications and
make sure everything sets up and works accordingly. This
documentation, however, implies analyzing the intermediate files
generated only during the "debug" build process, so make sure you
clean up the project after the first trial and re-build it with the
debug flag, e.g.:

	make DEBUG=1 ...

### Browsing the project files

After successfully running the test application, this project should
have a similar folder structure like in the following listing. You
should have this at hand to help with navigating the folder structure
whenever asked to review a certain resource.

	.
	├── apps                # source files describing the producer-consumer application
	│   ├── kernels         # native code in kernel nodes (both variants)
	│   ├── pc              # graph spec for the original variant of the app
	│   │   └── ProdCons
	│   └── prob-pc         # graph spec for the probed variant of the app
	│       └── ProdCons
	├── docs                # sources for this document (can be ignored)
	├── gen                 # all files generated by ZOTI (both target and intermediate)
	│   ├── pc              # generated files for original variant of the app
	│   │   ├── bin         # compiled binaries (just before deployment)
	│   │   ├── code        # generated C source and header files
	│   │   ├── plots       # (debug) plots at different stages
	│   │   ├── tran_in     # files fed to ZOTI-Tran + (debug) pre-processed by ZOTI-YAML
	│   │   └── tran_out    # files generated by ZOTI-Tran + (debug) pre-processed by ZOTI-YAML
	│   └── prob-pc         # generated files for the probed version of the app
	│       │ ...
	├── graphlib            # "External" library of graph components
	│   └── Lib
	├── target              # target platform resources
	│   ├── c_lib           # C sources for the target API (e.g. services)
	│   ├── deploy-scripts  # scripts for deployment commands
	│   └── prebuilt        # compiled target libs (after 'make prepare')
	│       └── x86_64
	├── templatelib         # library of ZOTI-Gen templates
	│   ├── Generic
	│   │ ...
	├── typelib             # sources for ZOTI-FTN type specifications
	└── zoti-scripts        # all scripts associated with the synthesis flow
	    └── unix_c          # ZOTI-Tran scripts (transformations from ZOTI-Graph to 
	                        # ZOTI-Gen and other artifacts)


## Synthesis Flow


The purpose of the synthesis flow in this tutorial is to obtain the
necessary artifacts to be able to compile and deploy the streaming
[application(s)](#application) on [the Target
Platform](#the-target-platform). In this case, these artifacts are the
C code files for each application process, the header file(s) with
common definitions, and a deployment configuration file fed to the
target deployment scripts. The particular flow for obtaining these
artifacts in this tutorial is sketched in the diagram below, which
follows exactly the design principles shown in the [ZOTI
Overview][zoti-overview] page.

[zoti-overview]: {{ "/overview" | prepend: site.baseurl }}

{% include image_caption.html url="zoti-0.png" relative=true
	legend="zoti-1.png" description="The synthesis flow
	diagram. Project files represent inputs specific to this
	application, whereas external resources represent libraries of
	(generic) components." %}

The flow depicted above is implemented by the `zoti-scripts/Makefile`
script. Notice that most input specification files pass (one way or
another) through a pre-processor, such as ZOTI-YAML. In the case of
ZOTI-Graph inputs this is evident, since ZOTI-YAML builds a unique
specification tree from multiple sources (both app description and
libraries). For ZOTI-Gen inputs (see `gen/<example>/tran_out/*.zoc`)
the `!default` feature is useful for less verbose genspecs. In all
cases however, one of the main benefits input pre-processing is
obtaining and propagating positional information for various nodes of
interest, which is essential when handling exceptions during
synthesis.

Notice also the sub-flow marked by the "Code artifact generation"
box. While it might seem slightly convoluted, it is partitioned like
that for the sake of generality. More exactly, ZOTI-Gen is a generic
template-based tool and does not contain any target-specific
logic. While it can parse and build dependency graphs based on its
internal structure representation, it does not know what these
dependencies actually *mean*: in the case of C target files, declared
dependencies can infer the order in which `#include` directives
appear, based what blocks are instantiated within the body. Instead of
injecting this logic into the ZOTI-Gen tool itself, we export the
solved dependencies as JSON files and use them to build C file
preambles using an external custom script (see
`zoti-scripts/unix_c/postproc.py`).

Finally, once we obtain the target artifacts, our job is done as far
as the ZOTI flow is concerned. This is why all subsequent actions are
hidden in the picture above behind a "cloud". For the sake of
completeness however, this tutorial project provides scripts that
perform compilation, linking, deployment and operation, but are
outside the scope of this document and are only briefly mentioned.

### Input Specification Files

Take a look at the input graph specifications of both versions of the
producer-consumer application, found in `apps/<example>`, alongside
their respective graph and tree plots found in
`gen/<example>/plots/ProdCons_*.dot`. Upon a first inspection the
following ZOTI-YAML features stick out:

{% include note.html content="When browsing '.zog' files it is
recommended to turn on the YAML syntax highlighting." %}

- When expanding the folder structure of `apps/<example>` and
  `graphlib`, e.g. via
		
		tree apps/<example> 
		tree graphlib
		
  this structure coincides with the module names referenced via
  `import` statements, This is because both are passed as search path
  roots to the `--pathvar` argument of ZOTI-YAML CLI (see the variable
  `GRAPH_LIB` in `zoti-scripts/Makefile`).
  
- Considering `apps/<example>/ProdCons.zog` as the main (i.e. root)
  file for the app description, all subsequent components are included
  via `!attach` directives, which simply "stitches" a sub-tree found in
  another module at the current location. In other words building an
  app graph specification is as rudimentary (yet as versatile) as
  "stitching together" different sub-trees found in various places
  (both in project and in libraries).
  
- When working with library components it is expected to fill in the
  missing information via the exposed `parameter` entries which are
  referenced in the component definition (see
  `graphlib/Lib/Probes.zog`)

It could be argued that counter injection along the dataflow paths can
be specified in a less verbose manner than explicitly importing and
connecting each auxiliary component. We invoke again the [principle
of generality][philosophy] for the solution we chose: a syntactic
sugaring construct that infers all auxiliary components for the
counter probes and monitor would preform a too specialized
(domain-specific) task for the purpose of ZOTI-YAML. Instead, such a
construct would be more appropriate for a domain-specific frontend
language parsed *before*, or as *an alternative to* ZOTI-YAML.


Notice that each `KernelNode` points to a certain file or file part
found at `apps/kernels` via an `!include` directive. Check these files
now. They contain a combination of native C code and Jinja2 template
markup. The most used markup functions for kernel code are the
`setter` and `getter` functions (see [ZOTI-Gen
documentation][zoti-gen]) which expands into the appropriate access
macros for the respective ports.

{% include note.html content="When browsing '.dfc' files it is
recommended to alternate between C and Jinja2 syntax highlighting, to
point out either C code or the template markup code." %}

Now that your attention is drawn to the markup binding code to ports
check more carefully the port definitions in the `.zog` files. Notice
that most ports have a `data_type` entry containing either one of the
following entries:

```yaml
data_type: {name: <type-name>, ...}
# or
data_type: {from_ftn: <type-definition>, ...}
```

Check the ones specifying a type name formed as
`<module>.<name>`. Each module is defined in a file at
`typelib/*.ftn`, using the in-house ZOTI-FTN specification
language. These specifications will aid in generating both glue code
(e.g., definition, instantiation, (de-)allocation, (un-)marshalling,
copying, etc) and the access macros we just mentioned in the previous
paragraph.

**OPTIONAL**: If you built the applications in debug mode, apart from
plots you can examine intermediate YAML files generated by ZOTI-YAML
are dumped at the following paths:

- `gen/<example>/tran_in/ProdCons_preparse.yaml` for the application graph;
- `gen/<example>/tran_in/types.yaml` for types.

Check them now and notice how they differ from the originals, as well
as from the raw `AppGraph` serialization in the same folder.

### Understanding What We Are Trying to Obtain

Open now the generated code file for one of the examples in
`gen/<example>/code/*.c` (start with `pc` and then `prob-pc`). Analyze
them for a few minutes and compare them against each other. Try to
answer the following questions:

- Can you identify where the kernel code is? How is it "glued" and
  called from within the program?
  
- Can you identify other elements from the original graph description?
  For example, can you see where the ports are? How are they
  instantiated and how are they used? How is the data passed to/from
  the kernel functions? How about actors, how are they represented?
  
- How does the concept of "timelines" we insisted on in the
  [application overview](#application) affect the execution of the
  program? How is this implemented?
  
- What part of the code do you think is boilerplate? Would you be able
  to write a template for that boilerplate?
  
- What part of the code do you think is dependent on the information
  stored in the port entries (e.g. `data_type`)?
  
- Can you make a rough partition of blocks from each source code file?
  What would these blocks be and where would they originate from?
  
Now check the plots for each genspec found at
`gen/<example>/plots/*.genspec.dot`. Do the block specifications there
follow (to some extent) the partitioning of the code you just
envisioned? How did they differ and do you have an idea why (if it is
the case)?

{% include note.html content="When browsing '.zoc' files it is
recommended to turn on the YAML syntax highlighting." %}

Finally, open the genspec files for each code file found at
`gen/<example>/tran_out/*.zoc`. While it is difficult to follow what
happens there, take a closer look to what port definitions have
become. Focus on entries such as `block/label` or
`block/instance/bind`. Pay special attention to how the blocks
originating from kernel nodes are being defined, especially their
`label` definitions. What do the `block/label/glue` entries represent
(tip: check [ZOTI-Gen][zoti-gen] documentation.) Cross-check with the
original kernel code (in `apps/kernels/*.dfc`) and the generated code
files (in `gen/<example>/code/*.c`), respectively the generated types
header file (at `gen/<example>/code/types.h`). Can you see the
connection between `.dfc` template, `.zoc` glue entire and generated
`.c` code and reverse-engineer how the code generation process
happened?

Hopefully, by studying the results of this ZOTI synthesis flow against
ts inputs, you built a rough intuition on how the the scripted
transformational process is being performed and why. Having this
intuition is important to justify and understand the chosen
transformations for this tutorial example presented in the next
section. Furthermore, the final scope of this tutorial is to build the
type of critical thinking enabling to judge both good and bad design
decisions and adapt the synthesis flow to your own custom use case.

### Graph Transformations

We now focus on the transformational process depicted with the
ZOTI-Tran node in the [synthesis flow](#synthesis-flow) diagram. For
this you need to study the Python scripts in
`zoti-scripts/unix_c`. Start by opening the main runner at
`zoti-scripts/unix_c/graph2block.py` After importing the `AppGraph`
and `FtnDb` graph/type representations and initiating a `Script`
object, the first operation performed is to sanity check the
specification graph against all the rules provided by
[ZOTI-Graph][zoti-graph]. The subsequent transformations are described
in the following paragraphs, where *G* denotes the graph
representation in the current state, whereas *T* denotes the type
database.

Notice the `TransSpec` definition for each transformation stage,
namely the title and the graph information which is plotted after the
transformation is being performed (only in debug mode). To check each
plot open `gen/<example>/plots/<dump_title>_graph.dot`.

#### Stage 1: Port Inference

| Defined in                        | Requires | Affects | Byproduct | Prerequisite |
|:----------------------------------|:---------|---------|:----------|:-------------|
| `zoti-scripts/unix_c/translib.py` | *G*, *T* | *G*     | flag      | none         |

You might have noticed when studying the application specification
inputs at `apps/<example>/**/*.zog` that not all ports are fully
specified, yet for the synthesis process all information possible
associated with a model object is mandatory. This was, by no mistake,
a feature assumed during the specification phase, namely to assume a
convenient type inference system that can "fill in" information based
on port connections. This feature however is not implemented anywhere,
instead is provided as a graph transformation function. In other
words, the first transformation syncs all `data_type`, `port_type` and
`mark` entries based on interconnections. If inconsistencies or
missing data are detected, this function throws an error.

#### Stage 2: Prepare Platform Ports

| Defined in                        | Requires | Affects | Byproduct | Prerequisite     |
|:----------------------------------|:---------|---------|:----------|:-----------------|
| `zoti-scripts/unix_c/translib.py` | *G*, *T* | *G*     | none      | `port_inference` |

Here we witness the first target-dependent transformation. As per the
target platform, each port type is required to store data in a
specific buffer-like structure, as well as to have an asigned socket
variable which will be filled in during the application
configuration. This transformation updates every port of each
platform node to reflect this:

- input ports update their `data_type` entry based on their
  `port_type`.
- output ports instantiate a new socket port which will create a
  socket global variable down the line.

#### Stage 3: Expand Actors

| Defined in                        | Requires | Affects | Byproduct | Prerequisite |
|:----------------------------------|:---------|---------|:----------|:-------------|
| `zoti-scripts/unix_c/translib.py` | *G*      | *G*     | flag      | none         |

Another "liberty" taken during the specification phase allowed us to
none-verbosely describe simple actors with only one characteristic
behavior by ignoring concepts like "detector" or "scenario". This
transformation makes up for that and transforms all actors to a
canonical form where detectors and scenarios are made explicit. In our
case, even though all actors have a unique scenario, it is explicitly
marked under a cluster called "default".

#### Stage 4: Flatten

| Defined in                               | Requires | Affects | Byproduct | Prerequisite |
|:-----------------------------------------|:---------|---------|:----------|:-------------|
| `${ZOTI_TRAN}/src/zoti_tran/translib.py` | *G*      | *G*     | flag      | none         |

This transformation "dissolves" (i.e., unclusters) all composite nodes
except for those marked as *scenario*, hence the only allowed
hierarchy of the system is `PlatformNode` &rarr; `ActorNode` &rarr;
`CompositeNode` (for scenarios) &rarr; `KernelNode`. All other
clusters originated from component reuse are flattened to their basic
components.

At this stage we brought the application graph to a convenient form
that can be matched against patterns and manipulated towards the form
we want to achieve, i.e. the code block genspecs studied in the
previous section.

#### Stage 5: Prepare SIDE Ports

| Defined in                        | Requires | Affects | Byproduct | Prerequisite     |
|:----------------------------------|:---------|---------|:----------|:-----------------|
| `zoti-scripts/unix_c/translib.py` | *G*, *T* | *G*     | none      | `port_inference` |

This transformation updates creates a global buffer port for each
connection via SIDE actor ports (i.e., interactions between actors via
side-effects). After this it updates all end-ports (i.e., belonging to
kernels) to match the name of this global buffer, as well as it
destroys all edges in-between. At the end of this transformation all
graph edges will represent event-like interactions, where graph
elements trigger each other within the same timeline. Actors belonging
to separate timelines will be "physically" separated.

#### Stage 5: Fuse Actors

| Defined in                               | Requires | Affects | Byproduct | Prerequisite |
|:-----------------------------------------|:---------|---------|:----------|:-------------|
| `${ZOTI_TRAN}/src/zoti_tran/translib.py` | *G*      | *G*     | flag      | `flatten`    |


Once actors belonging to different timelines have been separated
during the previous transformation, fusing actors belonging to the
same timeline becomes trivial, thanks to the API of ZOTI-Graph. After
this transformation

- all actors remaining in a platform node represent an independent
  reaction to the input stimuli; 
- each actor exposes scenarios resulted from merging the data paths of
  the fused actors.
- each actor has only one composite detector FSM resulted from merging
  the constituent FSMs.


{% assign notetext = "At the time of writing this tutorial during
release " | append: page.version | append: " scenario merging and
detector FSM merging were not fully implemented, only as much as this
demonstrator required." %}
{% include note.html content=notetext %}

#### Stage 6: Prepare Intermediate Ports

| Defined in                        | Requires | Affects | Byproduct | Prerequisite     |
|:----------------------------------|:---------|---------|:----------|:-----------------|
| `zoti-scripts/unix_c/translib.py` | *G*      | *G*     | flag      | `port_inference` |

The final graph-to-graph transformation in our custom synthesis flow
identifies intermediate connections between kernels and promotes them
to their own port which will become an intermediate buffer down the
line.

This transformation brings the application graph to a form which can
directly be parsed and translated into code blocks specifications in
one go,

{% include note.html content="Additional transformations will be
required when considering multi-input actors with user-defined
reaction patterns, but in the simple case of this tutorial these
transformations suffice." %}

#### Stage 7: Generate Typedefs

| Defined in                         | Requires | Affects | Byproduct             | Prerequisite     |
|:-----------------------------------|:---------|---------|:----------------------|:-----------------|
| `zoti-scripts/unix_c/artifacts.py` | *G*, *T* | none    | contents of `types.h` | `port_inference` |

Once the graph manipulations are complete and auxiliary constructs
created, building up the typedef header is a matter of parsing the
graph, gathering a set of types used in all ports and resolving the
dependencies between them to determine the order of declaration. For
each identified type, the code text for definition and access macros
is generated from *T*. 

The C code is presented as a byproduct of this transformation script
(see documentation for [ZOTI-Tran][zoti-tran]).

#### Stage 8: Generate Genspecs

| Defined in                         | Requires | Affects | Byproduct        | Prerequisite                                                                                                 |
|:-----------------------------------|:---------|---------|:-----------------|:-------------------------------------------------------------------------------------------------------------|
| `zoti-scripts/unix_c/artifacts.py` | *G*, *T* | none    | dict of genspecs | `prepare_platform_ports`, `prepare_side_ports`, `prepare_intermediate_ports`, `expand_actors`, `fuse_actors` |

{% include note.html content="It is recommended to read and understand
the source code while looking at the plot for Stage 6." %}

Creating block structure that specifies how the code is being
constructed involves parsing through the entire application graph and
dumping all the information necessary in the required format (see
input format documentation for [ZOTI-Gen][zoti-gen]). Each platform
node generates a separate genspec tree, which would eventually end up
in a separate code file. Hence the procedure is repeated for each
platform node and can be summarized as follows:

- identify marked resources at the platform node level, such as global
  variables, probe buffers, sockets, timers, atoms, etc. For these
  resources create, as appropriate:
  - blocks with declaration and initialization code.
  - blocks for target platform routines for initialization and
    configuration (e.g. in-ports, out-ports, atoms, timers, etc.)
- create a block for the main function
- for each input port belonging to a child actor node parse how the
  data propagates and build a port reaction routine as follows:
  - identify and create glue associated with buffers, intermediate
    variables etc.
  - identify and instantiate blocks for allocating, receiving and
    unmarshalling data from the input port.
  - identify and instantiate blocks for data preprocessing, detector
    FSM.
  - for each scenario belonging to the actor node build the
    corresponding data path consisting in:
	- instantiating blocks for each kernel node
	- identifying and creating blocks for marshalling, sending and
      deallocating buffer for each output port
	- sequencing these blocks in the correct order
  - sequence the blocks in the correct order
- create the preamble and document tree for each genspec.

#### Stage 9: Generate Deployment Spec

| Defined in                         | Requires | Affects | Byproduct   | Prerequisite |
|:-----------------------------------|:---------|---------|:------------|:-------------|
| `zoti-scripts/unix_c/artifacts.py` | *G*      | none    | depl. spec. | none         |

The final transformation stage creates a deployment specification
document as expected from the target deployment scripts. This document
mainly exposes platform nodes as Unix processes, associated binaries,
and what resources are being used and need to be allocated for
interprocess communication.

### Code Generation

The last step of the [synthesis flow](#synthesis-flow) is to generate
the target code files. As seen in the flow diagram above, this is
further broken down into two stages.

#### Stage 1: Generate Document Text

The main part of the code file is generated by [ZOTI-Gen][zoti-gen]
based on the genspec files established in the previous step. Now that
you went though their building process it should hopefully be more
clear what purpose the genspec files serve. For each platform node,
please open and compare against each other:

  * the genspec file `gen/<example>/tran_out/<node-name>.zoc`
  * the genspec plot `gen/<example>/plots/<node-name>.genspec.dot`
  * the generated code file `gen/<example>/code/<node-name>.c`

By now the relation between blocks and code should be
self-explanatory. Pay attention however that all blocks who do not
specify a `code` entry, have instead a `type` entry. This means that,
instead of explicitly exposing their code template, these blocks point
to a library template for pre-determined components. Open now and
analyze these template blocks specifications (e.g., at
`templatelib/Generic/Dfl.py`) and the text for their `code` entries
(e.g. in `templatelib/Generic/dfl.c`). Can you now identify this code
in the generated artifact in the place where its corresponding block
was specified?

Pay attention that, apart from `code`, some blocks specify other
entries such as `prototype` and even include `requirement`s. These
entries are carried out and reflected whenever the block is being
instantiated in a genspec document. Moreover, see that some blocks
define a `check` function containing mainly assertions. This is a hook
function that enables verification that the block is instantiated as
intended within a genspec tree, and if the conditions are not
satisfied ZOTI-Gen would throw an error during code generation.

{% include note.html content="The template components used in this
tutorial are only stubs for quickly setting up the example. In a
realistic production environment at least a richer API documentation,
as well as more advanced self-validation logic, would be required." %}

#### Stage 2: Generate Document Preamble

While studying the previous stage you might have noticed that both
some genspec blocks and some template library blocks contain a
`requirement` field. In the case of C target artifacts, these
represent dependencies upon external C libraries that appear in the
template code. While not really caring what these requirements
represent, ZOTI-Gen can gather them in categories, respectively build
and solve their inter-dependency graphs. This is precisely what the
`gen/<example>/tran_out/<node-name>.deps.json` files contain, their
information being used by the `zoti-scripts/unic_c/postproc.py` to
generate the text for the C file preambles.

## Compilation and Deployment

Once code files are generated compilation follows a typical procedure
for obtaining binary files. In this case we use the
[GCC](https://gcc.gnu.org/) compiler and link the generated `.c` files
against the header files and pre-built target objects in
`target/c_lib`. The compiled binaries are found at
`gen/<example>/bin`.

With the binary files in place deployment and operation follows the
procedure presented in the [target platform
overview](#the-target-platform), and can be controlled by the makefile
rules (see `README.md`).

## Conclusion

This tutorial walked through a complete end-to-end synthesis process
from a declarative specification of a streaming application containing
all the implementation details to generate the code (i.e. resource
allocation and usage is solved and given up-front) to its
implementation on a Unix-based system of intercommunicating
processes. While the exact implementation of this toy example might
get outdated in time, the focus of the tutorial was to build an
intuition of what resources are needed and where, as well as how to
conceptually design a synthesis flow and adapt it to any target
platform based on the current state of the ZOTI tools.

Another reason why this tutorial focuses on "reading the source code"
instead of "dictating what to do" is to build a critical thinking to
identify both benefits and caveats of the current approach to generic
multi-target code synthesis. Furthermore, we hope to inspire you to
actively contribute to the continuous improvement of this ecosystem,
methodology, and the community around it.

## Authors & Acknowledgements

The tutorial and toy example has been written and developed by [George
Ungureanu](https://github.com/ugeorge). The target run-time and
deployment scripts have been developed for an older internal project
and kindly provided by Leif Linderstam.



[philosophy]: {{ "/" | prepend: site.baseurl | append: "#motivation--philosophy" }}
[zoti-gen]: {{ "/zoti-gen" | prepend: site.baseurl }}
[zoti-graph]: {{ "/zoti-graph" | prepend: site.baseurl }}
[zoti-tran]: {{ "/zoti-tran" | prepend: site.baseurl }}
