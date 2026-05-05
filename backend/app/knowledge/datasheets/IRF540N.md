# IRF540N
Power N-channel MOSFET commonly used for medium-current low-side switching demonstrations.

## Pin Map
TO-220 front view is typically 1 gate, 2 drain, 3 source, with the tab connected to drain. Confirm insulation when mounting to metal hardware.

## Absolute Maximums
Gate-source voltage, drain-source voltage, pulsed current, continuous current, and thermal limits must stay within the selected vendor rating. A breadboard cannot safely carry the headline current rating.

## Typical Use
Low-side switching of lamps, motors, solenoids, and resistive loads when the gate drive is high enough for the required current.

## Common Faults
Using 3.3 V logic as if the MOSFET were fully enhanced, no flyback diode on motor or relay loads, source not grounded, tab accidentally shorting to another node, and overheating from high Rds(on) at low Vgs.
