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

1. This is the very first end-to-end example developped during the
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
   is a custom-built and legacy-constrained C-based runtime, the
   transformations and synthesis process (especially the artifact
   creation) might seem difficult to follow and unnecessarily
   complicated. Understanding these assumptions and limitations might
   help when adapting the example to more straigtforward and
   automation-friendly target platforms.
   
1. It is recommended to be get acquainted with the ZOTI ecosystem
   before following this tutorial or at least have the tool
   documentations at hand. 

## Application Overview

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
   
{% include image_caption.html url="pc.png" 
	relative=true legend="pc-legend.png" help=true
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
controls the acquisition and the fushing of the counter values and is
triggered externally
   
{% include image_caption.html url="pc-prob-col.png" 
	relative=true legend="pc-legend.png" help=true
	description="The modified producer-consumer application containing
	two counter probes along te datapath and an independent stats monitor
	process." %}
   
To describe this setup we use two components imported from a (possibly
external) component library `Lib.Probes`. From the perspective of the
application designer, these are "black boxes", and her only task is to
connect these components consistently within the system. To
understand, however, how the system is being synthesized, we need to
expand these "black boxes" and expose their constituent components, as
shown in the picture below.
   
{% include image_caption.html url="pc-prob-exp.png" relative=true
	legend="pc-legend.png" help=true description="The modified
	producer-consumer system with exposed library components." %}

As seen in the picture above, each `CounterProbe` consists in two
actors interacting via a "storage"-type of communication, which
implies two separate "timelines":

1. one triggered by the main data flow which increments the counter
   storage (buffer).

2. one triggered by the couter monitor which flushes the counter
   storage (buffer).

### The Target Platform

TBA

### Testing the application

This tutorial document is accompanying the executable example found on
[GitHub]({{root-path}}) at the specified root path. Follow the README
documentation at the provided link as well as in-tool help commands to
install, synthesizem deploy and execute both versions of the
application.

As a first trial run the "non-debug" versions of the applications and
make sure everything sets up and works accordingly. This
documentation, however, implies analyzing the intermediate files
generated only during the "debug" build process, so make sure you
clean up the project after the first trial and re-build it with the
debug flag, e.g.:

	make DEBUG=1 ...

## ZOTI Overview

{% include note.html content="Injecting counter probes could be
considered a generic enough operation to be performed by means of a
less verbose syntax sugaring construct (e.g., which might infer the
existence of `Lib.Probes.CounterStat` and its coupling with the
system). Such syntatic constructs could be featured in frontend
language parsers/pre-processors (e.g., as alternatives to ZOTI-YAML),
but are considered in this examples. Furthermore, as of [ZOTI's design
principles][philosophy] of orthogonalization, it does not matter where
the components originate or how they are being constructed as long as
the core internal representation (ZOTI-Graph) is a consistent and
fully-explicit graph, exposing all necessary implementation details." %}

[philosophy]: {{ "/" | prepend: site.baseurl | append: "#motivation--philosophy" }}

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
Ungureanu](https://github.com/ugeorge). The target runtime and
deployment scripts have been developed for an older internal project
and kindly provided by Leif Linderstam.
