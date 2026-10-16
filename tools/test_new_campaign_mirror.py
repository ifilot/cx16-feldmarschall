"""Complete-formation reflection using existing Fortress setup tickets only."""
from collections import Counter
import ctypes,hashlib,json,re,shlex,subprocess,tempfile,unittest
from pathlib import Path

from ai_registry import ROOT,get_policy
from feldmarschall import Engine,GLYPHS,setup_squares,valid_setup
from test_ai_selection import next_random
from tournament_store import mirror_setup
from research_deployment_double_shell import geometry

SOURCE=ROOT/'tools/new_campaign_mirror_deploy.c'
OUT=ROOT/'docs/ai-honest-campaign-2026-10-16/research/mirror-deployment'
MODES={'control':None,'default-off':None,'mirror':'AI_FORTRESS_MIRROR_ONLY','mixture':'AI_FORTRESS_MIRROR_MIX'}


def accepted(seed):
    draw=next_random(seed)
    while draw>65530:draw=next_random(draw)
    return draw,(draw-1)%10


class MirrorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(prefix='mirror-deployment-');cls.folder=Path(cls.tmp.name)
        cls.programs={};cls.libraries={};cls.records=[];cls.enumeration={}
        arrays=re.findall(r'\{([\d,]+)\}',(ROOT/'src/core/ai_deploy.c').read_text())
        row=next(a for a in arrays if len(a.split(','))==40)
        cls.base=''.join(GLYPHS[int(v)]for v in row.split(','));cls.mirrored=mirror_setup(cls.base)
        spec=get_policy('student-fortress-template-flag-bomb-v1-normal')
        engine=(ROOT/'src/native/engine.c').read_text();anchor='        } else if(!strcmp(command, "seed")) {'
        assert engine.count(anchor)==1
        engine=engine.replace(anchor,'        } else if(!strcmp(command,"fixture-rng")) { printf("rng %u\\n",random_current());fflush(stdout);\n'+anchor)
        (cls.folder/'engine.c').write_text(engine)
        for mode,flag in MODES.items():
            directory=cls.folder/mode;directory.mkdir()
            deploy=directory/'ai_deploy.c';deploy.write_bytes((ROOT/'src/core/ai_deploy.c' if mode=='control' else SOURCE).read_bytes())
            extra=[] if flag is None else [flag]
            sources=[str(cls.folder/'engine.c')if s=='src/native/engine.c' else str(deploy)if s=='src/core/ai_deploy.c' else s for s in spec['sources']]
            command=['gcc','-O2','-std=c99','-Wno-unknown-pragmas','-Isrc/core']+['-D'+f for f in spec['defines']+extra]+sources+['-o',str(directory/'engine')]
            subprocess.run(command,cwd=ROOT,check=True,capture_output=True);cls.programs[mode]=directory/'engine'
            library=directory/'setup.so'
            parts=[str(ROOT/'src/core'/(p+'.c'))for p in ('pieces','board','rules','random','ai_level','setup')]+[str(deploy)]
            subprocess.run(['gcc','-shared','-fPIC','-O2','-Wno-unknown-pragmas','-Isrc/core','-DAI_TEST','-DAI_DEPLOY_FORTRESS_ONLY']+['-D'+f for f in extra]+parts+['-o',str(library)],cwd=ROOT,check=True,capture_output=True)
            lib=ctypes.CDLL(str(library));lib.random_current.restype=ctypes.c_uint16
            cls.libraries[mode]=(lib,(ctypes.c_uint8*100).in_dll(lib,'board'),ctypes.c_uint8.in_dll(lib,'ai_difficulty'),ctypes.c_uint8.in_dll(lib,'game_rules'))

    @classmethod
    def tearDownClass(cls):
        OUT.mkdir(parents=True,exist_ok=True)
        doc=dict(scope='Deployment composition, ticket and real native protocol components; no saved strength games',
            source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in (SOURCE,Path(__file__),ROOT/'src/core/ai_deploy.c')},
            original=cls.base,mirrored=cls.mirrored,native_cases=cls.records,exhaustive_seed_mapping=cls.enumeration,
            mixture_contract='Five of ten accepted tickets select each orientation, no new draws. Accepted raw draw values are balanced; deterministic retry trajectories slightly imbalance uniform initial nonzero seeds.',
            geometry={name:geometry(s)for name,s in [('original',cls.base),('mirrored',cls.mirrored)]})
        (OUT/'component.json').write_text(json.dumps(doc,indent=2)+'\n');cls.tmp.cleanup()

    def test_exact_inventory_complete_reflection_and_structural_equivalence(self):
        self.assertTrue(valid_setup(self.mirrored));self.assertEqual(sorted(self.base),sorted(self.mirrored))
        self.assertEqual(mirror_setup(self.mirrored),self.base)
        self.assertEqual(self.mirrored.index('F'),39);self.assertEqual(self.mirrored.index('S'),22)
        a,b=geometry(self.base),geometry(self.mirrored)
        for key in ('min_bomb_captures_from_front','mobile_pieces_with_permanent_front_access','mobile_exit_distance_sum'):self.assertEqual(a[key],b[key])
        self.assertEqual(a['trapped_mobile_squares'],[38]);self.assertEqual(b['trapped_mobile_squares'],[31])

    def test_accepted_ticket_classes_exactly_five_each(self):
        counts=Counter((value-1)%10 for value in range(1,65531))
        self.assertEqual(set(counts.values()),{6553})
        self.assertEqual(sum(v for k,v in counts.items()if k<5),32765)
        self.assertEqual(sum(v for k,v in counts.items()if k>=5),32765)

    def test_actual_native_all_nonzero_seeds_both_colors_no_extra_rng(self):
        for mode in ('mirror','mixture'):
            lib,cells,level,rules=self.libraries[mode];level.value=1;rules.value=0
            for army in (0,1):
                counts=Counter();squares=setup_squares(army)
                for seed in range(1,65536):
                    draw,ticket=accepted(seed);want_mirror=mode=='mirror' or ticket>=5
                    lib.random_seed(seed);lib.setup_ai(army)
                    self.assertEqual(cells[squares[39 if want_mirror else 30]]&15,11)
                    self.assertEqual(lib.random_current(),draw)
                    counts['mirror' if want_mirror else 'original']+=1
                self.enumeration[mode+'-'+str(army)]=dict(counts)
                if mode=='mixture':self.assertEqual(dict(counts),dict(original=32766,mirror=32769))

    def setup(self,bot,army,seed,level,rules):
        for command in ('new '+('red','blue')[army],'rules '+str(rules),'difficulty '+level,'seed '+str(seed)):bot.send(command)
        return bot.ask('setup','setup')

    def test_real_native_layout_rng_force_common_policy_and_fallbacks(self):
        bots={m:Engine(shlex.quote(str(p)))for m,p in self.programs.items()}
        rejected=[s for s in range(1,65536)if next_random(s)>65530]
        try:
            for army in (0,1):
                for level,rules in (('normal',0),('easy',0),('hard',0),('normal',1)):
                    for seed in (1,17,791,65535,*rejected):
                        setups={m:self.setup(b,army,seed,level,rules)for m,b in bots.items()}
                        self.assertEqual(setups['control'],setups['default-off'])
                        if level=='normal' and rules==0:
                            self.assertEqual(setups['control'],self.base);self.assertEqual(setups['mirror'],self.mirrored)
                            self.assertEqual(setups['mixture'],self.mirrored if accepted(seed)[1]>=5 else self.base)
                        else:self.assertEqual(len(set(setups.values())),1)
                        self.assertEqual(len({b.ask('fixture-rng','rng')for b in bots.values()}),1)
                        for b in bots.values():b.send('setup '+self.base)
                        self.assertEqual(len({b.ask('go','move')for b in bots.values()}),1)
                        self.records.append(dict(army=army,level=level,rules=rules,seed=seed,setups=setups,rng_and_common_army_decision_equal=True))
        finally:
            for bot in bots.values():bot.close()

    def test_private_enemy_board_cannot_select_orientation_or_change_outside_cells(self):
        for mode in ('control','mirror','mixture'):
            lib,cells,level,rules=self.libraries[mode];level.value=1;rules.value=0
            for army in (0,1):
                own=set(setup_squares(army));answers=[]
                for salt in (0,1,7,31,254):
                    for sq in range(100):cells[sq]=(sq*17+salt)%256
                    before=bytes(cells);lib.random_seed(791);lib.setup_ai(army)
                    answers.append(bytes(cells[sq]for sq in sorted(own)))
                    self.assertTrue(all(cells[sq]==before[sq]for sq in range(100)if sq not in own))
                self.assertEqual(len(set(answers)),1)

    def test_macro_requirements_and_exclusivity(self):
        cases=[['AI_FORTRESS_MIRROR_ONLY'],['AI_DEPLOY_FORTRESS_ONLY','AI_FORTRESS_MIRROR_ONLY','AI_FORTRESS_MIRROR_MIX'],
               ['AI_DEPLOY_FORTRESS_ONLY','AI_FORTRESS_MIRROR_ONLY','AI_DEPLOY_DOUBLE_SHELL']]
        for defines in cases:
            r=subprocess.run(['gcc','-E','-Isrc/core']+['-D'+f for f in defines]+[str(SOURCE)],cwd=ROOT,capture_output=True,text=True)
            self.assertNotEqual(r.returncode,0)


if __name__=='__main__':unittest.main()
