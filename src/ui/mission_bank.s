; Mission planning lives in bank 24; callers include banked AI in bank 23.
.export _ai_mission_begin, _ai_mission_score, _ai_mission_reset
.import _ai_mission_begin_banked, _ai_mission_score_banked, _ai_mission_reset_banked
.bss
saved_bank: .res 1
.code
.proc select_bank
    pha
    lda $00
    sta saved_bank
    lda #24
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
.proc _ai_mission_begin
    jsr select_bank
    jsr _ai_mission_begin_banked
    jmp restore_bank
.endproc
.proc _ai_mission_score
    jsr select_bank
    jsr _ai_mission_score_banked
    jmp restore_bank
.endproc
.proc _ai_mission_reset
    jsr select_bank
    jsr _ai_mission_reset_banked
    jmp restore_bank
.endproc
