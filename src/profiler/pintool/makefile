# Standalone makefile for the hotskew pintool.
#
#   make PIN_ROOT=/path/to/pin
#
# PIN_ROOT may also come from the environment (experiments/env.sh sets it).

ifndef PIN_ROOT
$(error PIN_ROOT is not set. Try: make PIN_ROOT=$$HOME/pin)
endif

CONFIG_ROOT := $(PIN_ROOT)/source/tools/Config
include $(CONFIG_ROOT)/makefile.config

TOOL_ROOTS := hotskew

include $(TOOLS_ROOT)/Config/makefile.default.rules

# Our headers live next to the .cpp.
$(OBJDIR)hotskew$(OBJ_SUFFIX): hotskew.cpp cache_model.hpp counter_table.hpp
