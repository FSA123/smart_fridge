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
