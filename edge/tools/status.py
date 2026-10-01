"""Read-only gateway backlog/health inspection; never echoes payloads or secrets."""
from contextlib import closing
import argparse
import json
from pathlib import Path
import sqlite3
import urllib.parse
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--database',type=Path,required=True);args=p.parse_args()
if not args.database.is_file():raise SystemExit('Gateway database does not exist')
uri='file:'+urllib.parse.quote(str(args.database.resolve()))+'?mode=ro'
with closing(sqlite3.connect(uri,uri=True)) as db, db:
    tables={row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    out={}
    for table in ('forwarding','delivery_outbox'):
        if table in tables:
            out[table]={'pending':db.execute(f'SELECT count(*) FROM {table} WHERE delivered=0 AND blocked=0').fetchone()[0],
                        'blocked':db.execute(f'SELECT count(*) FROM {table} WHERE delivered=0 AND blocked=1').fetchone()[0],
                        'delivered':db.execute(f'SELECT count(*) FROM {table} WHERE delivered=1').fetchone()[0]}
    if 'edge_schema_migrations' in tables:out['schema_migrations']=[{'version':v,'applied':at,'summary':json.loads(summary)} for v,at,summary in db.execute('SELECT * FROM edge_schema_migrations ORDER BY applied')]
    if 'migration_quarantine' in tables:out['unresolved_migration_rows']=db.execute('SELECT count(*) FROM migration_quarantine WHERE resolved=0').fetchone()[0]
    if 'command_inbox' in tables:out['command_states']=dict(db.execute('SELECT state,count(*) FROM command_inbox GROUP BY state'))
    if 'ingress_health' in tables:out['transport_health']=[{'key':key,'value':json.loads(value),'updated':updated} for key,value,updated in db.execute('SELECT key,value,updated FROM ingress_health ORDER BY key')]
    if 'rule_evaluations' in tables:out['local_rules']=[{'id':ident,'status':status,'reason':reason,'updated':updated} for ident,status,reason,updated in db.execute('SELECT * FROM rule_evaluations ORDER BY id')]
print(json.dumps(out,ensure_ascii=False,indent=2))
