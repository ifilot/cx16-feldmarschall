.export _template_prepare, _template_row, _template_export
.import _template_prepare_banked, _template_row_banked, _template_export_banked
.bss
saved_template: .res 1
saved_export: .res 1
.code
.proc _template_prepare
 lda $00
 sta saved_template
 lda #25
 sta $00
 jsr _template_prepare_banked
 lda saved_template
 sta $00
 rts
.endproc
.proc _template_row
 pha
 lda $00
 sta saved_template
 lda #25
 sta $00
 pla
 jsr _template_row_banked
 lda saved_template
 sta $00
 rts
.endproc
.proc _template_export
 pha
 lda $00
 sta saved_export
 lda #24
 sta $00
 pla
 jsr _template_export_banked
 pha
 lda saved_export
 sta $00
 pla
 rts
.endproc
