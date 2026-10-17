<CsoundSynthesizer>
<CsOptions>
</CsOptions>
<CsInstruments>
sr = 44100
ksmps = 64
nchnls = 2
0dbfs = 1

; sparse FM bells with long decays
instr 1
  ifreq = p4
  iamp = p5
  iratio = p6
  iindex = p7
  kenv expseg 1, p3, 0.001
  kidx = iindex * kenv
  asig foscil iamp * kenv, ifreq, 1, iratio, kidx, 1
  ipan = 0.5 + 0.4 * sin(ifreq)
  aL, aR pan2 asig, ipan
  outs aL, aR
endin

</CsInstruments>
<CsScore>
f1 0 16384 10 1
; start dur freq amp ratio index
i1 0.0 6.0 440 0.3 1.41 3.0
i1 2.5 7.0 659 0.2 2.76 2.0
i1 5.0 8.0 330 0.3 1.41 4.0
i1 7.2 5.0 880 0.15 3.5 1.5
i1 9.0 7.0 220 0.3 1.41 5.0
i1 11.0 6.0 523 0.2 2.0 2.5
e
</CsScore>
</CsoundSynthesizer>
