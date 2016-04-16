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

frisbee = Category(name = 'Frisbee')
tennis = Category(name = 'Tennis')
soccer = Category(name = 'Soccer')
session.add_all([frisbee, tennis, soccer])
session.commit()

print 'Success!\n'


# Print the categories out
print 'Printing categories!'

for c in session.query(Category).all():
    print c.name

print 'Success!\n'


# Add some items
print 'Addind a bunch of items!'

item1 = Item(name = 'Super duper frisbee',
             desc = 'This frisbee is reall cool.... blah blah blah',
             category = frisbee)
item2 = Item(name = 'Tennis balls',
             desc = 'Bouncy tennis balls',
             category = tennis)
item3 = Item(name = 'Tennis racket',
             desc = 'A racket!',
             category = tennis)
item4 = Item(name = 'Soccer ball',
             desc = 'WILSONNNNNNN!',
             category = soccer)

session.add_all([item1, item2, item3, item4])
session.commit()

print 'Success!\n'


# print the items out
print 'Printing items!\n'

for i in session.query(Item).all():
    print '%s: %s\n%s\n' % (i.category.name, i.name, i.desc)

print 'Success!\n'
