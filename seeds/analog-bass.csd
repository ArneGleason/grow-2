<CsoundSynthesizer>
<CsOptions>
</CsOptions>
<CsInstruments>
sr = 44100
ksmps = 64
nchnls = 2
0dbfs = 1

; palette: analog
; a saw and a sub through a resonant lowpass, playing a bass line
instr 1
  ifreq = p4
  iamp = p5
  icut = p6
  kenv linseg 1, p3 - 0.05, 0.6, 0.05, 0
  asaw vco2 iamp, ifreq
  asub oscil iamp * 0.6, ifreq * 0.5, 1
  kcut expseg icut, p3, icut * 0.3
  afilt moogladder asaw, kcut, 0.45
  amix = (afilt + asub) * kenv
  aL, aR pan2 amix, 0.5
  outs aL, aR
endin

</CsInstruments>
<CsScore>
f1 0 16384 10 1
; start dur freq amp cutoff
i1 0.00 0.45 55 0.5 1800
i1 0.50 0.2 55 0.3 900
i1 0.75 0.45 82.4 0.4 2400
i1 1.50 0.45 65.4 0.5 3200
i1 2.00 0.2 55 0.3 900
i1 2.25 0.7 110 0.4 2800
i1 3.00 0.45 55 0.5 1800
i1 3.50 0.2 55 0.3 900
i1 3.75 0.45 82.4 0.4 2400
i1 4.50 0.45 65.4 0.5 3200
i1 5.00 0.2 55 0.3 900
i1 5.25 0.7 110 0.4 2800
i1 6.00 0.45 55 0.5 1800
i1 6.50 0.45 73.4 0.4 2200
i1 7.00 1.0 41.2 0.5 1200
e
</CsScore>
</CsoundSynthesizer>
