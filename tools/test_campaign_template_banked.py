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
    parser.add_argument('--engine',type=Path,default=ROOT/'build/feldmarschall-engine-student')
    parser.add_argument('--template-layout',type=int,default=-1)
    parser.add_argument('--label',default='audio-default')
    parser.add_argument('--check-rng-output',action='store_true',help='Requires a private fixture-rng diagnostic observer; policy code stays unchanged.')
    args=parser.parse_args();runtime=args.runtime
    assert not (runtime/(args.label+'.json')).exists()
    # Fail before running the emulator if the source/build binding is missing.
    runtime_provenance=json.loads((runtime/'provenance.json').read_text())
    symbols=(runtime/'FELDMARS.sym').read_text()
    symbol=lambda name:int(re.search(r'al ([0-9A-F]+) \._'+name+r'\b',symbols).group(1),16)
    mapping=(runtime/'FELDMARS.map').read_text()
    data_base=int(re.search(r'^DATA\s+([0-9A-F]+)',mapping,re.M).group(1),16)
    rng_offset=int(re.search(r'random\.o:\n\s+CODE[^\n]*\n\s+DATA\s+Offs=([0-9A-F]+)',mapping).group(1),16)
    gateway,observe,mask=symbol('ai_move'),symbol('ai_memory_observe'),symbol('ai_mask')
    import zipfile
    with zipfile.ZipFile(ROOT/'docs/ai-honest-campaign-2026-10-15/research/template-target-prototype-v1/relocated-link-evidence.zip') as z:
        layout=z.read('core/ai_template.s').decode().split('.segment\t"BELIEFBSS"',1)[1].split('.segment\t"CODE"',1)[0]
    offsets={};offset=0
    for name,length in re.findall(r'_(\w+):\s+\.res\s+(\d+),',layout):
        offsets[name]=offset;offset+=int(length)
    belief_base=int(re.search(r'^BELIEFBSS\s+([0-9A-F]+)',mapping,re.M)[1],16)-0xa000
    engines=[];records=[];debug=[]
    with tempfile.TemporaryDirectory(prefix='feldmarschall-student-') as tmp:
        for path in runtime.iterdir():
            if path.is_file():shutil.copy2(path,Path(tmp)/path.name)
        session=start(Path(tmp))
        try:
            session.emu.write_memory(symbol('ai_difficulty'),bytes([1]))
            if args.template_layout>=0:
                from campaign_template_beliefs import TEMPLATES
                initial=symbol('ai_template_start')
                session.emu.request('breakpoint',address=initial)
                choose(session,'6')
                at_start=session.emu.request('status');assert at_start['pc']==initial and at_start['ram_bank']==22
                cells=bytearray(session.emu.read_memory(symbol('board'),100))
                for side in (0,1):
                    for square,glyph in zip(setup_squares(side),TEMPLATES[(args.template_layout+side)%8]):cells[square]=side*16+GLYPHS.index(glyph)
                session.emu.write_memory(symbol('board'),cells)
                hw=0x100|((at_start['sp']+1)&255)
                initial_return=int.from_bytes(session.emu.read_memory(hw,2),'little')+1
                session.emu.request('breakpoint',action='remove',address=initial)
                session.emu.request('breakpoint',address=symbol('ai_memory_sync'),bank=24)
                assert session.emu.advance(2)['reason']=='breakpoint'
                assert session.emu.request('status')['ram_bank']==24
                session.emu.request('breakpoint',action='remove',address=symbol('ai_memory_sync'),bank=24)
                session.emu.request('breakpoint',address=initial_return,bank=22)
                assert session.emu.advance(2)['reason']=='breakpoint'
                assert session.emu.request('status')['ram_bank']==22
                session.emu.request('breakpoint',action='remove',address=initial_return,bank=22)
                session.emu.request('breakpoint',address=mask)
                assert session.emu.advance(600)['reason']=='breakpoint'
            else:
                session.emu.request('breakpoint',address=mask)
                choose(session,'6')
            assert session.emu.request('status')['pc']==mask
            truth=bytes(session.emu.read_memory(symbol('board'),100))
            for army in (0,1):
                engine=Engine(str(args.engine.resolve())+' --difficulty normal')
                engine.send('new '+('red','blue')[army])
                engine.send('setup '+''.join(GLYPHS[truth[sq]&15] for sq in setup_squares(army)))
                engines.append(engine)
            session.emu.request('breakpoint',action='remove',address=mask)
            session.emu.request('breakpoint',address=gateway)
            assert session.emu.advance(2)['reason']=='breakpoint'
            for turn in range(args.turns):
                before=session.emu.request('status');assert before['pc']==gateway
                stack=int.from_bytes(session.emu.read_memory(0x22,2),'little')
                assert 0x9b00+32 < stack < 0x9f00, 'software stack stays inside its reserved 1 KB'
                canary=bytes([0xa5])*(stack-0x9b00)
                session.emu.write_memory(0x9b00,canary)
                arguments=bytes(session.emu.read_memory(stack,5))
                from_ptr=int.from_bytes(arguments[:2],'little')
                to_ptr=before['a']|before['x']<<8
                army=bool(arguments[4]);seed=int.from_bytes(session.emu.read_memory(data_base+rng_offset,2),'little')
                engines[army].send('seed '+str(seed))
                expected=tuple(map(parse_square,engines[army].ask('go','move').split()))
                history=list(map(int,engines[army].ask('memory '+square_name(expected[0]),'history').split()))
                audio_before={name:session.emu.read_memory(symbol(name),1)[0] for name in ('sound_ready','sound_music_enabled','sound_music_bank')}
                psg_before=session.emu.read_memory(0x1f9c0,64,space='vram').hex()
                assert audio_before['sound_ready']==audio_before['sound_music_enabled']==1
                session.emu.request('breakpoint',action='remove',address=gateway)
                export=symbol('ai_template_export_banked')
                session.emu.request('breakpoint',address=export,bank=24)
                assert session.emu.advance(600)['reason']=='breakpoint'
                assert session.emu.request('status')['ram_bank']==24
                session.emu.request('breakpoint',action='remove',address=export,bank=24)
                prepare=symbol('ai_template_build')
                session.emu.request('breakpoint',address=prepare)
                assert session.emu.advance(600)['reason']=='breakpoint'
                preparing=session.emu.request('status');assert preparing['ram_bank']==23
                hw=0x100|((preparing['sp']+1)&255)
                return_pc=int.from_bytes(session.emu.read_memory(hw,2),'little')+1
                session.emu.request('breakpoint',action='remove',address=prepare)
                if turn==0:
                    entry=symbol('ai_template_build_banked')
                    session.emu.request('breakpoint',address=entry,bank=25)
                    assert session.emu.advance(600)['reason']=='breakpoint'
                    assert session.emu.request('status')['ram_bank']==25
                    session.emu.request('breakpoint',action='remove',address=entry,bank=25)
                    helper=int(re.search(r'al ([0-9A-F]+) \.toslcmp\b',symbols)[1],16)
                    session.emu.request('breakpoint',address=helper,bank=25)
                    assert session.emu.advance(600)['reason']=='breakpoint'
                    assert session.emu.request('status')['ram_bank']==25
                    session.emu.request('breakpoint',action='remove',address=helper,bank=25)
                session.emu.request('breakpoint',address=return_pc)
                assert session.emu.advance(600)['reason']=='breakpoint'
                prepared=session.emu.request('status');assert prepared['ram_bank']==23
                session.emu.request('breakpoint',action='remove',address=return_pc)
                session.emu.request('breakpoint',address=gateway+6)
                assert session.emu.advance(600)['reason']=='breakpoint'
                after=session.emu.request('status')
                got=(session.emu.read_memory(from_ptr,1)[0],session.emu.read_memory(to_ptr,1)[0])
                if args.check_rng_output:
                    native_rng=int(engines[army].ask('fixture-rng','rng'))
                    target_rng=int.from_bytes(session.emu.read_memory(data_base+rng_offset,2),'little')
                    assert target_rng==native_rng,(turn,target_rng,native_rng)
                prior=list(map(int,engines[army].ask('template-prior','prior').split()))
                def private(name,size):return session.emu.read_memory(belief_base+offsets[name],size,space='banked_ram',bank=25)
                flag=private('flag_q',80);bomb=private('bomb_q',80)
                flags=[int.from_bytes(flag[i:i+2],'little') for i in range(0,80,2)]
                bombs=[int.from_bytes(bomb[i:i+2],'little') for i in range(0,80,2)]
                cache=private('cache',960)
                cache_values=[int.from_bytes(cache[i:i+2],'little',signed=True) for i in range(0,960,2)]
                debug.append(dict(ai_cycles=after['cycles']-before['cycles'],prepare_cycles=prepared['cycles']-preparing['cycles'],audio=audio_before,psg_before=psg_before,psg_after=session.emu.read_memory(0x1f9c0,64,space='vram').hex(),cache_differences=[(i,cache_values[i],prior[84+i]) for i in range(480) if cache_values[i]!=prior[84+i]],turn=turn,army=int(army),target_move=got,native_move=expected,native_prior=prior,
                    target_status=session.emu.read_memory(symbol('ai_template_status'),1)[0],
                    target_valid=session.emu.read_memory(symbol('ai_template_valid'),1)[0],
                    target_evidence=int.from_bytes(private('evidence',4),'little'),target_mask=private('allowed',1)[0],
                    target_flags=flags,target_bombs=bombs,
                    target_history=private('history',80).hex(),
                    q12_differences=[i for i in range(40) if (flags[i],bombs[i])!=tuple(prior[4+2*i:6+2*i])]))
                (runtime/(args.label+'.json')).write_text(json.dumps(debug,indent=2)+'\n')
                assert got==expected,(turn,army,got,expected)
                assert after['ram_bank']==23
                used=bytes(session.emu.read_memory(0x9b00,len(canary)))
                untouched=next((i for i,v in enumerate(used) if v!=0xa5),len(used))
                assert untouched>=32, 'AI leaves a stack guard intact'
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
                                'frames':after['frames']-before['frames'],
                                'stack_canary_untouched_bytes':untouched,
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
    assert any(bytes.fromhex(r['psg_after'])[v*4+2]&63 for r in debug for v in range(16))
    assert any(r['psg_before']!=r['psg_after'] for r in debug)
    assert all(not r['cache_differences'] and not r['q12_differences'] for r in debug)
    (runtime/(args.label+'-summary.json')).write_text(json.dumps(dict(rng_output_compared=args.check_rng_output,template_layout=args.template_layout,history_start_banks=[22,24,22] if args.template_layout>=0 else None,per_turn_history_export_bank24=True,turns=len(debug),max_ai_cycles=max(r['ai_cycles'] for r in debug),max_prepare_cycles=max(r['prepare_cycles'] for r in debug),audio_active=True,relocated_runtime_executed_in_bank25=True,all_native_q12_cache_moves_identical=True,minimum_stack_canary_untouched_bytes=min(r['stack_canary_untouched_bytes'] for r in records)),indent=2)+'\n')
    report={'turns':records,'mismatches':0,'max_actor_prior_observed_moves':max(r['actor_prior_observed_moves'] for r in records),
            'max_frames':max(r['frames'] for r in records),
            'minimum_stack_canary_untouched_bytes':min(r['stack_canary_untouched_bytes'] for r in records),
            'native_sha256':hashlib.sha256(args.engine.read_bytes()).hexdigest(),
            'runtime_provenance':runtime_provenance}
    (runtime/'banked-student-decisions.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f'{len(records)} real banked student turns match both native armies; history and per-turn RNG preserved')


if __name__=='__main__':main()
