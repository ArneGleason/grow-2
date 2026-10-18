<CsoundSynthesizer>
<CsOptions>
</CsOptions>
<CsInstruments>
sr = 44100
ksmps = 64
nchnls = 2
0dbfs = 1

; palette: digital
; a gated pulse wave ticking through a bandpass, like a wire humming
instr 1
  ifreq = p4
  iamp = p5
  icf = p6
  kenv expseg 1, p3, 0.01
  kgate lfo 1, 6, 3
  apulse vco2 iamp, ifreq, 2, 0.3
  afilt butbp apulse, icf, icf * 1.2
  amix = (afilt * 1.5 + apulse * 0.15) * kenv * (0.35 + 0.65 * kgate)
  aL, aR pan2 amix, 0.5 + 0.3 * sin(ifreq * 0.01)
  outs aL, aR
endin

</CsInstruments>
<CsScore>
; start dur freq amp cutoff
i1 0.0 1.5 220 0.4 1200
i1 1.5 1.5 220 0.4 1800
i1 3.0 1.5 293 0.4 1500
i1 4.5 1.5 220 0.4 2400
i1 6.0 1.5 330 0.4 1200
i1 7.5 1.5 220 0.4 2000
i1 9.0 3.0 165 0.4 900
e
</CsScore>
</CsoundSynthesizer>
