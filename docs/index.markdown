---
layout: default
---

# The ZOTI Project

ZOTI stands for Zero-Overhead Topology Infrastructure and is being
developped as an attempt to tackle the rapidly increasing
heterogeneity of today's compute platforms in the context of
high-performance applications. In this sense ZOTI is meant to aid in
the tedious process of electronic system-level design with one
concrete task: the generation of *deployable and executable code* from
a (set of) *declarative specification model(s)*.

By design ZOTI does *not* promise a one-stop shop solution for generic
code synthesis, but rather an environment where developers can
describe and build systematic and traceable transformation flows from
target-agnostic system models down to implementation. As such, ZOTI is
offering to fill in an increasingly prominent gap between formal
design methodologies and commercial platform solutions by addressing
the *translation* between these two domains.

{% include image_caption.html url="/assets/fundamental.png"
	description="Visualization of the translation problem. The
	declarative specification model usually depicts a graph-like
	structure describing components and relations between them. The
	target structure represents hierarchical blocks of code
	consistently glued together. Most often the original structure
	does not resemble to the resulted one, much rather needs to
	undergo a series of transformations that preserve the declared
	semantics in terms of target mechanisms."  %}

## Motivation & Philosophy

Today's landcape for computing architectures is certainly not
stagnant. [The end of Moore's
Law](https://doi.org/10.1109/MCSE.2017.29) has pushed platform vendors
into finding new and ingenious solutions for transforming silicon into
raw performance, especially in niche application areas such as
telecom, AI, automotive, graphics, security, etc. With these solutions
come a plethora of vendor-specific tools and means to exploit this
performance, such as instruction sets, domain specific languages,
programming frameworks, runtimes, compilers, synthesizers,
etc. Designing complex systems based on multi-vendor platforms,
however, is crippled by a lack of a common design paradigm with proper
tool support due to various reasons:

- most vendor solutions are designed in-house based on strict, often
  undocumented assumptions on the underlying architecture and/or are
  motivated by keeping a competitive edge on the market;
  
- despite recent advances in research and promising preliminary
  results, there are still no generic resource-conscious end-to-end
  solutions based on formal (target-agnostic) computation models, most
  either working within a theoretical framework or being demonstrated
  on small or general purpose platforms;

- despite attempts at standardizing programming models for certain
  application domains (e.g., parallel computing), generic/unified
  frameworks [seldomly display a clear
  advantage](https://doi.org/10.1145/3529538.3529980) as compared with
  vendor-specific counterparts, most often sacrificing performance for
  generality and portability.

Acknowledging both research and industrial efforts to bridge system
(behavioral) models to computational platforms, ZOTI approaches this
problem from a pragmatic perspective: to provide a development
environment to combine methods *that work*[^1] in a systematic and
traceable manner for transforming *declarative specifications*[^2]
into *efficient implementations*[^3]. As such, ZOTI is devoted to
three key principles:

[^1]: i.e., that have been succesfully used, are well-known or have been proven to give good results.

[^2]: possibly resulted from a model-based design space exploration, or any other methodology that analyzes tradeoffs and takes educated design decisions.

[^3]: i.e., comparable or even origninating from hand-crafted code.

Abstraction comes at a high price.
: The effort of describing a transformational synthesis flow from
  specification components to code is justified when conventional
  means of abstraction (i.e. technology stacks, runtime libraries,
  etc.) imply an unacceptable performance loss. Otherwise reusing
  existing (possibly platform-specific) high-level constructs is
  advised in favor of "reinventing the wheel".
	
Be a cog in a larger machinery.
: In order to be of any use in system design and development, ZOTI
  focuses on solving a clearly-delimited, relatively small problem:
  target code generation. That way not only does the methodology
  become a scrutinizable and validatable process, but it clearly
  transfers responsibility for decision-making to other components in
  the larger design flow: model-based design space exploration
  upstream and platform-speific CAD tools (e.g., compilers)
  downstream.
	
Do one thing and do it well.
: Although sketched above as a small and well-delimited task, target
  code gereration is by far non-trivial and can differ drastically for
  various targets. ZOTI is founded on the reasoning that the strength
  of a methodology lies in the ability to decompose a large problem
  into small and understandable sub-problems. As such, by design, each
  tool in the ZOTI suite is developed as an independent tool
  ultra-specialized in solving or aiding in one translation
  sub-problem alone, whereas data is being passed between tools in
  standard serialized formats (e.g. JSON, YAML).


## Further Reading

To get a glimpse in the current state of the ZOTI suite, visit the
[Overview](overview) page, which briefly presents the available tools,
their role and relation with one another, as well as guidelines on how
to design code synthesis flows.

Each tool is documented individually in its own web page, accessible
through the navigation menu in the left.

A [toy example](example) showcases the current features and usage of
the ZOTI tools, and can be read as a tutorial. Being an independent
project though, it is minimally cross-referenced and it assumes the
reader can navigate on her own to extract relevant information from
each tool's documentation page.

---
