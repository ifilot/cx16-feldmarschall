; JOYSTICK_GET: A=port 1..4; returns active-low buttons in A/X and presence in Y.
.export _input_poll_pad
.import _pad_low, _pad_high, _pad_present
.code
.proc _input_poll_pad
    jsr $FF56
    sta _pad_low
    stx _pad_high
    sty _pad_present
    rts
.endproc
