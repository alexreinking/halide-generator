###
# Global settings
###

CXX=g++
CXXFLAGS=-O3 -g3 -std=c++14

###
# Halide configuration options
###

HALIDE_DISTRIB_PATH ?= /opt/halide
HL_TARGET ?= host

HLGEN_KERNEL_PATH ?= ./kernels
HLGEN_EXE ?= hlgen

###
# Detect Halide installation
###

ifeq (,$(wildcard $(HALIDE_DISTRIB_PATH)))
ifeq (file,$(origin HALIDE_DISTRIB_PATH))
$(warning Environment variable HALIDE_DISTRIB_PATH not set)
endif
$(error No Halide installation found at $(HALIDE_DISTRIB_PATH))
endif

###
# Generator targets
###

# TODO: detect shared lib extension
HLGEN_HALIDE_PCH = $(HLGEN_KERNEL_PATH)/Halide.gen.pch
HLGEN_GENERATOR_DEPS = $(HALIDE_DISTRIB_PATH)/bin/libHalide.so $(HLGEN_HALIDE_PCH) $(HALIDE_DISTRIB_PATH)/tools/GenGen.cpp
HLGEN_GENERATOR_CXXFLAGS = $(CXXFLAGS) -Og -ggdb3 -fno-rtti
HLGEN_GENERATOR_LIBS = -L "$(HALIDE_DISTRIB_PATH)/lib" -lHalide -lz -lpthread -ldl

$(HLGEN_KERNEL_PATH): ; mkdir $@

.PRECIOUS: $(HLGEN_HALIDE_PCH)
$(HLGEN_HALIDE_PCH): $(HALIDE_DISTRIB_PATH)/include/Halide.h | $(HLGEN_KERNEL_PATH)
	$(CXX) $^ -o $@ -I "$(HALIDE_DISTRIB_PATH)/include" $(HLGEN_GENERATOR_CXXFLAGS)

.PRECIOUS: $(HLGEN_EXE)
$(HLGEN_EXE): $(wildcard *.gen.cpp) $(HLGEN_GENERATOR_DEPS)
	$(CXX) -rdynamic $(filter-out %.h %.pch,$^) -o $@ -I "$(HALIDE_DISTRIB_PATH)/include" $(HLGEN_GENERATOR_CXXFLAGS) $(HLGEN_GENERATOR_LIBS)

.PRECIOUS: $(HLGEN_KERNEL_PATH)/%.registration.cpp
$(HLGEN_KERNEL_PATH)/%.a \
$(HLGEN_KERNEL_PATH)/%.h \
$(HLGEN_KERNEL_PATH)/%.stmt \
$(HLGEN_KERNEL_PATH)/%.html \
$(HLGEN_KERNEL_PATH)/%.registration.cpp: $(HLGEN_EXE) | $(HLGEN_KERNEL_PATH)
	./$< -g $* -e static_library,h,stmt,html,registration -o $(HLGEN_KERNEL_PATH) target=$(HL_TARGET)

###
# Standalone runner targets
###

$(HLGEN_KERNEL_PATH)/RunGenMain.o: $(HALIDE_DISTRIB_PATH)/tools/RunGenMain.cpp $(HLGEN_HALIDE_PCH)
	$(CXX) -rdynamic -c $< -o $@ -I "$(HALIDE_DISTRIB_PATH)/include" $(HLGEN_GENERATOR_CXXFLAGS) $(HLGEN_GENERATOR_LIBS) -ljpeg -lpng

run_%: $(HLGEN_KERNEL_PATH)/%.registration.cpp $(HLGEN_KERNEL_PATH)/RunGenMain.o $(HLGEN_KERNEL_PATH)/%.a $(HLGEN_HALIDE_PCH)
	$(CXX) -rdynamic $(filter-out %.pch, $^) -o $@ -I "$(HALIDE_DISTRIB_PATH)/include" $(HLGEN_GENERATOR_CXXFLAGS) $(HLGEN_GENERATOR_LIBS) -ljpeg -lpng

###
# Cleanup
###

.PHONY: hlgen_clean
hlgen_clean:
	$(RM) -r $(HLGEN_KERNEL_PATH)
	$(RM) $(HLGEN_EXE) run_*

###
# Targets
###

all: ; @echo foo
