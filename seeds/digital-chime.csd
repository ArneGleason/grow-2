<CsoundSynthesizer>
<CsOptions>
</CsOptions>
<CsInstruments>
sr = 44100
ksmps = 64
nchnls = 2
0dbfs = 1

; palette: digital
; soft FM chimes with a slow lowpass and a short delay
instr 1
  ifreq = p4
  iamp = p5
  iratio = p6
  iindex = p7
  kenv expseg 1, p3, 0.002
  kidx = iindex * kenv
  asig foscil iamp, ifreq, 1, iratio, kidx, 1
  asig butlp asig * kenv, 2600
  adel delay asig, 0.37
  amix = asig + adel * 0.3
  ipan = 0.5 + 0.35 * sin(ifreq)
  aL, aR pan2 amix, ipan
  outs aL, aR
endin

</CsInstruments>
<CsScore>
f1 0 16384 10 1
; start dur freq amp ratio index
i1 0.0 5.0 330 0.4 2.0 1.2
i1 2.0 6.0 495 0.3 3.0 0.8
i1 4.5 6.0 247 0.4 2.0 1.5
i1 7.0 4.0 660 0.25 1.5 0.9
i1 9.0 6.0 220 0.4 2.0 1.8
i1 11.5 5.0 392 0.3 3.0 0.7
e
</CsScore>
</CsoundSynthesizer>
