# Simulate the reset mechanism of Begin-End fragment protocol

Simulates the sequence number reset mechanism in `draft-mosko-icnrg-beginendfragment-01`.  This mechanism ensures that
both sides of an Ethernet connection start or reset their sequence numbers correctly.

## Files
The `simulator/` directory is the discrete event simulator.  It's a basic hand-crafted message passing discrete event simulator.

Simulation executables:

* `sim_initialization.py`: Runs 1000 trials with different random number seeds for syncing two fresh nodes.
* `sim_reboot.py`: Runs trials of syncing two nodes, passing data, then rebooting one or more of the nodes.

## Usage

    python sim_x.py

## Diagrams

The state diagram (StateDiagram.pdf) is created using yEd (https://www.yworks.com/products/yed) and the source
file is in diagrams/StateDiagram.graphml.

For use in the RFC draft, we manually translated the states to Graph::Easy (http://bloodgate.com/perl/graph/manual)
format and separated some states to make it fit as ASCII art.  These are in diagrams/state{123}.eg.  The
script diagrams/gengraphs.sh shows the command lines to generate the ASCII art.  We then manually edited
the generated ASCII art for more compactness to fit in the RFC draft line width.
