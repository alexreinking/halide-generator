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
# Helper functions
###

get_gen_name = $(firstword $(subst _, ,$(1)))

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
HLGEN_SHARED_LIB_EXT = so
HLGEN_PCH_EXT = gch

HLGEN_PCH = $(HLGEN_KERNEL_PATH)/stdafx.h

HLGEN_DEPS = $(HALIDE_DISTRIB_PATH)/bin/libHalide.so $(HLGEN_PCH) $(HALIDE_DISTRIB_PATH)/tools/GenGen.cpp
HLGEN_CXXFLAGS = $(CXXFLAGS) -Og -ggdb3 -fno-rtti
HLGEN_LIBS = -L "$(HALIDE_DISTRIB_PATH)/lib" -lHalide -lz -lpthread -ldl

$(HLGEN_KERNEL_PATH): ; mkdir $@

.PRECIOUS: $(HLGEN_PCH)
$(HLGEN_PCH): $(HALIDE_DISTRIB_PATH)/include/Halide.h | $(HLGEN_KERNEL_PATH)
	$(file >$@,#include "$<")
	$(CXX) $@ -o $@.gch -I "$(HALIDE_DISTRIB_PATH)/include" $(HLGEN_CXXFLAGS)

.PRECIOUS: $(HLGEN_EXE)
$(HLGEN_EXE): $(wildcard *.gen.cpp) $(HLGEN_DEPS)
	$(CXX) -rdynamic $(filter-out %.h, $^) -include $(HLGEN_PCH) -o $@ -I "$(HALIDE_DISTRIB_PATH)/include" $(HLGEN_CXXFLAGS) $(HLGEN_LIBS)

.PRECIOUS: $(HLGEN_KERNEL_PATH)/%.a $(HLGEN_KERNEL_PATH)/%.h $(HLGEN_KERNEL_PATH)/%.stmt $(HLGEN_KERNEL_PATH)/%.html $(HLGEN_KERNEL_PATH)/%.registration.cpp
$(HLGEN_KERNEL_PATH)/%.a \
$(HLGEN_KERNEL_PATH)/%.h \
$(HLGEN_KERNEL_PATH)/%.stmt \
$(HLGEN_KERNEL_PATH)/%.html \
$(HLGEN_KERNEL_PATH)/%.registration.cpp: $(HLGEN_EXE) | $(HLGEN_KERNEL_PATH)
	./$< -g $(call get_gen_name, $*) -e static_library,h,stmt,html,registration -n $* -o $(HLGEN_KERNEL_PATH) target=$(HL_TARGET) $(CFG__$*)

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
	$(CXX) -rdynamic -c $< -include $(HLGEN_PCH) -o $@ -I "$(HALIDE_DISTRIB_PATH)/include" $(HLGEN_CXXFLAGS) $(HLGEN_LIBS) -ljpeg -lpng

run_%: $(HLGEN_KERNEL_PATH)/%.registration.cpp $(HLGEN_KERNEL_PATH)/RunGenMain.o $(HLGEN_KERNEL_PATH)/%.a $(HLGEN_PCH)
	$(CXX) -rdynamic $(filter-out %.h, $^) -include $(HLGEN_PCH) -o $@ -I "$(HALIDE_DISTRIB_PATH)/include" $(HLGEN_CXXFLAGS) $(HLGEN_LIBS) -ljpeg -lpng

###
# Cleanup
###

.PHONY: clean
clean::
	$(RM) -r $(HLGEN_KERNEL_PATH)
	$(RM) $(HLGEN_EXE) run_*
