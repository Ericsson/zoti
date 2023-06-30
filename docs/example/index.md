---
layout: default
---

# Examples

Here is a collection of open-source code synthesis examples using the
ZOTI tools used for didactic purpose.

[Producer-Consumer](prodcons-unix)
: This is the very first end-to-end example published with the initial
  (pre-alpha) release or ZOTI showcasing its capabilities. It features
  a classical producer-consumer application implemented on a custom
  Unix deployment where each target node is a Unix process running C
  code and communicating via UDP sockets. The exampe walks through
  advanced topics such as using library components (i.e., using a
  monitor process and hooking counters into the dataflow), timelines,
  model transformations and artifact generation, and is meant to be
  self-contained (i.e., all sources and scripts are provided).
  
  > This example has been built and tested with version [0.2.0]() of
  > the ZOTI tools.
 
