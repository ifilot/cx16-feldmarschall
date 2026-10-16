"""Single-swap retained Flag guard: real native setup and response fixtures."""
import ctypes
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import tempfile
import unittest

from ai_registry import ROOT,get_policy
from feldmarschall import COUNTS,Engine,GLYPHS,LAKES,Position,battle,setup_squares,valid_setup
from tournament_store import mirror_setup
from research_deployment_double_shell import geometry

OUT=ROOT/'docs/ai-honest-campaign-2026-10-16/research/inner-guard'
SOURCE=ROOT/'tools/new_campaign_inner_guard_deploy.c'


def layouts():
    arrays=re.findall(r'\{([\d,]+)\}',(ROOT/'src/core/ai_deploy.c').read_text())
    base=''.join(GLYPHS[int(n)] for n in next(a for a in arrays if len(a.split(','))==40).split(','))
    candidate=list(base);candidate[21],candidate[34]=candidate[34],candidate[21]
    return base,''.join(candidate)


class InnerGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='inner-guard-');cls.folder=Path(cls.temp.name)
        cls.base,cls.candidate=layouts();cls.records=[];cls.programs={}
        spec=get_policy('student-fortress-template-flag-bomb-v1-normal')
        engine=(ROOT/'src/native/engine.c').read_text()
        anchor='        } else if(!strcmp(command, "seed")) {'
        assert engine.count(anchor)==1
        engine=engine.replace(anchor,'        } else if(!strcmp(command,"fixture-rng")) { printf("rng %u\\n",random_current());fflush(stdout);\n'+anchor)
        (cls.folder/'engine.c').write_text(engine)
        for mode in ('control','default-off','candidate'):
            files=[str(cls.folder/'engine.c') if f=='src/native/engine.c' else
                   str(SOURCE) if f=='src/core/ai_deploy.c' and mode!='control' else f for f in spec['sources']]
            defines=spec['defines']+(['AI_FORTRESS_INNER_GUARD'] if mode=='candidate' else [])
            command=['gcc','-O2','-std=c99','-Wno-unknown-pragmas','-Isrc/core']+['-D'+x for x in defines]+files+['-o',str(cls.folder/mode)]
            subprocess.run(command,cwd=ROOT,check=True,capture_output=True)
            cls.programs[mode]=cls.folder/mode

    @classmethod
    def tearDownClass(cls):
        OUT.mkdir(parents=True,exist_ok=True)
        doc=dict(scope='Own deployment and controlled native public defense fixtures; no tournament or playing-strength result',
            sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in (SOURCE,Path(__file__),ROOT/'src/core/ai_deploy.c')},
            layouts={name:dict(setup=setup,geometry=geometry(setup)) for name,setup in [('Fortress',cls.base),('InnerGuard',cls.candidate)]},
            native_responses=cls.records,
            limitation='Both layouts retain the preexisting isolated mobile at origin38. Geometry counts permanent Bomb/Flag blockers and assumes mobile teammates can vacate. Controlled response states are synthetic inventory-consistent public components, not proven reachable full histories or fresh initial-formation breaches. Right breach clears own origin32, assuming that Miner left earlier, so it does not simultaneously occupy the invader approach square.')
        (OUT/'component.json').write_text(json.dumps(doc,indent=2)+'\n');cls.temp.cleanup()

    def test_single_swap_inventory_and_unchanged_structure(self):
        a,b=self.base,self.candidate
        self.assertTrue(valid_setup(b));self.assertEqual(sorted(a),sorted(b))
        self.assertEqual([i for i in range(40) if a[i]!=b[i]],[21,34])
        for glyph in 'BFS':self.assertEqual([i for i,v in enumerate(a) if v==glyph],[i for i,v in enumerate(b) if v==glyph])
        self.assertEqual(a[:20],b[:20]);self.assertEqual(geometry(a),geometry(b))
        self.assertEqual(geometry(b)['mobile_pieces_with_permanent_front_access'],32)
        self.assertEqual(geometry(b)['trapped_mobile_squares'],[38])

    def test_guard_geometry_and_combat_both_gates_both_colors(self):
        for army in (0,1):
            for mirrored in (False,True):
                layout=mirror_setup(self.candidate) if mirrored else self.candidate
                transform=lambda i:i//10*10+9-i%10 if mirrored else i
                squares=setup_squares(army);guard=squares[transform(21)]
                for origin in (20,31):
                    target=squares[transform(origin)]
                    self.assertEqual(abs(guard//10-target//10)+abs(guard%10-target%10),1)
                    self.assertEqual(battle(GLYPHS.index(layout[transform(21)]),7),'attacker')
            self.assertEqual(battle(GLYPHS.index(self.base[21]),7),'both')
        self.assertEqual(self.base[10],'6') # Existing Lieutenant already covers left gate20.

    def setup(self,bot,army,seed,level='normal'):
        for cmd in ['new '+('red','blue')[army],'rules 0','difficulty '+level,'seed '+str(seed)]:bot.send(cmd)
        return bot.ask('setup','setup')

    def test_native_setup_rng_rotation_and_default_off(self):
        bots={name:Engine(shlex.quote(str(path))) for name,path in self.programs.items()}
        try:
            for army in (0,1):
                for level in ('easy','normal','hard'):
                    for seed in (1,2,17,791,9123,65535):
                        setups={name:self.setup(bot,army,seed,level) for name,bot in bots.items()}
                        self.assertEqual(setups['control'],setups['default-off'])
                        if level=='normal':self.assertEqual(setups['candidate'],self.candidate)
                        else:self.assertEqual(setups['candidate'],setups['control'])
                        self.assertEqual(len({bot.ask('fixture-rng','rng') for bot in bots.values()}),1)
                        for bot in bots.values():bot.send('setup '+self.base)
                        self.assertEqual(len({bot.ask('go','move') for bot in bots.values()}),1)
        finally:
            for bot in bots.values():bot.close()

    def test_native_formation_defense_components_both_gates_both_colors(self):
        for army,reflected in ((a,m) for a in (0,1) for m in (False,True)):
            enemy=1-army
            reflect=lambda sq:sq//10*10+9-sq%10 if reflected else sq
            own=list(map(reflect,setup_squares(army)));far=list(map(reflect,setup_squares(enemy)))
            for breach in (20,31):
                for mode,layout in [('control',self.base),('candidate',self.candidate)]:
                    cells=[254 if s in LAKES else 255 for s in range(100)]
                    for index,glyph in enumerate(layout):cells[own[index]]=army*16+GLYPHS.index(glyph)
                    cells[own[breach]]=enemy*16+7+32+64
                    if breach==31:cells[own[32]]=255 # This Miner must have left before the breach.
                    cells[far[30]]=enemy*16+12
                    for index in (20,31):cells[far[index]]=enemy*16+10+32
                    lost=COUNTS[:];lost[7]-=1;lost[10]-=2;lost[11]-=1
                    bot=Engine(shlex.quote(str(self.programs[mode])))
                    try:
                        bot.send('difficulty normal')
                        reply=bot.ask('think %d 3137 %s %s'%(army,bytes(lost).hex(),bytes(cells).hex()),'best')
                        source,target=map(int,reply.split());self.assertEqual(target,own[breach])
                        rank=cells[source]&15;outcome=battle(rank,7)
                        self.assertEqual(outcome,'attacker' if mode=='candidate' or breach==20 else 'both')
                        if mode=='candidate' and breach==31:self.assertEqual(source,own[21])
                        self.records.append(dict(army=army,breach_origin=breach,mode=mode,selected=[source,target],
                            own_rank=rank,public_enemy_rank=7,outcome=outcome,guard_survives=outcome=='attacker',
                            cleared_own_mobile_origins=[32] if breach==31 else [],horizontal_reflection=reflected,
                            synthetic_component_not_history=True))
                    finally:bot.close()

    def test_macro_requires_fortress_and_separate_idea(self):
        for flags,message in [(['AI_FORTRESS_INNER_GUARD'],'requires AI_DEPLOY_FORTRESS_ONLY'),
            (['AI_FORTRESS_INNER_GUARD','AI_DEPLOY_FORTRESS_ONLY','AI_DEPLOY_DOUBLE_SHELL'],'separate single-swap')]:
            result=subprocess.run(['gcc','-E','-Isrc/core']+['-D'+f for f in flags]+[str(SOURCE)],cwd=ROOT,capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0);self.assertIn(message,result.stderr)

    def test_native_setup_independent_of_enemy_board(self):
        stub=self.folder/'boundary.c'
        stub.write_text('#include <stdint.h>\n#include "board.h"\n#include "ai.h"\n#include "setup.h"\nuint8_t board[SQUARES],game_rules=0,ai_difficulty=AI_NORMAL;\nuint16_t random_next(void){return 123u;}\nvoid setup_random(uint8_t blue){(void)blue;}\n')
        library=self.folder/'boundary.so'
        subprocess.run(['gcc','-O2','-shared','-fPIC','-Wno-unknown-pragmas','-Isrc/core',
            '-DAI_DEPLOY_FORTRESS_ONLY','-DAI_FORTRESS_INNER_GUARD',str(SOURCE),str(stub),'-o',str(library)],
            cwd=ROOT,check=True,capture_output=True)
        native=ctypes.CDLL(str(library));board=(ctypes.c_uint8*100).in_dll(native,'board')
        for army in (0,1):
            own=setup_squares(army);outputs=[]
            for salt in (0,1,7,31,254):
                for sq in range(100):board[sq]=(sq*17+salt)%256
                previous=list(board);native.setup_ai(army)
                outputs.append([board[sq] for sq in own])
                self.assertTrue(all(board[sq]==previous[sq] for sq in range(100) if sq not in own))
            self.assertTrue(all(row==outputs[0] for row in outputs))


if __name__=='__main__':unittest.main()
