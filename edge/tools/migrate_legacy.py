"""Explicit offline migration/review retry. Stop the prior gateway and back up DB/WAL first."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from config import enrollments
from migrations import migrate_legacy_outbox
from service import strict_json
from store import EdgeStore
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--database',type=Path,required=True);p.add_argument('--devices',type=Path,required=True)
p.add_argument('--retry-quarantine',action='store_true',help='Explicitly retry after correcting enrollment; original evidence/time is still required')
args=p.parse_args()
if not args.database.is_file():raise SystemExit('Existing database is required; not creating a migration fixture')
store=EdgeStore(args.database)
try:print(json.dumps(migrate_legacy_outbox(store,enrollments(strict_json(args.devices.read_bytes(),maximum=65536)),args.retry_quarantine),indent=2))
finally:store.close()
