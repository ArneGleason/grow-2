<CsoundSynthesizer>
<CsOptions>
</CsOptions>
<CsInstruments>
sr = 44100
ksmps = 64
nchnls = 2
0dbfs = 1

; palette: texture
; a granular cloud that thickens and thins
instr 1
  idens0 = p4
  idens1 = p5
  ipitch = p6
  kamp linseg 0, 2, 0.18, p3 - 4, 0.18, 2, 0
  kdens line idens0, p3, idens1
  kpoff = ipitch * 0.5
  asig grain kamp, ipitch, kdens, 0.1, kpoff, 0.08, 1, 2, 0.2
  asig butlp asig, 3000
  aL, aR pan2 asig, 0.5
  outs aL, aR
endin

</CsInstruments>
<CsScore>
f1 0 16384 10 1
f2 0 1024 20 2 1
; start dur dens0 dens1 pitch
i1 0 14 20 120 180
i1 3 9 8 40 360
e
</CsScore>
</CsoundSynthesizer>
