# Tutorial

This tutorial goes through the main features of ZOTI-YAML, and is
supposed to complement the [Syntax
Reference](syntax-reference). ZOTI-YAML is an extension of the [YAML
1.1 language](https://yaml.org/spec/1.1/) which supports workflows
based on modules and library imports. To showcase such a workflow, we
set up a toy example in an arbitrary folder where the ZOTI-YAML CLI
tool is accessible. In this example we run the CLI tool as executable
Python module:

```
export ZOTI_YAML=python3 -m zoti_yaml
```

Let a "top" module (i.e., a module which imports and uses nodes from
other modules) called `main.zoml` be defined in the root folder as
follows:

```{literalinclude} ../../tests/scenario1/main.zoml
---
language: yaml
linenos: true
caption: main.zoml
---
```

This module imports two other modules: `mod1`, used with its qualified
name throughout the document (see line `24`), and `sub.mod` called
with an alias `mod2` throughout this document (see line `26`).

To keep this example simple we do not extend `pathvar` (see [Syntax
Reference](syntax-reference)), hence `mod1` needs to be defined in the
same root as the top module:


```{literalinclude} ../../tests/scenario1/mod1.zoml
---
language: yaml
linenos: true
caption: mod1.zoml
---
```

whereas `sub.mod` is defined at the coresponding path:

```{literalinclude} ../../tests/scenario1/sub/mod.zoml
---
language: yaml
linenos: true
caption: sub/mod.zoml
---
```

As seen above, module `sub.mod` references a text file in the same
relative path called `test.txt` and includes raw text from it under
its `contentX` entries, using different directives. This file contains
the following text:

```{literalinclude} ../../tests/scenario1/sub/test.txt
---
caption: sub/test.txt
---
```

Finally, let us define a configuration file in the root of the project
so that we do not need to manually pass the respective CLI arguments:

```{literalinclude} ../../tests/scenario1/zoticonf.toml
---
language: toml
caption: zoticonf.toml
---
```

To process the source files above, we run the command the command:

```
$ZOTI_YAML --verbose --spec=toy --out=toy.yaml main
```

The argument `--verbose` can be used to print out extensive debug
information to `stderr` and can be used to trace every step in the
processing of the source file. It can be ignored for silent
output. Since we declared `main` to be the top module then the output
file `toy.yaml` will contain the following info:

```{literalinclude} ../../tests/scenario1/toy.yaml
---
language: yaml
caption: toy.yaml
linenos: true
---
```

The new preamble has additional information such as the original file
path and a log. Also, notice that every child of `root` and `nodes`
contains an `_info` entry with positional metadata.

The effects of `!default` (in `main.zoml` line `8`) can be seen in the
fact that each 1st level child node (corresponding to the first
argument specification) contains a `mark: DEFAULT_MARKING` entry, as a
result of merging the default values under `!policy:union` (see
[Syntax Reference](syntax-reference)).

The `!ref` command has been resolved each time pointing to a valid
node in the module trees, enabling the `!attach` command to act
accordingly. `!attach` is used in three places, from last to first:

- in `main.zoml` line `25`: attaches the contents of the `n1` node
  from `sub.mod` under the node `n2` in `main`. The behavior of the
  `!include` command in `sub/mod.zoml` lines `10-13` can be seen in
  the result. Notice that `floating-ref` is resolved according to its
  new location (module resolved to `main` instead of `sub.mod`). This
  node also shows an example of passing an argument from the caller to
  the calle using a dedicated field `zoti-args` which is destroyed
  after resolving the document.  Also notice that its metadata
  contains its entire history and previous attributes.
  
- in `main.zoml` line `23`: attaches the `data` entry of node `n_who`
  from `mod1` to the `data` entry of `n1_n2` from `main`. This is seen
  in `toy.yaml` at line `30`. Since the attached node is of type
  string, it does not contain any metadata.

- in `main.zoml` line `19`: attaches the `extra` entry of the sibling
  node `n1_n2` from `main` (implicit) to the `data` entry of node
  `n1_n1_n1` in the same module. This is seen in `toy.yaml` at line
  `25`.

By now, you should have a rough idea of the capabilities of
ZOTI-YAML. While the new commands and their usage might seem like a
mouthful at first, their purpose is simple: to define a generic way of
working with specification trees distributed across multiple files and
libraries (possibly associated with different licenses), and construct
the information into one cohesive JSON tree. In turn, this should
enable any tool downstream to focus on parsing the right information
and construct its core objects irrespective to where information
originated, while also bookkeeping metadata for debugging purposes. As
further shown in the [ZOTI Toy
Example](https://ericsson.github.io/zoti/example), these capabilities
can be used to (minimally) emulate a component framework where
parameters and interfaces can be specified after loading core
components from designated libraries.
