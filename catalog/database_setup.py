import sys

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()

class CatalogCategory(Base):
    __tablename__ = 'catalog_category'

    name = Column(String(80), nullable = False)
    id = Column(Integer, primary_key = True)

class CategoryItem(Base):
    __tablename__ = 'category_item'

    title = Column(String(80), nullable = False)
    id = Column(Integer, primary_key = True)
    user = Column(String(200), nullable = False)
    description = Column(String(250))
    category_id = Column(Integer, ForeignKey('catalog_category.id'))
    category = relationship(CatalogCategory)

    @property
    def serialize(self):
        #returns in json format
        return {
            'title': self.title,
            'description': self.description,
            'id': self.id,
            'category': self.category.id
        }

engine = create_engine('sqlite:///catalog.db')
Base.metadata.create_all(engine)
