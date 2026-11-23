import argparse
from .db import Base, engine
from . import models  # noqa

def main():
    p=argparse.ArgumentParser(description="Initialize local Reliability TRI database")
    p.add_argument("--yes",action="store_true",help="Create missing tables (development only)")
    args=p.parse_args()
    if not args.yes: p.error("Pass --yes to create tables. Production should use Alembic migrations.")
    Base.metadata.create_all(bind=engine)
    print("Development database tables created.")

if __name__=="__main__": main()
