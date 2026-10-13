; AI gateways are separate from the play gateways: play calls AI while banked.
.export _ai_move, _ai_reset
.import _ai_move_banked, _ai_reset_banked
.bss
saved_bank: .res 1
.code
.proc select_bank
    pha
    lda $00
    sta saved_bank
    lda #23
    sta $00
    pla
    rts
.endproc
.proc restore_bank
    pha
    lda saved_bank
    sta $00
    pla
    rts
.endproc
.proc _ai_move
    jsr select_bank
    jsr _ai_move_banked
    jmp restore_bank
.endproc
.proc _ai_reset
    jsr select_bank
    jsr _ai_reset_banked
    jmp restore_bank
.endproc
