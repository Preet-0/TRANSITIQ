# Scientific Methods

## Input and provenance
Time, flux, uncertainty (optional), and quality flags are validated. Invalid times/flux, non-positive flux, nonzero quality flags, duplicate times, and malformed arrays are handled explicitly. Data are sorted by time. The uploaded or downloaded original curve remains separately available. Archive source/product, target, mission, and user settings are attached as provenance when known.

## Baseline and transit preservation
The default detrending estimates a median-filter baseline. It iteratively masks negative residuals so brief dips do not lower the baseline. The cleaned series is original flux divided by baseline. This guards against common attenuation but is not universally safe: broad/long transits, dense transit trains, or windows comparable to a period can still bias a baseline. Run injection/recovery at representative period/depth and compare attenuated depth before interpreting a candidate.

## BLS measurements
Astropy BLS searches configurable periods and box durations. Period is in days, duration in hours, depth as fractional flux and ppm, epoch in the input time coordinate, and power as the Astropy periodogram statistic. The displayed S/N is an approximate depth divided by robust scatter times square root of in-transit samples; it is not a formal significance. Event counts and event depths are approximate and cadence-dependent.

## Vetting
Odd/even relative depth mismatch and flux near phase 0.5 are photometric clues only. Multiple weak diagnostics raise a likely-false-positive triage flag; they cannot identify the astrophysical cause. A planet-like flag is not confirmation. External imaging, spectroscopy, or radial-velocity follow-up is not performed.

## Injection experiment
A box-shaped transit with user-specified epoch, period, duration and depth is multiplied into a real supplied/archive flux series. Noise can be varied around the measured scatter. The identical detrending and BLS search code is applied. Recovery is defined in advance as period error ≤2% and relative depth error ≤50%. The grid rate estimates recovery for its injected scenarios only and must never be reported as real-star classification accuracy.


## Transit Least Squares verification
The optional verification action runs Transit Least Squares on the same cleaned samples and selected period bounds. TLS uses a limb-darkened transit template and returns an independent period, epoch, duration, depth, SDE and S/N. Depth is converted from the TLS best-fit in-transit normalized flux to a fractional drop. BLS/TLS review warnings are shown when period differs by more than 2% or depth by more than 50%; these tolerances prompt review and do not establish correctness. TLS can be expensive and may return diagnostic warnings on short/noisy data; BLS remains available.
