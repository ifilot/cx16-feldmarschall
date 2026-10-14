"""Stateful Python access to the game's unmodified C rules, for truth or masked views."""
import ctypes
from pathlib import Path

from feldmarschall import ROOT, GLYPHS, UNKNOWN, setup_squares, square_name, parse_square

STATE_SIZE = 157
RESCUED = 51


class VariantPosition:
    def __init__(self, rules=0, library=None):
        self.library = Path(library or ROOT/'build/librules-variant.so')
        self.lib = ctypes.CDLL(str(self.library.resolve()))
        self.board = (ctypes.c_uint8*100).in_dll(self.lib, 'board')
        self.options = ctypes.c_uint8.in_dll(self.lib, 'game_rules')
        for name in ('rules_targets','rules_apply','rules_battle','rules_flag_arrived','rules_can_rescue','rules_rescue','rules_reveal_defender'):
            getattr(self.lib,name).restype = ctypes.c_uint8
        self.lib.board_clear(); self.options.value=rules; self.lib.rules_reset()
        self.cells=bytes(self.board); self.state=self._save(); self.arrival=None

    def _save(self):
        state=(ctypes.c_uint8*STATE_SIZE)(); self.lib.rules_state_save(state)
        return bytes(state)

    def _sync(self):
        self.board[:]=self.cells
        self.lib.rules_state_load((ctypes.c_uint8*STATE_SIZE).from_buffer_copy(self.state))

    def _take(self): self.cells=bytes(self.board); self.state=self._save()

    @property
    def rules(self): return self.state[0]

    def place(self, army, glyphs, known=True):
        cells=bytearray(self.cells)
        for sq,glyph in zip(setup_squares(army),glyphs):
            cells[sq]=(GLYPHS.index(glyph) if known else UNKNOWN)|(16 if army else 0)
        self.cells=bytes(cells)

    def moves(self, army):
        self._sync(); found=[]; targets=(ctypes.c_uint8*20)()
        for sq,cell in enumerate(self.cells):
            if cell<254 and bool(cell&16)==bool(army):
                n=self.lib.rules_targets(sq,targets)
                found.extend((sq,int(targets[i])) for i in range(n))
        return found

    def outcome(self, attacker, defender):
        self._sync(); return int(self.lib.rules_battle(attacker,defender))

    def apply(self, src, dst):
        self._sync(); a,d=self.cells[src],self.cells[dst]
        outcome=int(self.lib.rules_apply(src,dst)); self._take()
        self.arrival=dst if outcome in (0,3) else None
        squares=f'{square_name(src)} {square_name(dst)}'
        if outcome==3: event='moved '+squares
        else:
            visible=bool(d&32) or bool(self.lib.rules_reveal_defender(a&15))
            event=f"combat {squares} {GLYPHS[a&15]} {GLYPHS[d&15] if visible else '?'} {'ADX'[outcome]}"
        winner = None
        if d<254 and d&15==11: winner='flag'
        elif self.lib.rules_flag_arrived(dst): winner='flag arrival'
        return event,winner

    def auto_rescue(self, trigger):
        if trigger!=self.arrival:return None
        self._sync()
        if not self.lib.rules_can_rescue(trigger): return None
        army=bool(self.cells[trigger]&16)
        lost=(ctypes.c_uint8*24).in_dll(self.lib,'rules_lost')
        rank=next(r for r in range(10) if lost[int(army)*12+r])
        destinations=range(39,-1,-1) if army else range(60,100)
        dst=next(sq for sq in destinations if self.cells[sq]==255)
        assert self.lib.rules_rescue(trigger,rank,dst)
        self._take(); return trigger,dst,rank,bool(self.cells[dst]&32)

    def view(self, army):
        cells=bytes((cell&240)|12 if cell<254 and bool(cell&16)!=bool(army) and not cell&32 else cell for cell in self.cells)
        own_lost=self.state[1+12*army:1+12*(army+1)]
        enemy_known=self.state[25+12*(1-army):25+12*(2-army)]
        shuttle=bytearray(self.state[-6:])
        for a in (0,1):
            if not shuttle[4+a]: shuttle[a]=shuttle[2+a]=255
        return f'{army} {cells.hex()} {enemy_known.hex()} {own_lost.hex()} {self.state[49:51].hex()} {shuttle.hex()}'

    def observe(self, event):
        words=event.split(); command=words[0]
        src,dst=map(parse_square,words[1:3]); self._sync()
        state=bytearray(self.state); cells=bytearray(self.cells)
        if command=='reinforce':
            rank=GLYPHS.index(words[3]) if words[3]!='?' else 12
            visible=int(words[4]); army=int(bool(cells[src]&16))
            cells[dst]=rank|(16 if army else 0)|(32 if visible else 0)
            if rank<12:
                for offset in ([1] + ([25] if visible else [])):
                    index=offset+army*12+rank
                    if state[index]: state[index]-=1
            state[49+army]+=1;state[RESCUED+src]=1;state[RESCUED+dst]=0
        else:
            self.lib.rules_record(src,dst); state=bytearray(self._save())
            a,d=cells[src],cells[dst]
            if command=='moved':
                if abs(src//10-dst//10)+abs(src%10-dst%10)>1: a=(a&240)|8|32
                result=3
            elif command=='combat':
                a=(a&240)|GLYPHS.index(words[3])|32
                if words[4]!='?': d=(d&240)|GLYPHS.index(words[4])|32
                result='ADX'.index(words[5])
                for cell,fallen in ((a,result!=0),(d,result!=1)):
                    rank=cell&15
                    if fallen and rank<12:
                        army=int(bool(cell&16));state[1+12*army+rank]+=1
                        if cell&32:state[25+12*army+rank]+=1
            else: raise ValueError(command)
            if result in (0,3): cells[dst]=a|64;state[RESCUED+dst]=state[RESCUED+src]
            elif result==2: cells[dst]=255;state[RESCUED+dst]=0
            else: cells[dst]=d
            cells[src]=255;state[RESCUED+src]=0
        self.cells=bytes(cells);self.state=bytes(state)
