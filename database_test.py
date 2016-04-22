# This file includes tests to ensure the database is working properly

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base, Category, Item


# Set up the database session
engine = create_engine('sqlite:///catalog.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind = engine)
session = DBSession()


# Insert a few categories
print 'Adding categories!'

session.add_all([Category(name = 'Soccer'),
                 Category(name = 'Basketball'),
                 Category(name = 'Baseball'),
                 Category(name = 'Frisbee'),
                 Category(name = 'Snowboarding'),
                 Category(name = 'Rock Climbing'),
                 Category(name = 'Foosball'),
                 Category(name = 'Skating'),
                 Category(name = 'Hockey')])
session.commit()

print 'Success!\n'


# Print the categories out
print 'Printing categories!'

for c in session.query(Category).all():
    print c.name

print 'Success!\n'
