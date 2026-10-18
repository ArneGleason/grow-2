<CsoundSynthesizer>
<CsOptions>
</CsOptions>
<CsInstruments>
sr = 44100
ksmps = 64
nchnls = 2
0dbfs = 1

; palette: plucked
; two slightly detuned plucked strings that ring into a short delay
instr 1
  ifreq = p4
  iamp = p5
  ipan = p6
  kenv linseg 1, p3, 0.0001
  a1 pluck iamp, ifreq, ifreq, 0, 1
  a2 pluck iamp * 0.6, ifreq * 1.003, ifreq, 0, 1
  asig butlp a1 + a2, 3600
  adel delay asig, 0.31
  amix = asig + adel * 0.35
  aL, aR pan2 amix * kenv, ipan
  outs aL, aR
endin

</CsInstruments>
<CsScore>
; start dur freq amp pan
i1 0.0 2.5 220 0.5 0.3
i1 0.7 2.5 330 0.4 0.7
i1 1.9 3.0 261 0.45 0.5
i1 3.2 2.0 392 0.35 0.2
i1 4.1 4.0 196 0.5 0.6
i1 6.0 2.5 349 0.4 0.8
i1 7.4 3.0 294 0.4 0.4
i1 9.0 5.0 165 0.5 0.5
i1 10.5 3.0 247 0.3 0.7
e
</CsScore>
</CsoundSynthesizer>
