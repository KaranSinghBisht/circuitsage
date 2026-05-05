% Scope capture analysis
fs = 1000;
t = 0:1/fs:1;
vin = sin(2*pi*10*t);
vout = 0.4 * vin;
plot(t, vin);
plot(t, vout);
