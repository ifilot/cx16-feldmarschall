"""Headless execution of the original 1990 Stratego AI machine instructions.

This is an AI coprocessor, not a replacement strategy or DOS UI emulator.
The host Classic referee supplies deployments and public move/battle events.
Original physical-rank access (including privileged knowledge) is preserved.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
import time

# A normal source checkout uses the isolated dependency install; frozen catalog
# engines have their own sibling unicorn package and need no checkout paths.
try:
    import unicorn
except ImportError:
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'build/msdos1990/deps'))
    import unicorn
from unicorn import Uc, UC_ARCH_X86, UC_MODE_16, UC_HOOK_INTR
from unicorn.x86_const import (UC_X86_REG_AX,UC_X86_REG_BX,UC_X86_REG_CX,UC_X86_REG_DX,
    UC_X86_REG_SI,UC_X86_REG_DI,UC_X86_REG_BP,UC_X86_REG_SP,UC_X86_REG_CS,UC_X86_REG_DS,
    UC_X86_REG_ES,UC_X86_REG_SS,UC_X86_REG_IP,UC_X86_REG_EFLAGS)
from feldmarschall import Position,GLYPHS,LAKES,parse_square,square_name,valid_setup

LOAD=0x1000
DS=LOAD+0x1fe5
OVERLAY=LOAD+0x0d90
RETURN=0x90000
ORIGINAL_RANK=(1,2,3,4,5,6,7,8,9,10,11,0)
FELD_RANK=(11,0,1,2,3,4,5,6,7,8,9,10)
REGISTERS=(UC_X86_REG_AX,UC_X86_REG_BX,UC_X86_REG_CX,UC_X86_REG_DX,UC_X86_REG_SI,
 UC_X86_REG_DI,UC_X86_REG_BP,UC_X86_REG_SP,UC_X86_REG_CS,UC_X86_REG_DS,
 UC_X86_REG_ES,UC_X86_REG_SS,UC_X86_REG_IP,UC_X86_REG_EFLAGS)


def digest(data):return hashlib.sha256(data).hexdigest()

class OriginalCPU:
    """One isolated x86 real-mode address space, persistent between AI calls."""
    def __init__(self,assets,instruction_limit=0,timeout_microseconds=2000000):
        self.assets=Path(assets);self.instruction_limit=instruction_limit
        self.timeout_microseconds=timeout_microseconds
        manifest=json.loads((self.assets/'manifest.json').read_text())
        images={name:(self.assets/name).read_bytes() for name in manifest['images']}
        for name,info in manifest['images'].items():
            if digest(images[name])!=info['sha256']:raise ValueError('Original image hash mismatch: '+name)
        self.manifest=manifest;self.uc=Uc(UC_ARCH_X86,UC_MODE_16);self.uc.mem_map(0,0x110000)
        header=images['mz-header.bin'];image=bytearray(images['resident-image.bin'])
        if header[:2]!=b'MZ':raise ValueError('Expected original MZ header')
        count=struct.unpack_from('<H',header,6)[0];start=struct.unpack_from('<H',header,0x18)[0]
        if start+4*count>len(header):raise ValueError('Truncated original MZ relocations')
        for i in range(count):
            off,seg=struct.unpack_from('<HH',header,start+4*i);at=16*seg+off
            value=struct.unpack_from('<H',image,at)[0];struct.pack_into('<H',image,at,(value+LOAD)&65535)
        self.uc.mem_write(LOAD*16,bytes(image))
        overlay=bytearray(images['ovl5.cod']);rel=images['ovl5.rel']
        for i in range(struct.unpack_from('<H',rel)[0]):
            off,seg=struct.unpack_from('<HH',rel,2+4*i)
            if seg!=0x0d90:raise ValueError('Unsupported overlay relocation')
            value=struct.unpack_from('<H',overlay,off)[0];struct.pack_into('<H',overlay,off,(value+LOAD)&65535)
        self.uc.mem_write(OVERLAY*16,bytes(overlay))
        self.uc.mem_write(RETURN,b'\xf4')
        for register in (UC_X86_REG_DS,UC_X86_REG_ES,UC_X86_REG_SS):self.uc.reg_write(register,DS)
        self.uc.reg_write(UC_X86_REG_EFLAGS,2)
        self.uc.hook_add(UC_HOOK_INTR,self._interrupt)
        self.calls=0;self.elapsed=0.

    def _interrupt(self,uc,number,_):
        raise RuntimeError(f'Unexpected original interrupt {number:02x} at {uc.reg_read(UC_X86_REG_CS):04x}:{uc.reg_read(UC_X86_REG_IP):04x}')

    def read(self,offset,size):return bytes(self.uc.mem_read(DS*16+offset,size))
    def write(self,offset,data):self.uc.mem_write(DS*16+offset,bytes(data))
    def word(self,offset):return struct.unpack('<H',self.read(offset,2))[0]
    def put_word(self,offset,value):self.write(offset,struct.pack('<H',value&65535))

    def call(self,offset,arguments=(),segment=OVERLAY):
        # Near pointers in the original medium model require SS==DS. The
        # disjoint high DGROUP stack leaves original globals and board intact.
        stack=struct.pack('<'+'H'*(2+len(arguments)),0,RETURN//16,*[a&65535 for a in arguments])
        self.write(0xff00,stack);self.uc.reg_write(UC_X86_REG_SP,0xff00)
        self.uc.reg_write(UC_X86_REG_CS,segment);self.uc.reg_write(UC_X86_REG_IP,offset)
        started=time.perf_counter()
        try:self.uc.emu_start(segment*16+offset,RETURN,
                            timeout=self.timeout_microseconds,count=self.instruction_limit)
        except Exception as exc:
            raise RuntimeError(f'Original call {segment:04x}:{offset:04x} failed at {self.uc.reg_read(UC_X86_REG_CS):04x}:{self.uc.reg_read(UC_X86_REG_IP):04x}: {exc}') from exc
        finally:self.calls+=1;self.elapsed+=time.perf_counter()-started
        if self.uc.reg_read(UC_X86_REG_CS)!=RETURN//16 or self.uc.reg_read(UC_X86_REG_IP)!=0:
            raise RuntimeError('Original call did not return within its execution budget')
        return self.uc.reg_read(UC_X86_REG_AX)

    def checkpoint(self):
        return dict(dgroup=self.read(0,65536).hex(),registers=[self.uc.reg_read(r) for r in REGISTERS])

    def restore(self,state):
        self.write(0,bytes.fromhex(state['dgroup']))
        for register,value in zip(REGISTERS,state['registers']):self.uc.reg_write(register,value)

class OriginalAI:
    def __init__(self,assets,side,setups,seed=1,level=3,verify=True):
        if side not in (0,1) or level not in range(1,6) or len(setups)!=2 or not all(valid_setup(s) for s in setups):
            raise ValueError('Classic armies, side 0/1 and DOS difficulty 1..5 required')
        self.side=side;self.level=level;self.cpu=OriginalCPU(assets);self.verify=verify
        self.position=Position()
        for army in (0,1):self.position.place(army,setups[army])
        self.plies=0;self.decisions=0;self.selection_seconds=0.;self.last_move=None
        physical=bytearray(12*12*6)
        for row in range(12):
            for col in range(12):struct.pack_into('<BBHBB',physical,72*row+6*col,0,0,9,0,1)
        for sq in range(100):
            local=self.local(sq);row,col=divmod(local,10);cell=self.position.cells[sq]
            owner=1 if cell and cell[0]==side else 0
            struct.pack_into('<BBHBB',physical,72*(row+1)+6*(col+1),owner,0,ORIGINAL_RANK[cell[1]] if cell else 9,int(sq not in LAKES),0 if cell else 1)
        self.cpu.write(0x3e9c,physical)
        self.cpu.put_word(0x3e90,level)
        # Fixed Classic configuration: Scout move+attack enabled, ordinary
        # combat, original repetition gate. Original knowledge stays enabled.
        self.cpu.write(0x5dec,bytes([0,0,0,0,1,0,1,0,1,0]))
        self.cpu.put_word(0x3544,seed);self.cpu.put_word(0x3546,0)
        self.cpu.call(0x0078) # original initialization entry -> 02FB
        for at in (0x5605,0x5607,0x5609,0x560b,0x5685,0x5687,0x5689,0x568b):self.cpu.put_word(at,-1)
        if verify:self.verify_state()

    def local(self,square):return square if self.side==1 else 99-square
    def global_square(self,square):return self.local(square)

    def choose(self):
        start=time.perf_counter();ok=self.cpu.call(0x13c4,(0x7800,0x7804))
        self.selection_seconds+=time.perf_counter()-start;self.decisions+=1
        if not ok:return None
        fr,fc,tr,tc=(self.cpu.word(at)-1 for at in (0x7800,0x7802,0x7804,0x7806))
        if not all(0<=v<10 for v in (fr,fc,tr,tc)):raise RuntimeError('Original selector returned invalid coordinates')
        move=self.global_square(fr*10+fc),self.global_square(tr*10+tc)
        if move not in self.position.moves(self.side):raise RuntimeError(f'Original selector produced incompatible Classic move: {move}')
        self.last_move=move
        return move

    def observe(self,src,dst,attacker=None,defender=None):
        source=self.position.cells[src];target=self.position.cells[dst]
        if source is None or (src,dst) not in self.position.moves(source[0]):raise ValueError('Illegal public event')
        actual_a=source[1];actual_d=target[1] if target else None
        if attacker is None:
            if target:raise ValueError('Quiet event has an occupied destination')
            self.position.move(src,dst)
        else:
            if target is None or (attacker,defender)!=(actual_a,actual_d):raise ValueError('Battle disclosure differs from original physical board')
            self.position.fight(src,dst,attacker,defender)
        ls,lt=self.local(src),self.local(dst)
        for square in (src,dst):
            row,col=divmod(self.local(square),10);offset=0x3e9c+72*(row+1)+6*(col+1);cell=self.position.cells[square]
            if cell:
                self.cpu.write(offset,bytes([int(cell[0]==self.side)]));self.cpu.put_word(offset+2,ORIGINAL_RANK[cell[1]])
            self.cpu.write(offset+5,bytes([0 if cell else 1]))
        self.cpu.call(0x134b,(ls//10+1,ls%10+1,lt//10+1,lt%10+1,ORIGINAL_RANK[actual_a],ORIGINAL_RANK[actual_d] if actual_d is not None else 9))
        self.plies+=1
        if self.verify:self.verify_state()

    def verify_state(self):
        # Bulk reads keep invariant checking cheap during long tournaments.
        state=self.cpu.read(0x4204,0x1200)
        for square,cell in enumerate(self.position.cells):
            local=self.local(square);pointer=struct.unpack_from('<H',state,0x1062+2*local)[0]
            if bool(pointer)!=bool(cell):raise RuntimeError(f'Original AI occupancy diverged after ply {self.plies} at {square_name(square)}')
            if pointer:
                offset=pointer-0x4204
                row,col,owner,kind=struct.unpack_from('<hhhh',state,offset+3)
                if (row,col,owner)!=(local//10,local%10,int(cell[0]==self.side)):
                    raise RuntimeError(f'Original piece record diverged after ply {self.plies}')
                if cell[0]==self.side and kind!=ORIGINAL_RANK[cell[1]]:raise RuntimeError('Original own-rank state diverged')

    def stats(self):return dict(plies=self.plies,decisions=self.decisions,selection_seconds=self.selection_seconds,cpu_calls=self.cpu.calls,cpu_seconds=self.cpu.elapsed,unicorn_version=unicorn.__version__,level=self.level,information_model='original physical-rank access preserved')


def protocol(assets,level,identity):
    side=0;seed=1;own_setup=None;enemy_setup=None;ai=None
    for line in sys.stdin:
        words=line.split()
        if not words:continue
        command=words[0]
        try:
            if command=='feldmarschall':print(f'id name {identity}\nid author Original 1990 executable / Feldmarschall adapter\nok',flush=True)
            elif command=='isready':print('readyok',flush=True)
            elif command=='seed':seed=int(words[1])
            elif command=='rules':
                if words[1]!='0':raise ValueError('1990 adapter supports Classic only')
            elif command=='new':side=int(words[1]=='blue');own_setup=enemy_setup=None;ai=None
            elif command=='setup':
                if not valid_setup(words[1]):raise ValueError('Invalid own army')
                own_setup=words[1]
            elif command=='opponent-setup':
                if not valid_setup(words[1]):raise ValueError('Invalid original physical opponent army')
                if ai is not None:raise ValueError('Original setup cannot change during a match')
                enemy_setup=words[1]
            elif command=='difficulty':pass # fixed, named DOS level in recipe
            elif command=='go':
                if ai is None:
                    if own_setup is None or enemy_setup is None:raise ValueError('Original DOS engine needs both initial physical armies')
                    setups=[None,None];setups[side]=own_setup;setups[1-side]=enemy_setup
                    ai=OriginalAI(assets,side,setups,seed,level)
                move=ai.choose();print('move '+('none' if move is None else ' '.join(map(square_name,move))),flush=True)
            elif command in ('moved','battle'):
                if ai is None:
                    if own_setup is None or enemy_setup is None:raise ValueError('Missing physical armies')
                    setups=[None,None];setups[side]=own_setup;setups[1-side]=enemy_setup;ai=OriginalAI(assets,side,setups,seed,level)
                src,dst=map(parse_square,words[1:3])
                if command=='moved':ai.observe(src,dst)
                else:ai.observe(src,dst,GLYPHS.index(words[3]),GLYPHS.index(words[4]))
            elif command=='stats':print('stats '+json.dumps(ai.stats() if ai else {}),flush=True)
            elif command=='quit':break
            else:raise ValueError('Unsupported command: '+command)
        except Exception as exc:
            print('error '+str(exc),flush=True)
            # A failed original call must not silently produce a fallback move.
            return 2
    return 0

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets',type=Path,required=True)
    parser.add_argument('--level',type=int,choices=range(1,6),default=3)
    parser.add_argument('--difficulty',choices=('easy','normal','hard'),default='normal')
    parser.add_argument('--identity',default='msdos-1990-unregistered')
    args=parser.parse_args();raise SystemExit(protocol(args.assets,args.level,args.identity))
