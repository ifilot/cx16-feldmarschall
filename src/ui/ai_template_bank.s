; Opt-in template inference has separate save bytes from AI/mission gateways.
.ifdef AI_TEMPLATE_PRIOR_Q24
.export _ai_template_build, _ai_template_copy, _ai_template_export, _ai_template_forget
.export _ai_template_start
.import _ai_memory_sync
.import _ai_template_build_banked, _ai_template_copy_banked
.import _ai_template_export_banked, _ai_template_forget_banked
.bss
saved_inference: .res 1
saved_history: .res 1
.code
.proc _ai_template_build
 lda $00
 sta saved_inference
 lda #25
 sta $00
 jsr _ai_template_build_banked
 pha
 lda saved_inference
 sta $00
 pla
 rts
.endproc
.proc _ai_template_copy
 pha
 lda $00
 sta saved_inference
 lda #25
 sta $00
 pla
 jsr _ai_template_copy_banked
 lda saved_inference
 sta $00
 rts
.endproc
.proc _ai_template_export
 pha
 lda $00
 sta saved_history
 lda #24
 sta $00
 pla
 jsr _ai_template_export_banked
 pha
 lda saved_history
 sta $00
 pla
 rts
.endproc
.proc _ai_template_forget
 lda $00
 sta saved_history
 lda #24
 sta $00
 jsr _ai_template_forget_banked
 lda saved_history
 sta $00
 rts
.endproc
.proc _ai_template_start
 lda $00
 sta saved_history
 lda #24
 sta $00
 jsr _ai_memory_sync
 lda saved_history
 sta $00
 rts
.endproc
.endif
