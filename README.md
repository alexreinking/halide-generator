# hl - a Halide project generator

This is a simple tool for quickly creating Halide projects and generators with
sane Makefiles. Current features include:

* Create new-style benchmark tools and runners by default.
* Manage multiple configurations per generator
* Precompiled headers for faster incremental builds

Planned features include:

* Merge all configurations into a single static lib with a suitable runtime
* Integrate with the autoscheduler (need upstream support -- weights are not included in the distributions yet)
* Out-of-tree builds

This project is _hours_ old. Therefore expect:

* No support for non-GNU make or cmake
* No macOS support
* No support for compilers other than GCC (and maybe clang)
* Lots of bugs

Feel free to contribute, though I'm rapidly bringing this to alpha.

## Quick demo

Here's the quickest way to see how `hlgen` works: 

    $ hl create project my_project
    $ cd my_project
    $ ls
    Makefile  my_project.gen.cpp
    $ make
    ...
    $ ./run_my_project input=random:0:auto --output_extents=[64,64] --benchmarks=all
    Benchmark for my_project produces best case of 4.49293e-07 sec/iter (over 10 samples, 904060 iterations, accuracy 5%).
    Best output throughput is 8.7e+03 mpix/sec.
    $ ls
    Makefile  kernels/  my_project.gen.cpp  my_project.generator  run_my_project
    $ ls kernels
    RunGenMain.o  my_project.h     my_project.registration.cpp  stdafx.h
    my_project.a  my_project.html  my_project.stmt              stdafx.h.gch

The default pipeline that's generated is a plain image copy. The Makefile automatically generates
a precompiled header that includes just Halide.h. It includes the header via `-include`, which is
supported by GCC and Clang.

**TODO** add a way of specifying additional headers to include in the PCH

## Conventions and project layout

This tool assumes you wish to use Halide in ahead-of-time mode. It will create and manage `.gen.cpp` files, each of
which contain must contain a _single_ generator class. Generators can have multiple configurations, each of which has
a unique identifying name. The C functions are named `<generator>` for the default configuration, and
`<generator>__<config-name>` for other configurations. These names are also used for the library files.

Running `make` will (by default) generate a `run_<configuration>` executable for each configuration specified in the
Makefile. These are based on `RunGenMain.cpp`, a new tool in upstream Halide . Thus the "latest" release available from
Github is **incompatible** with this tool. Intermediate files and libraries are collected in a directory called
`kernels/`. You can also make just the libraries without the runners by calling `make generate_<configuration>`.

To consume the libraries produced by the Makefiles, just run Make recursively.

## Installation

Just clone the repository to some location (maybe `~/bin`) and add it to your path. For example, you could add the
following line to your `~/.profile` or `~/.bashrc`:

    export PATH="$PATH:$HOME/bin/hlgen"

This project can use a system-installed Python 3 since it has no additional Python dependencies.

## Dependencies

* Python 3.4+
* A [recent Halide distribution](https://buildbot.halide-lang.org/) or build (`distrib` target) with the environment
  variable `HALIDE_DISTRIB_PATH` set to the root. You can also install Halide to `/opt/halide` if you don't want to set
  an environment variable.
