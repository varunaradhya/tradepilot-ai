from __future__ import annotations
from pathlib import Path
from urllib.request import urlopen

URL='https://images.dhan.co/api-data/api-scrip-master-detailed.csv'
OUT=Path('data/reference/dhan_scrip_master_detailed.csv')

def main():
    OUT.parent.mkdir(parents=True,exist_ok=True)
    with urlopen(URL,timeout=60) as r: OUT.write_bytes(r.read())
    print(f'Saved Dhan instrument master: {OUT} ({OUT.stat().st_size:,} bytes)')
if __name__=='__main__': main()
