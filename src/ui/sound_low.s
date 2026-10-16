; ZSMKit v1 memory playback; music priority 0, effects priority 1.
; The library's ISR keeps playing during AI searches and restores VERA/banks.
.scope zsmkit
.include "../vendor/zsmkit.inc"
.endscope
.export _sound_engine_init, _sound_music, _sound_stop, _sound_stop_music, _sound_stop_effects, _sound_sfx
.import _sound_effects_enabled, _sound_ready, _sound_last_sfx
.export _sound_shutdown
.bss
saved_bank: .res 1
music_bank: .res 1
.code
.proc _sound_shutdown
    lda _sound_ready
    beq done
    php
    sei
    jsr _sound_stop
    jsr zsmkit::zsmkit_clearisr
    stz _sound_ready
    plp
done:
    rts
.endproc
.proc _sound_engine_init
    lda $00
    sta saved_bank
    lda #1
    jsr zsmkit::zsm_init_engine
    jsr zsmkit::zsmkit_setisr
    lda saved_bank
    sta $00
    rts
.endproc
.proc _sound_stop
    ldx #0
    jsr zsmkit::zsm_stop
    ldx #1
    jmp zsmkit::zsm_stop
.endproc
.proc _sound_stop_music
    ldx #0
    jmp zsmkit::zsm_stop
.endproc
.proc _sound_stop_effects
    ldx #1
    jmp zsmkit::zsm_stop
.endproc
.proc _sound_music
    sta music_bank
    lda $00
    sta saved_bank
    lda music_bank
    sta $00
    lda #<$A000
    ldy #>$A000
    ldx #0
    jsr zsmkit::zsm_setmem
    ldx #0
    jsr zsmkit::zsm_play
    lda saved_bank
    sta $00
    rts
.endproc
.proc _sound_sfx
    sta _sound_last_sfx
    stx _sound_last_sfx+1
    ldy _sound_ready
    beq done
    ldy _sound_effects_enabled
    beq done
    clc
    adc #<$A000
    pha
    txa
    adc #>$A000
    tay
    lda $00
    sta saved_bank
    lda #2
    sta $00
    pla
    ldx #1
    jsr zsmkit::zsm_setmem
    ldx #1
    clc
    jsr zsmkit::zsm_setloop
    ldx #1
    jsr zsmkit::zsm_play
    lda saved_bank
    sta $00
done:
    rts
.endproc
