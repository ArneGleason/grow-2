<CsoundSynthesizer>
<CsOptions>
</CsOptions>
<CsInstruments>
sr = 44100
ksmps = 64
nchnls = 2
0dbfs = 1

; palette: modular drone
; detuned saws and slow partials breathing through a resonant lowpass
instr 1
  ibase = p4
  iamp = p5
  kenv linseg 0, 2.5, 1, p3 - 5, 1, 2.5, 0
  klfo1 oscil 0.6, 0.07, 1
  klfo2 oscil 1.0, 0.11, 1
  a1 vco2 iamp * 0.35, ibase
  a2 vco2 iamp * 0.3, ibase * 1.004 + klfo1
  a3 oscil iamp * 0.25, ibase * 2.01 + klfo2, 1
  a4 oscil iamp * 0.12, ibase * 3.0, 1
  asub oscil iamp * 0.3, ibase * 0.5, 1
  amix = (a1 + a2 + a3 + a4 + asub) * kenv
  kcut oscil 500, 0.05, 1
  afilt moogladder amix, 700 + kcut, 0.35
  aL, aR pan2 afilt, 0.5 + 0.3 * klfo1
  outs aL, aR
endin

</CsInstruments>
<CsScore>
f1 0 16384 10 1
; start dur base amp
i1 0 16 55 0.5
i1 4 12 82.4 0.3
e
</CsScore>
</CsoundSynthesizer>
