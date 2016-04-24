# This file contains the ORM code to setup the database

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine


Base = declarative_base()


# Map the user table
class User(Base):
    __tablename__ = 'user'

    id            = Column(Integer, primary_key = True)
    name          = Column(String(250), nullable = False)
    email         = Column(String(250), nullable = False)
    picture       = Column(String(500), nullable = False)


# Map the category table
class Category(Base):
    __tablename__ = 'category'

    id            = Column(Integer, primary_key = True)
    name          = Column(String(80), nullable = False)

    @property
    def serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            'items': []
        }
    

# Map the item table
class Item(Base):
    __tablename__ = 'item'

    id            = Column(Integer, primary_key = True)
    user_id       = Column(Integer, ForeignKey('user.id'))
    category_id   = Column(Integer, ForeignKey('category.id'))
    name          = Column(String(80), nullable = False)
    desc          = Column(String(500), nullable = False)
    user          = relationship(User)
    category      = relationship(Category)

    @property
    def serialize(self):
        return {
            'category_id': self.category_id,
            'desc': self.desc,
            'id': self.id,
            'name': self.name
        }


engine = create_engine('sqlite:///catalog.db')
Base.metadata.create_all(engine)
