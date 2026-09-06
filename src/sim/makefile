# Builds the simulator-facing probe with a plain compiler -- no Pin, no harness.
# That is the point: if this only built inside a pintool, the claim that these
# structures drop into CXLRAMSim would be hollow.
CXX      ?= g++
CXXFLAGS ?= -std=c++17 -O2 -Wall -Wextra

hotskew_sim: standalone_driver.cpp hotskew_probe.hpp \
             ../profiler/pintool/counter_table.hpp ../profiler/pintool/tracker.hpp
	$(CXX) $(CXXFLAGS) -o $@ standalone_driver.cpp

.PHONY: test clean
test: hotskew_sim
	./hotskew_sim --self-test

clean:
	rm -f hotskew_sim
