; Unbanked gateways preserve C arguments/return values and the caller's bank.
; Only play.c's code and constants are banked; its mutable state stays in MAIN.
.export _play_demo, _play_enter, _play_position, _play_load, _play_resume, _play_update
.import _play_demo_banked, _play_enter_banked, _play_position_banked, _play_load_banked
.import _play_resume_banked, _play_update_banked
.bss
saved_bank: .res 1
.code
.proc select_bank
    pha
    lda $00
    sta saved_bank
    lda #22
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
.macro gateway name, target
.proc name
    jsr select_bank
    jsr target
    jmp restore_bank
.endproc
.endmacro
gateway _play_enter, _play_enter_banked
gateway _play_position, _play_position_banked
gateway _play_load, _play_load_banked
gateway _play_resume, _play_resume_banked
gateway _play_update, _play_update_banked
gateway _play_demo, _play_demo_banked
