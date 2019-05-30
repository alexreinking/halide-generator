# hlgen

This is a simple tool for quickly creating Halide projects and generators with
sane makefiles. Features include:

* Create new-style benchmark tools and runners by default.
* Multiple configurations per generator
* Precompiled headers
* Merging all configurations into a single static lib with a suitable runtime (TODO)
* Integration with the autoscheduler (TODO - need upstream support, too)

This project is _hours_ old. Therefore expect:

* No support for non-GNU make
* No support for compilers other than GCC (and maybe clang)
* Lots of bugs

Feel free to contribute, though I'm rapidly bringing this to alpha.

## Quick demo

Here's the quickest way to see how `hlgen` works: 

    $ hlgen create project my_project
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

**TODO** add a way of letting the user specify additional headers to include in the PCH

## Dependencies

* Python 3.4+
