from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, declarative_base

# Create the database engine.
# We use check_same_thread=False because SQLite connection objects
# cannot be shared between threads, but SQLAlchemy handles pooling.
engine = create_engine('sqlite:///fridge.db', connect_args={'check_same_thread': False})

# Create a configured "Session" class
db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))

# Create a Base class for our models
Base = declarative_base()
Base.query = db_session.query_property()

def init_db():
    # import all modules here that might define models so that
    # they will be registered properly on the metadata.
    import src.models
    Base.metadata.create_all(bind=engine)
    seed_data()

def seed_data():
    from src.models import ProductType
    from src.utils import SHELF_LIFE, BASIC_ITEMS

    # Check if we already have data
    if ProductType.query.first() is not None:
        return

    print("Seeding database with initial product types...")

    # Combine all unique names from SHELF_LIFE and BASIC_ITEMS
    all_names = set(SHELF_LIFE.keys()) | set(BASIC_ITEMS)

    for name in all_names:
        days = SHELF_LIFE.get(name, 7)
        is_basic = name in BASIC_ITEMS
        pt = ProductType(name=name, shelf_life_days=days, is_basic=is_basic)
        db_session.add(pt)

    db_session.commit()
    print("Database seeding complete.")
