<CsoundSynthesizer>
<CsOptions>
</CsOptions>
<CsInstruments>
sr = 44100
ksmps = 64
nchnls = 2
0dbfs = 1

; palette: glass
; struck glass: inharmonic partials that ring and beat against each other
instr 1
  ifreq = p4
  iamp = p5
  kenv expseg 1, p3, 0.001
  a1 oscil iamp * 0.5, ifreq, 1
  a2 oscil iamp * 0.3, ifreq * 2.76, 1
  a3 oscil iamp * 0.2, ifreq * 5.4, 1
  a4 oscil iamp * 0.1, ifreq * 8.93, 1
  k2 expseg 1, p3 * 0.6, 0.001
  k3 expseg 1, p3 * 0.35, 0.001
  amix = (a1 + a2 * k2 + (a3 + a4) * k3) * kenv
  aL, aR pan2 amix, 0.5 + 0.4 * sin(ifreq * 0.03)
  outs aL, aR
endin

</CsInstruments>
<CsScore>
f1 0 16384 10 1
; start dur freq amp
i1 0.0 6 523 0.4
i1 1.5 6 659 0.3
i1 3.5 7 392 0.4
i1 6.0 5 784 0.25
i1 8.0 7 440 0.4
i1 10.5 6 587 0.3
e
</CsScore>
</CsoundSynthesizer>
