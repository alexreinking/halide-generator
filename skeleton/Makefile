###
# Global settings
###

CXX=g++
CXXFLAGS=-std=c++14

.PHONY: all
all: allcfgs

###
# Configure generators
###

# A "configuration" for a generator GEN is a SUFFIX / PARAMS pair
# that leads to the production of another shared library for GEN 
# with the given PARAMS, named GEN_SUFFIX.
#
# To create a new configuration, create a variable like so:
#
#   CFG__GEN__SUFFIX = [target=...] PARAMS
#
# If you omit the target specifier then HL_TARGET will be used instead.
#
# Note that generators built using these conventions CANNOT contain
# a double underscore in the name.
#
# If you specify a particular configuration, the allcfgs target
# will exclude the default unless you specify it manually, eg.
# 
#   CFG__GEN = 
#
# where the value is CFG__GEN is intentionally left blank.

###
# Include common support Makefile
###

include {{_HLGEN_BASE}}/support/Makefile

