include $(HALIDE_DISTRIB_PATH)/halide_config.make

###
# Halide configuration options
###

HLGEN_KERNEL_PATH ?= ./kernels

_HLGEN_EXE := $(dir $(abspath $(firstword $(MAKEFILE_LIST))))
_HLGEN_EXE := $(notdir $(_HLGEN_EXE:%/=%))
HLGEN_EXE ?= $(_HLGEN_EXE).generator

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
# Helper functions
###

get_gen_name = $(firstword $(subst __, ,$(1)))

###
# Detect user-defined generators
###

HLGEN_CFGS := $(filter CFG__%,$(.VARIABLES))
HLGEN_CFGS := $(HLGEN_CFGS:CFG__%=%)
HLGEN_EXCLUDE := $(foreach CFG,$(HLGEN_CFGS),$(call get_gen_name,$(CFG)))
HLGEN_CFGS := $(sort $(HLGEN_CFGS) $(filter-out $(HLGEN_EXCLUDE), $(patsubst %.gen.cpp,%,$(wildcard *.gen.cpp))))

HLGEN_GENS := $(sort $(foreach O,$(HLGEN_CFGS),$(call get_gen_name, $(O))))

HLGEN_MISSING := $(filter-out $(wildcard *.gen.cpp), $(HLGEN_GENS:=.gen.cpp))
ifneq (,$(HLGEN_MISSING))
$(warning Detected configurations: $(HLGEN_CFGS))
$(error Missing .gen.cpp for generators: $(HLGEN_MISSING))
endif

.PHONY: allcfgs
allcfgs: $(addprefix run_, $(HLGEN_CFGS))

###
# Generator targets
###

# TODO: detect these
ifeq ($(OS),Windows_NT)
	$(error "Windows builds not yet supported")
else
HLGEN_OS := $(shell uname -s)
ifeq ($(HLGEN_OS),Linux)
HLGEN_SHARED_LIB_EXT := so
USE_EXPORT_DYNAMIC := -rdynamic
endif
ifeq ($(HLGEN_OS),Darwin)
HLGEN_SHARED_LIB_EXT := dylib
USE_EXPORT_DYNAMIC := -undefined dynamic_lookup
endif
endif
HLGEN_PCH_EXT = gch

HLGEN_PCH = $(HLGEN_KERNEL_PATH)/stdafx.hpp

HLGEN_DEPS = $(HALIDE_DISTRIB_PATH)/bin/libHalide.$(HLGEN_SHARED_LIB_EXT) $(HLGEN_PCH) $(HALIDE_DISTRIB_PATH)/tools/GenGen.cpp
HLGEN_CXXFLAGS = $(CXXFLAGS) -Og -ggdb3 -fno-rtti
HLGEN_LIBS = -L "$(HALIDE_DISTRIB_PATH)/lib" -lHalide -lz -lpthread -ldl

$(HLGEN_KERNEL_PATH): ; mkdir $@

.PRECIOUS: $(HLGEN_PCH)
$(HLGEN_PCH): $(HALIDE_DISTRIB_PATH)/include/Halide.h | $(HLGEN_KERNEL_PATH)
#	$(file >$@,#include "$<")
	echo '#include "$<"' > "$@"
	$(CXX) $@ -o $@.gch -I "$(HALIDE_DISTRIB_PATH)/include" $(HLGEN_CXXFLAGS)


.PRECIOUS: $(HLGEN_KERNEL_PATH)/%.gen.o
$(HLGEN_KERNEL_PATH)/%.gen.o: %.gen.cpp $(HLGEN_PCH)
	$(CXX) -c $< -include $(HLGEN_PCH) -o $@ -I $(HALIDE_DISTRIB_PATH)/include $(HLGEN_CXXFLAGS)

HLGEN_EXE_FILTERS = %.hpp %.h %.$(HLGEN_SHARED_LIB_EXT)

.PRECIOUS: $(HLGEN_EXE)
$(HLGEN_EXE): $(HLGEN_GENS:%=$(HLGEN_KERNEL_PATH)/%.gen.o) $(HLGEN_DEPS)
	$(CXX) $(USE_EXPORT_DYNAMIC) $(filter-out $(HLGEN_EXE_FILTERS), $^) -include $(HLGEN_PCH) -o $@ -I $(HALIDE_DISTRIB_PATH)/include $(HLGEN_CXXFLAGS) $(HLGEN_LIBS)

.SECONDEXPANSION:
.PRECIOUS: $(HLGEN_KERNEL_PATH)/%.a $(HLGEN_KERNEL_PATH)/%.h $(HLGEN_KERNEL_PATH)/%.stmt $(HLGEN_KERNEL_PATH)/%.html $(HLGEN_KERNEL_PATH)/%.registration.cpp
$(HLGEN_KERNEL_PATH)/%.a \
$(HLGEN_KERNEL_PATH)/%.h \
$(HLGEN_KERNEL_PATH)/%.stmt \
$(HLGEN_KERNEL_PATH)/%.html \
$(HLGEN_KERNEL_PATH)/%.registration.cpp: $$(call get_gen_name, $$*).gen.cpp | $(HLGEN_EXE) $(HLGEN_KERNEL_PATH)
	./$(HLGEN_EXE) -g $(call get_gen_name, $*) -e static_library,h,stmt,html,registration -n $* -o $(HLGEN_KERNEL_PATH) target=$(HL_TARGET) $(CFG__$*)

###
# Standalone generator targets
###

.PHONY: _hl_generate_target
_hl_generate_target:

generate_%: $(HLGEN_KERNEL_PATH)/%.a _hl_generate_target ;

###
# Standalone runner targets
###

$(HLGEN_KERNEL_PATH)/RunGenMain.o: $(HALIDE_DISTRIB_PATH)/tools/RunGenMain.cpp $(HLGEN_PCH)
	$(CXX) -c $< -include $(HLGEN_PCH) -o $@ -I "$(HALIDE_DISTRIB_PATH)/include" $(HLGEN_CXXFLAGS)

run_%: $(HLGEN_KERNEL_PATH)/%.registration.cpp $(HLGEN_KERNEL_PATH)/RunGenMain.o $(HLGEN_KERNEL_PATH)/%.a $(HLGEN_PCH)
	$(CXX) $(USE_EXPORT_DYNAMIC) $(filter-out $(HLGEN_EXE_FILTERS), $^) -include $(HLGEN_PCH) -o $@ -I "$(HALIDE_DISTRIB_PATH)/include" $(HLGEN_CXXFLAGS) $(HLGEN_LIBS) -ljpeg -lpng

###
# Cleanup
###

.PHONY: clean
clean::
	$(RM) -r $(HLGEN_KERNEL_PATH)
	$(RM) -r $(HLGEN_EXE) run_*
