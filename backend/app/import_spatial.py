"""Explicit production-safe reference import. No migrations, accounts or demo data."""
import argparse
import json
from .config import Settings
from .db import make_engine, make_session_factory
from .spatial import import_package
from .common import DomainError
from sqlalchemy.exc import SQLAlchemyError


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    action=parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--check',action='store_true',help='Read-only additions/metadata/removal plan')
    action.add_argument('--apply',action='store_true',help='Atomically apply only safe reference changes')
    parser.add_argument('--expected-version',help='Require the exact operator-selected package manifest version')
    args=parser.parse_args();settings=Settings(worker_enabled=False)
    engine=make_engine(settings.database_url)
    try:
        with make_session_factory(engine)() as db:
            if args.check and engine.dialect.name=='sqlite':
                db.connection(execution_options={'sqlite_write':False})
            result=import_package(db,settings,apply=args.apply,expected_version=args.expected_version)
            if args.apply:
                db.commit()
            print(json.dumps(result,ensure_ascii=False,sort_keys=True,allow_nan=False))
            if not result['applicable']:
                raise SystemExit(2)
    except DomainError as exc:
        print(json.dumps({'error':{'code':exc.code,'message':exc.message,'details':exc.details}},ensure_ascii=False))
        raise SystemExit(2) from None
    except SQLAlchemyError:
        print(json.dumps({"error":{"code":"database_unavailable","message":"Reference import could not complete its database transaction; check connectivity and run migrations first"}}))
        raise SystemExit(2) from None
    finally:
        engine.dispose()


if __name__=='__main__':
    main()
