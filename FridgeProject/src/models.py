from sqlalchemy import Column, Integer, String, DateTime, Boolean
from src.database import Base
from datetime import datetime

class Item(Base):
    __tablename__ = 'items'
    id = Column(Integer, primary_key=True)
    label = Column(String(50), nullable=False)
    entry_date = Column(DateTime, default=datetime.utcnow)
    last_confirmed = Column(DateTime, default=datetime.utcnow)
    image_path = Column(String(200)) # Path to the image where it was last seen
    status = Column(String(20), default='active') # active, removed

    def __repr__(self):
        return f'<Item {self.label!r} status={self.status!r}>'

    def to_dict(self):
        return {
            'id': self.id,
            'label': self.label,
            'entry_date': self.entry_date.isoformat() if self.entry_date else None,
            'last_confirmed': self.last_confirmed.isoformat() if self.last_confirmed else None,
            'image_path': self.image_path,
            'status': self.status
        }

class ProductType(Base):
    __tablename__ = 'product_types'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    shelf_life_days = Column(Integer, default=7)
    is_basic = Column(Boolean, default=False)

    def __repr__(self):
        return f'<ProductType {self.name!r}>'
