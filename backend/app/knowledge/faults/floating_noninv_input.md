# Floating Non-Inverting Input

Fault id: floating_noninv_input. In an inverting op-amp amplifier, the non-inverting input is the reference node. If it floats or sits away from 0 V, the op-amp sees a false differential input and can drive the output into a supply rail. Confirm by measuring V_noninv with respect to circuit ground. If V_noninv is not near 0 V, power down, tie the non-inverting input to ground, then retest Vout.
