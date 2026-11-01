import os
from pathlib import Path
from sqlalchemy import create_engine, Column, String, JSON
from sqlalchemy.orm import declarative_base, sessionmaker

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(os.getenv('BIOFORGE_DATA_DIR', str(ROOT / 'data')))
DATA.mkdir(parents=True, exist_ok=True)
engine = create_engine(os.getenv('DATABASE_URL', 'sqlite:///' + str(DATA/'bioforge.db')), **({'connect_args': {'check_same_thread': False}} if not os.getenv('DATABASE_URL','').startswith('postgres') else {}))
Session = sessionmaker(bind=engine)
Base = declarative_base()
class Record(Base):
    __tablename__ = 'records'
    id = Column(String, primary_key=True)
    category = Column(String, index=True, nullable=False)
    payload = Column(JSON, nullable=False)
Base.metadata.create_all(engine)

def put(category, payload):
    with Session.begin() as session:
        session.merge(Record(id=payload['id'],category=category,payload=payload))
    return payload

def all_records(category):
    with Session() as session:
        return [r.payload for r in session.query(Record).filter_by(category=category).all()]

def get(identifier, category=None):
    with Session() as session:
        record = session.get(Record, identifier)
        if record is None or (category and record.category != category):
            return None
        return record.payload
