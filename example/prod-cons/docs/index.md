---
layout: default
version: 0.1.0
release-url: TBA
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
   {{version}}]({{release-url}}). While API, tools and code might
   change in time, the general design principles should be valid
   regardless of the current state of ZOTI. For this reason this
   tutorial will not focus much on showing code examples instead you
   are supposed to browse through the source files while this document
   only guides you on how to discover the features alone. If you also
   want to compile and execute the examples you need to download and
   install version [{{version}}]({{release-url}}) of ZOTI.
   
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
	two counter probes along te data path and an independent stats monitor
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
	│   │   ├── spec        # spec files generated by ZOTI-Tran + (debug) their plots
	│   │   ├── graph       # input ZOTI-Graph files + (debug) their plots
	│   │   ├── trans_dbg   # (debug) plots after each transformation stage
	│   │   └── types       # (debug) Parsed .ftn files fed to ZOTI-YAML
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
artifacts in this tutorial is sketcked in the diagram below, which
follows exactly the design principles shown in the [ZOTI
Overview][zoti-overview] page.

[zoti-overview]: {{ "/overview" | prepend: site.baseurl }}

{% include image_caption.html url="zoti-0.png" relative=true
	legend="zoti-1.png" description="The synthesis flow
	diagram. Project files represent inputs specific to this
	application, whereas external resources represent libraries of
	(generic) components." %}

The flow depicted above is implemented by the `zoti-scripts/Makefile`
script. Notice that all input specification files that are fed to ZOTI
tools pass (one way or another) through ZOTI-YAML. In the case of
ZOTI-Graph this is evident, since it builds a unique specification
tree from multiple sources (both app description and librarires). For
ZOTI-Gen inputs (see `gen/<example>/spec/*.zoc`) the `!default`
feature is useful for less verbose genspecs. In all cases however, one
of the main benefits of passing input through ZOTI-YAML is obtaining
and propagating positional information for various nodes of interest,
which is essential when handling exceptions during the synthesis
process.

Notice also the sub-flow marked by the "Code artifact generation"
box. While it might seem slightly convoluted, it is partitioned like
that for the sake of generality. More exactly, ZOTI-Gen is a generic
template-based tool and does not contain any target-specific
logic. While it can parse and build dependecy graphs based on its
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
hidden in the picture aboce behind a "cloud". For the sake of
completeness however, the tutorial project provides scripts that
perform compilation, linking, deployment and operation, but are
outside the scope of this document and are only briefly mentioned.

### Project sources


{% include note.html content="When browsing '.zog' files it is
recommended to turn on the YAML syntax highlighting." %}

Take a look now at the input graph specifications of both versions of
the producer-consumer application, found in `apps/<example>`,
alongside their respective graph and tree plots found in
`gen/<example>/graph/*.dot`. Upon a first inspection the following
ZOTI-YAML features stick out:

- when expanding the folder structure of `apps/<example>` and
  `graphlib`, e.g. via
		
		tree apps/<example> 
		tree graphlib
		
  this structure coincides with the module names of each file, This is
  because both are passed as search path roots to the `--pathvar`
  argument of ZOTI-YAML CLI (see the variable `GRAPH_LIB` in
  `zoti-scripts/Makefile`).
  
- considering `apps/<example>/ProdCons.zoc` as the main (i.e. root)
  file for the app description, all subsequent componets are included
  via `!attach` directives, which simply "stitches" a subtree found in
  another module at the current location. In other words building an
  app graph specification is as rudimentary (yet as versatile) as
  "stitching together" different subtrees found in various places
  (both in project and in libraries).
  
- when working with library components it is expected to fill in the
  missing information via the exposed `parameter` entries which are
  referenced in the component definition (see
  `graphlib/Lib/Probes.zog`)


<!-- {  % include note.html content="Injecting counter probes could be -->
<!-- considered a generic enough operation to be performed by means of a -->
<!-- less verbose syntax sugaring construct (e.g., which might infer the -->
<!-- existence of `Lib.Probes.CounterStat` and its coupling with the -->
<!-- system). Such syntactic constructs could be featured in frontend -->
<!-- language parsers/pre-processors (e.g., as alternatives to ZOTI-YAML), -->
<!-- but are considered in this examples. Furthermore, as of [ZOTI's design -->
<!-- principles][philosophy] of orthogonalization, it does not matter where -->
<!-- the components originate or how they are being constructed as long as -->
<!-- the core internal representation (ZOTI-Graph) is a consistent and -->
<!-- fully-explicit graph, exposing all necessary implementation details." %  } -->

<!-- [philosophy]: {{ "/" | prepend: site.baseurl | append: "#motivation--philosophy" }} -->

## Browsing Through the Source Files

TBA

## The Synthesis Flow

TBA

## Compilation and Deployment

TBA

## Conclusion

TBA

## Authors & Acknowledgements

The tutorial and toy example has been written and developed by [George
Ungureanu](https://github.com/ugeorge). The target run-time and
deployment scripts have been developed for an older internal project
and kindly provided by Leif Linderstam.
