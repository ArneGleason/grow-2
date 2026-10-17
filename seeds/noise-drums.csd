<CsoundSynthesizer>
<CsOptions>
</CsOptions>
<CsInstruments>
sr = 44100
ksmps = 64
nchnls = 2
0dbfs = 1

; a kick and a filtered noise hit
instr 1
  iamp = p4
  kenv expseg 1, 0.25, 0.001
  kpitch expseg 160, 0.08, 50
  asig oscil kenv * iamp, kpitch, 1
  outs asig, asig
endin

instr 2
  iamp = p4
  icf = p5
  ipan = p6
  kenv expseg 1, p3, 0.001
  anoise rand iamp
  afilt butbp anoise, icf, icf * 0.5
  aL, aR pan2 afilt * kenv, ipan
  outs aL, aR
endin

</CsInstruments>
<CsScore>
f1 0 16384 10 1
; kick: start dur amp
i1 0.0 0.3 0.7
i1 1.0 0.3 0.7
i1 1.75 0.3 0.5
i1 2.0 0.3 0.7
i1 3.0 0.3 0.7
i1 4.0 0.3 0.7
i1 5.0 0.3 0.7
i1 5.75 0.3 0.5
i1 6.0 0.3 0.7
i1 7.0 0.3 0.7
i1 8.0 0.3 0.7
i1 9.0 0.3 0.7
i1 9.5 0.3 0.4
i1 10.0 0.3 0.7
i1 11.0 0.3 0.7
; noise: start dur amp cutoff pan
i2 0.5 0.15 0.4 3000 0.3
i2 1.5 0.15 0.4 3000 0.7
i2 2.5 0.15 0.4 3000 0.3
i2 3.5 0.4 0.3 6000 0.7
i2 4.5 0.15 0.4 3000 0.3
i2 5.5 0.15 0.4 3000 0.7
i2 6.5 0.15 0.4 3000 0.3
i2 7.5 0.4 0.3 6000 0.7
i2 8.5 0.15 0.4 3000 0.3
i2 9.5 0.15 0.4 3000 0.7
i2 10.5 0.15 0.4 3000 0.3
i2 11.5 0.8 0.3 1200 0.5
e
</CsScore>
</CsoundSynthesizer>
