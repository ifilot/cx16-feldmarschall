"""Match real student decisions, random state and accumulated histories in both armies."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile

from feldmarschall import ROOT, Engine, GLYPHS, parse_square, setup_squares, square_name
from test_colors import start, choose


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime',type=Path,default=ROOT/'build/ai-student-x16')
    parser.add_argument('--turns',type=int,default=80)
    args=parser.parse_args();runtime=args.runtime
    symbols=(runtime/'FELDMARS.sym').read_text()
    symbol=lambda name:int(re.search(r'al ([0-9A-F]+) \._'+name+r'\b',symbols).group(1),16)
    mapping=(runtime/'FELDMARS.map').read_text()
    data_base=int(re.search(r'^DATA\s+([0-9A-F]+)',mapping,re.M).group(1),16)
    rng_offset=int(re.search(r'random\.o:\n\s+CODE[^\n]*\n\s+DATA\s+Offs=([0-9A-F]+)',mapping).group(1),16)
    gateway,observe,mask=symbol('ai_move'),symbol('ai_memory_observe'),symbol('ai_mask')
    engines=[];records=[]
    with tempfile.TemporaryDirectory(prefix='feldmarschall-student-') as tmp:
        for path in runtime.iterdir():
            if path.is_file():shutil.copy2(path,Path(tmp)/path.name)
        session=start(Path(tmp))
        try:
            session.emu.write_memory(symbol('ai_difficulty'),bytes([1]))
            session.emu.request('breakpoint',address=mask)
            choose(session,'6')
            assert session.emu.request('status')['pc']==mask
            truth=bytes(session.emu.read_memory(symbol('board'),100))
            for army in (0,1):
                engine=Engine(str(ROOT/'build/feldmarschall-engine-student')+' --difficulty normal')
                engine.send('new '+('red','blue')[army])
                engine.send('setup '+''.join(GLYPHS[truth[sq]&15] for sq in setup_squares(army)))
                engines.append(engine)
            session.emu.request('breakpoint',action='remove',address=mask)
            session.emu.request('breakpoint',address=gateway)
            assert session.emu.advance(2)['reason']=='breakpoint'
            for turn in range(args.turns):
                before=session.emu.request('status');assert before['pc']==gateway
                stack=int.from_bytes(session.emu.read_memory(0x22,2),'little')
                arguments=bytes(session.emu.read_memory(stack,5))
                from_ptr=int.from_bytes(arguments[:2],'little')
                to_ptr=before['a']|before['x']<<8
                army=bool(arguments[4]);seed=int.from_bytes(session.emu.read_memory(data_base+rng_offset,2),'little')
                engines[army].send('seed '+str(seed))
                expected=tuple(map(parse_square,engines[army].ask('go','move').split()))
                history=list(map(int,engines[army].ask('memory '+square_name(expected[0]),'history').split()))
                session.emu.request('breakpoint',action='remove',address=gateway)
                session.emu.request('breakpoint',address=gateway+6)
                assert session.emu.advance(600)['reason']=='breakpoint'
                got=(session.emu.read_memory(from_ptr,1)[0],session.emu.read_memory(to_ptr,1)[0])
                assert got==expected,(turn,army,got,expected)
                assert session.emu.request('status')['ram_bank']==23
                session.emu.request('breakpoint',action='remove',address=gateway+6)
                session.emu.request('breakpoint',address=observe)
                assert session.emu.advance(600)['reason']=='breakpoint'
                state=session.emu.request('status');assert state['ram_bank']==22
                stack=int.from_bytes(session.emu.read_memory(0x22,2),'little')
                to,src=session.emu.read_memory(stack,2);outcome=state['a']
                assert (src,to)==got
                cells=bytes(session.emu.read_memory(symbol('board'),100))
                notification=f'moved {square_name(src)} {square_name(to)}' if outcome==3 else (
                    f'battle {square_name(src)} {square_name(to)} {GLYPHS[cells[src]&15]} {GLYPHS[cells[to]&15]}')
                for engine in engines:engine.send(notification)
                records.append({'turn':turn,'army':int(army),'seed':seed,'move':got,
                                'actor_prior_observed_moves':history[5],'notification':notification})
                session.emu.request('breakpoint',action='remove',address=observe)
                if outcome!=3 and cells[to]&15==11:break
                if turn+1<args.turns:
                    session.emu.request('breakpoint',address=gateway)
                    result=session.emu.advance(600)
                    if result['reason']!='breakpoint':break # a legal no-moves ending
                if (turn+1)%20==0:print(f'{turn+1} real banked student turns matched',flush=True)
        finally:
            for engine in engines:engine.close()
            session.emu.close()
    assert len(records)>=20
    report={'turns':records,'mismatches':0,'max_actor_prior_observed_moves':max(r['actor_prior_observed_moves'] for r in records),
            'native_sha256':hashlib.sha256((ROOT/'build/feldmarschall-engine-student').read_bytes()).hexdigest(),
            'runtime_provenance':json.loads((runtime/'provenance.json').read_text())}
    (runtime/'banked-student-decisions.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f'{len(records)} real banked student turns match both native armies; history and per-turn RNG preserved')


if __name__=='__main__':main()
