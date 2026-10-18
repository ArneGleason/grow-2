<CsoundSynthesizer>
<CsOptions>
</CsOptions>
<CsInstruments>
sr = 44100
ksmps = 64
nchnls = 2
0dbfs = 1

; palette: percussive
; a kick with body, a snare of tone and noise, and a hat
instr 1
  iamp = p4
  kenv expseg 1, 0.35, 0.001
  kpitch expseg 170, 0.09, 48
  asig oscil kenv * iamp, kpitch, 1
  aclick rand iamp * 0.3
  kcl expseg 1, 0.01, 0.001
  asig = asig + aclick * kcl
  outs asig, asig
endin

instr 2
  iamp = p4
  kenv expseg 1, p3, 0.001
  abody oscil iamp * 0.5, 190, 1
  ktone expseg 1, 0.08, 0.01
  anoise rand iamp
  afilt butbp anoise, 2800, 2200
  amix = abody * ktone + afilt * kenv * 0.9
  aL, aR pan2 amix, 0.45
  outs aL, aR
endin

instr 3
  iamp = p4
  ipan = p5
  kenv expseg 1, p3, 0.001
  anoise rand iamp
  afilt buthp anoise, 6500
  aL, aR pan2 afilt * kenv, ipan
  outs aL, aR
endin

</CsInstruments>
<CsScore>
f1 0 16384 10 1
; kick: start dur amp
i1 0.0 0.35 0.7
i1 1.0 0.35 0.7
i1 1.75 0.35 0.5
i1 2.0 0.35 0.7
i1 3.0 0.35 0.7
i1 4.0 0.35 0.7
i1 5.0 0.35 0.7
i1 5.75 0.35 0.5
i1 6.0 0.35 0.7
i1 7.0 0.35 0.7
; snare: start dur amp
i2 0.5 0.25 0.5
i2 1.5 0.25 0.5
i2 2.5 0.25 0.5
i2 3.5 0.4 0.45
i2 4.5 0.25 0.5
i2 5.5 0.25 0.5
i2 6.5 0.25 0.5
i2 7.5 0.6 0.5
; hat: start dur amp pan
i3 0.25 0.08 0.25 0.3
i3 0.75 0.08 0.2 0.7
i3 1.25 0.08 0.25 0.3
i3 1.75 0.08 0.2 0.7
i3 2.25 0.08 0.25 0.3
i3 2.75 0.08 0.2 0.7
i3 3.25 0.08 0.25 0.3
i3 3.75 0.2 0.3 0.5
i3 4.25 0.08 0.25 0.3
i3 4.75 0.08 0.2 0.7
i3 5.25 0.08 0.25 0.3
i3 5.75 0.08 0.2 0.7
i3 6.25 0.08 0.25 0.3
i3 6.75 0.08 0.2 0.7
i3 7.25 0.08 0.25 0.3
i3 7.75 0.3 0.3 0.5
e
</CsScore>
</CsoundSynthesizer>
