#include <stdint.h>
/* Lifecycle-disjoint public history packet and one attacker gain row. */
union transfer {uint8_t history[80];int16_t row[100];};
union transfer template_transfer;
uint8_t template_owner,template_valid;
extern uint8_t __fastcall__ template_export(uint8_t owner);
extern void template_prepare(void);
extern void __fastcall__ template_row(uint8_t rank);
void __fastcall__ template_prepare_main(uint8_t owner) {
 template_owner=owner; template_valid=template_export(owner);
 if(template_valid) template_prepare();
}
void __fastcall__ template_row_main(uint8_t rank) {
 if(template_valid) template_row(rank);
}
