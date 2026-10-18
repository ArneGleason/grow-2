<CsoundSynthesizer>
<CsOptions>
</CsOptions>
<CsInstruments>
sr = 44100
ksmps = 64
nchnls = 2
0dbfs = 1

; palette: pad
; a wide detuned pad that opens and closes slowly
instr 1
  ifreq = p4
  iamp = p5
  kenv linseg 0, 1.5, 1, p3 - 3, 1, 1.5, 0
  a1 vco2 iamp * 0.3, ifreq
  a2 vco2 iamp * 0.3, ifreq * 1.006
  a3 vco2 iamp * 0.3, ifreq * 0.994
  a4 vco2 iamp * 0.2, ifreq * 2.003
  kcut linseg 400, p3 * 0.5, 2200, p3 * 0.5, 500
  afilt moogladder a1 + a2 + a3 + a4, kcut, 0.2
  klfo oscil 0.3, 0.13, 1
  aL, aR pan2 afilt * kenv, 0.5 + klfo
  outs aL, aR
endin

</CsInstruments>
<CsScore>
f1 0 16384 10 1
; start dur freq amp
i1 0 8 130.8 0.4
i1 0 8 196 0.3
i1 8 8 116.5 0.4
i1 8 8 174.6 0.3
e
</CsScore>
</CsoundSynthesizer>
