"""Compare both sides of a learned history split inside the actual banked scorer."""
import argparse
import json
from pathlib import Path
import re
import shutil
import tempfile

from feldmarschall import ROOT, COUNTS, LAKES, GLYPHS, Engine, square_name, Position
from test_colors import start, choose


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime',type=Path,default=ROOT/'build/ai-student-x16')
    args=parser.parse_args();runtime=args.runtime
    mapping=(runtime/'FELDMARS.map').read_text();symbols=(runtime/'FELDMARS.sym').read_text()
    symbol=lambda name:int(re.search(r'al ([0-9A-F]+) \._'+name+r'\b',symbols).group(1),16)
    base=int(re.search(r'^MISSIONBSS\s+([0-9A-F]+)',mapping,re.M).group(1),16)
    base+=int(re.search(r'ai_memory\.o:\n\s+MISSIONBSS\s+Offs=([0-9A-F]+)',mapping).group(1),16)
    lost=COUNTS[:];lost[8]-=1;lost[11]-=1
    cells=[255]*100
    for sq in LAKES:cells[sq]=254
    for sq,cell in {60:4,99:11,7:8|16|32,9:12|16}.items():cells[sq]=cell
    histories=[]
    for cold in (True,False):
        native=Engine(str(ROOT/'build/feldmarschall-engine-student-features'))
        native.send('new red');native.send('setup '+''.join(g*n for g,n in zip(GLYPHS,COUNTS)))
        native.ask(f'features 0 {bytes(lost).hex()} {bytes(cells).hex()} 1','features_done')
        moves=[50,40,30,20,10,11,12,13,14,15,16,17]
        enemy=[8,18,19,29,28,18,19,29,28,18,8,7]
        truth=Position();truth.cells[60]=[0,4,False,False];truth.cells[99]=[0,11,False,False]
        truth.cells[7]=[1,8,False,True];truth.cells[9]=[1,11,False,False]
        src,other=60,7
        for to,next_enemy in zip(moves,enemy):
            assert (src,to) in truth.moves(0);truth.move(src,to)
            native.send(f'moved {square_name(src)} {square_name(to)}');src=to
            assert (other,next_enemy) in truth.moves(1);truth.move(other,next_enemy)
            native.send(f'moved {square_name(other)} {square_name(next_enemy)}');other=next_enemy
        final=[255]*100
        for sq in LAKES:final[sq]=254
        for sq,cell in {17:4|64,99:11,7:8|16|32|64,9:12|16}.items():final[sq]=cell
        if cold:native.ask(f'features 0 {bytes(lost).hex()} {bytes(final).hex()} 1','features_done')
        expected=int(native.ask('student '+square_name(17)+' '+square_name(7),'learned'))
        identities=[255]*100;records=[]
        for sq in (7,9,17,99):
            history=list(map(int,native.ask('memory '+square_name(sq),'history').split()))
            identities[sq]=history[1];records.append((history[1],history))
        state=bytearray(941);state[:100]=bytes(identities);state[100]=max(index for index,_ in records)+1
        for index,history in records:
            offset=101+index*10;state[offset:offset+8]=bytes(history[2:10]);state[offset+8:offset+10]=history[10].to_bytes(2,'little')
        with tempfile.TemporaryDirectory(prefix='feldmarschall-student-history-') as tmp:
            for path in runtime.iterdir():
                if path.is_file():shutil.copy2(path,Path(tmp)/path.name)
            session=start(Path(tmp))
            try:
                session.emu.write_memory(symbol('ai_difficulty'),bytes([1]))
                gateway=symbol('ai_move');entry=symbol('ai_student_score')
                session.emu.request('breakpoint',address=gateway);choose(session,'6')
                assert session.emu.request('status')['pc']==gateway
                stack=int.from_bytes(session.emu.read_memory(0x22,2),'little')
                lost_ptr=int.from_bytes(session.emu.read_memory(stack+2,2),'little')
                session.emu.write_memory(lost_ptr,bytes(lost));session.emu.write_memory(symbol('board'),bytes(final))
                session.emu.write_memory(stack+4,bytes([0]))
                session.emu.write_memory(base-0xa000,state,space='banked_ram',bank=24)
                session.emu.request('breakpoint',action='remove',address=gateway)
                session.emu.request('breakpoint',address=entry,bank=24)
                assert session.emu.advance(600)['reason']=='breakpoint'
                before=session.emu.request('status')
                stack=int.from_bytes(session.emu.read_memory(0x22,2),'little')
                assert session.emu.read_memory(stack,1)[0]==17 and before['a']==7
                hardware=0x100|((before['sp']+1)&255)
                return_pc=int.from_bytes(session.emu.read_memory(hardware,2),'little')+1
                session.emu.request('breakpoint',action='remove',address=entry,bank=24)
                session.emu.request('breakpoint',address=return_pc,bank=24)
                assert session.emu.advance(2)['reason']=='breakpoint'
                result=session.emu.request('status');got=result['a']|result['x']<<8
                if got>=32768:got-=65536
                assert got==expected,(cold,got,expected)
                histories.append({'cold':cold,'prior_actor_moves':0 if cold else 12,'native':expected,'x16':got})
            finally:session.emu.close();native.close()
    assert histories[0]['native']!=histories[1]['native']
    (runtime/'history-sensitive-inference.json').write_text(json.dumps(histories,indent=2)+'\n')
    print('Banked learned split: cold and 12-move public histories match native predictions',histories)


if __name__=='__main__':main()
