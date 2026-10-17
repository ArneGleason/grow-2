<CsoundSynthesizer>
<CsOptions>
</CsOptions>
<CsInstruments>
sr = 44100
ksmps = 64
nchnls = 2
0dbfs = 1

; slow additive drone with drifting partials
instr 1
  ibase = p4
  iamp = p5
  kenv linseg 0, 3, 1, p3 - 6, 1, 3, 0
  klfo1 oscil 0.6, 0.07, 1
  klfo2 oscil 0.9, 0.11, 1
  a1 oscil iamp * 0.5, ibase, 1
  a2 oscil iamp * 0.3, ibase * 2.01 + klfo1, 1
  a3 oscil iamp * 0.2, ibase * 3.0 + klfo2, 1
  a4 oscil iamp * 0.12, ibase * 4.98, 1
  a5 oscil iamp * 0.08, ibase * 7.02, 1
  amix = (a1 + a2 + a3 + a4 + a5) * kenv
  aL, aR pan2 amix, 0.5 + 0.3 * klfo1
  outs aL, aR
endin

</CsInstruments>
<CsScore>
f1 0 16384 10 1
; start dur base amp
i1 0 16 55 0.5
i1 2 14 82.4 0.3
i1 6 8 110 0.15
e
</CsScore>
</CsoundSynthesizer>
