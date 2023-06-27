---
layout: default
---

# The ZOTI Project

The Zero-Overhead Topology Infrastructure Project sets out to aid in
the development of high-performance applications on heterogeneous
platforms by means of model-driven engineering.

{% include image_caption.html url="/assets/images/Pitch_flow.png"
	description="ZOTI's goal in a nutshell: develop practical means
	for computer-aided synthesis from platform-agnostic application
	models to heterogeneous platforms."  %}

This web site (together with its
[repository](https://github.com/Ericsson/zoti)) is meant as a hub for
gathering open-source tools, demos, tutorials and publications that
can showcase and kickstart the development of synthesis flows from
system models to deployable implementations with respect to the
project goals. This hub is planned to grow organically with sporadic
additions as the project also grows. The material falls in one of
three categories, as shown below: synthesis flows, tools, and
examples.

## Flows, Tools and Examples

> ZOTI is an arena for combining, orchestrating, and "filling in the
> gaps" between state-of-the-art open-source tools/methods with the
> purpose of developing end-to-end design solutions.

Synthesis Flows 
: A flow is a (transformational) design process, usually chaining
  several design steps, for the purpose of solving a particular design
  problem. As per [the third key principle of
  ZOTI](goals-and-key-principles) the inputs and outputs of flows are
  *models*, wheres a flow itself represents a *model
  refinement*. Flows are generic and presented in terms of guidelines,
  whereas the tools implementing them can be chaged or adapted to a
  particular use case.
  
Tools
: A tool is an implementation of a specific task in a synthesis
  flow. Tools can be either computer programs, scripts, pointers to
  existing open-source tools that can be used as-is or wrappers around
  existing open-source tools adapting them to a particular flow. Their
  inputs and outputs are mainly intermediate representations of models
  expressed as serializable formats.
  
Examples
: An example is a use case showing a particular instance of a
  synthesis flow, where design steps are usually implemented with
  tools in the ZOTI suite.

## Goals and Key Principles

> ZOTI does not "reinvent the wheel", but rather employs conventional
> wisdom and existing tools to showcase pragmatic, scalable and
> future-proof methodologies.

As a project, ZOTI does not promise nor does it intend to pursue a
"one-stop shop" for generic design and synthesis, but an environment
where developers can describe systematic and traceable transformation
flows from target-agnostic application models down to concrete
implementation, as well as plug in machine intelligence into this
process. In a very broad sense, its goal is to provide practical means
to explore an application's design space via systematic,
computer-aided decisions and model transformations (see drawing
below). This is done by staying true to three overarching principles:

{% include image_caption.html url="/assets/images/Design_space.png"
	scale=220 description="Visualization of the design process. Points
	are models, arrows are model refinements."  %}
	
Traditional technology abstraction is too costly
: This refers to abstracting away the complexity of the underlying
  machinery by means of software technology stacks (e.g. libraries,
  runtimes, containers, etc.). While this works well enough with the
  majority of computational systems, there are a classes of systems
  (e.g. high-performance or embedded) where the overhead implied by
  such abstraction stacks is unacceptable, either because it reduces
  some KPI (e.g., throughput, energy consumption, security) or because
  it introduces hazardous behaviors (e.g. timing aspects). To
  circumvent this, developers usually break the abstractions by
  controlling and programming low-level resources (e.g. via assembly,
  intrinsics, directives, low-level APIs), hence also breaking the
  paradigm of the said abstractions (e.g. losing testability,
  modularity, maintainability, etc.). ZOTI pursues a third approach,
  where the developers program the systems at a high abstraction level
  and *systematically generate the low-level code* by transforming
  functions/behaviors to target-specific boilerplate code. Hence it is
  the application model (e.g., the flow of data) which dictates the
  implementation, and not an entire technology stack that hosts the
  model.
   
   *This key principle captures the "Zero Overhead" part in ZOTI's
   name.*

Meaningful decisions can only be taken on a complete view of HW and SW in tandem
: Also to cope with the sheer complexity, the separation of the
  different parts of a system (e.g., SW, HW) is a necessity during
  design and development. This approach, however, limits the insight
  into the desired system behavior too early into the design process,
  allowing only for at most local optimizations as well as external
  assumptions which need to be resolved during system integration. To
  unlock the full potential of a system HW/SW co-design principles
  need to be applied. In this sense a cohesive view on how the
  different aspects of a system interact with each other
  (e.g. application-mapping-platform) can help in taking meaningful
  design decisions and choosing opimal refinements.

  *This key principle captures the "Topology" part in ZOTI's name.*

Models are the exchange currency between tools
: This states that, although acknowledging the role of models as
  design lanuages, ZOTI values them rather for their ability to be
  parsed, analyzed and serialized between different tools. While
  showing an affinity to modeling paradigms that express concurrency
  (e.g. dataflow), parallelism (e.g. algorithmic skeletons) and in
  general lend themselves to efficient implementations, ZOTI does not
  impose the usage of any particular language or model. Instead ZOTI
  works with various intermediate representations, which can vary from
  guidelines and schemas to existing open-source formats.

   *This key principle captures the "Infrastructure" part in ZOTI's
   name.*


