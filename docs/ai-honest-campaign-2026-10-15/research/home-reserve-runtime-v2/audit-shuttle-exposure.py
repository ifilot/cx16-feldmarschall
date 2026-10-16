"""Count the corrected enemy-shuttle condition in existing screened public roots."""
import gzip,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'tools'))
from campaign_flag_guard import position_from_public
OUT=Path(__file__).resolve().parent
source=OUT.parent/'home-miner-interceptor-v1/result.json.gz'
data=json.loads(gzip.decompress(source.read_bytes()));hits=[]
for row in data['screened_known_Miner_roots']:
 p=position_from_public(bytes.fromhex(row['public_board_hex']),row['army'],row['shuttle_hex'])
 old,last,count=p.shuttle[1-row['army']]
 if count>=5 and last is not None and p.cells[last] and p.cells[last][3] and p.cells[last][1]==7:
  hits.append(dict(game=row['game'],ply=row['ply'],shuttle=[old,last,count]))
result=dict(roots=len(data['screened_known_Miner_roots']),active_disclosed_Miner_shuttle_roots=len(hits),hits=hits,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),scope='Completed C21 screening public-state condition only; no fresh validation or strength claim.')
(OUT/'shuttle-exposure.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
