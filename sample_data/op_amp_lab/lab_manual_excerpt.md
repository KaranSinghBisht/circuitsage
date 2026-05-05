# Inverting Op-Amp Amplifier Lab

Aim: Verify that an inverting op-amp amplifier produces an output voltage Vout = -(Rf/Rin) Vin.

For this lab, use Rin = 10kΩ and Rf = 47kΩ. The expected gain is -4.7.

The non-inverting input must be connected to circuit ground. With negative feedback, the inverting input behaves like a virtual ground.

Before debugging gain, check:
1. Positive and negative supply rails.
2. Common ground between function generator, oscilloscope, and circuit.
3. Non-inverting input connected to ground.
4. Feedback resistor connected between output and inverting input.

If the output saturates near a supply rail, likely causes include missing feedback, floating input reference, incorrect op-amp power pins, or input amplitude too large.

