"""Teacher horizon, consistent sampling and oracle-input isolation checks."""
import copy
import json
from pathlib import Path
import random
import subprocess
import unittest
import zipfile

from feldmarschall import ROOT, COUNTS, LAKES
from train_ai_student import label, sample_world, predict


class TeacherTests(unittest.TestCase):
    def test_capture_exchange_horizon(self):
        cells=[255]*100
        for sq in LAKES: cells[sq]=254
        for sq,cell in {60:1,51:9,99:11,50:4|16|32,40:0|16|32,0:11|16|32}.items(): cells[sq]=cell
        process=subprocess.Popen([str(ROOT/'build/feldmarschall-teacher')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
        results={}
        try:
            for depth in (2,3):
                process.stdin.write(f'search 0 {depth} {bytes(cells).hex()} ffffffff0000\n');process.stdin.flush()
                scores={}
                while True:
                    fields=process.stdout.readline().split()
                    if fields[0]=='done': break
                    self.assertEqual(fields[0],'action')
                    scores[tuple(map(int,fields[1:3]))]=int(fields[3])
                results[depth]=scores
            self.assertEqual(results[2][(60,50)],-155)
            self.assertEqual(results[3][(60,50)],45)
            self.assertEqual(max(results[3],key=results[3].get),(60,50))
        finally:
            process.stdin.close();process.wait();process.stdout.close()

    def test_public_inventory_sampling(self):
        cells=[255]*100;cells[99]=11
        histories={}
        for sq in range(4):
            moved=sq in (1,2);cells[sq]=12|16|(64 if moved else 0)
            histories[sq]=[sq,sq,sq,sq,16,int(moved),0,12,12,12,0x03ff if moved else 0x0fff]
        lost=COUNTS[:]
        for rank in (0,1,10,11):lost[rank]-=1
        rng=random.Random(8675309)
        for _ in range(100):
            world,weight=sample_world(cells,lost,histories,rng,0)
            self.assertEqual(sorted(world[sq]&15 for sq in range(4)),[0,1,10,11])
            self.assertLess(world[1]&15,10);self.assertLess(world[2]&15,10)
            self.assertEqual(world[99],11);self.assertEqual(weight,1)
        self.assertEqual(cells[0],28) # no mutation of the masked input

    def test_oracle_fields_cannot_change_labels(self):
        with zipfile.ZipFile(ROOT/'docs/ai-diagnostics/positions-20261014.zip') as archive:
            records=[json.loads(line) for line in archive.read('positions.jsonl').splitlines()]
        record=next(r for r in records if any(bytes.fromhex(r['input']['board_hex'])[to]<254 for _,to in r['legal_moves']))
        altered=copy.deepcopy(record)
        altered['referee_board']=None;altered['replay']=None;altered['labels']=['arbitrary'];altered['evidence']=None
        job=(ROOT/'build/feldmarschall-engine-features',ROOT/'build/feldmarschall-teacher',4,1234567)
        self.assertEqual(label((record,*job)),label((altered,*job)))

    def test_integer_model_bounds_and_split_isolation(self):
        path=ROOT/'build/ai-student/teacher-v1'
        if (path/'model.json').exists():
            model=json.loads((path/'model.json').read_text())
            data=(path/'labels.jsonl').read_bytes()
        else:
            with zipfile.ZipFile(ROOT/'docs/ai-student/offline-tactical-20261014.zip') as archive:
                model=json.loads(archive.read('training/model.json'));data=archive.read('training/labels.jsonl')
        rows=[json.loads(line) for line in data.splitlines()]
        self.assertLessEqual(len(model['nodes']),31)
        self.assertEqual(model['node_bytes'],len(model['nodes'])*6)
        train={row['split_group'] for row in rows if not row['validation']}
        validation={row['split_group'] for row in rows if row['validation']}
        self.assertFalse(train&validation)
        for row in rows:
            self.assertEqual(len(row['features']),16)
            self.assertTrue(all(0<=value<=255 for value in row['features']))
            self.assertLessEqual(abs(predict(model['nodes'],row['features'])),192)


if __name__=='__main__':unittest.main()
