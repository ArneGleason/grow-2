<CsoundSynthesizer>
<CsOptions>
</CsOptions>
<CsInstruments>
sr = 44100
ksmps = 64
nchnls = 2
0dbfs = 1

; palette: voice
; a vowel-like tone: a buzzing source through three formant bandpasses
instr 1
  ifreq = p4
  iamp = p5
  if1 = p6
  if2 = p7
  kenv linseg 0, 0.15, 1, p3 - 0.4, 1, 0.25, 0
  kvib oscil 3, 5.5, 1
  asrc vco2 iamp, ifreq + kvib
  a1 butbp asrc, if1, if1 * 0.15
  a2 butbp asrc, if2, if2 * 0.15
  a3 butbp asrc, 2800, 400
  amix = (a1 * 1.2 + a2 * 0.8 + a3 * 0.3) * kenv
  aL, aR pan2 amix, 0.5
  outs aL, aR
endin

</CsInstruments>
<CsScore>
f1 0 16384 10 1
; start dur freq amp formant1 formant2
i1 0.0 2.0 147 0.6 650 1100
i1 2.5 1.5 165 0.6 400 1900
i1 4.5 2.5 131 0.6 300 870
i1 7.5 1.5 196 0.5 730 1090
i1 9.5 3.0 123 0.6 440 1020
e
</CsScore>
</CsoundSynthesizer>
