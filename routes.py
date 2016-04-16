# This file contains the HTTP routes for the website

from flask import Flask, render_template
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base, Category, Item


# Set up the database session
engine = create_engine('sqlite:///catalog.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind = engine)
db = DBSession()


# Define the app
app = Flask(__name__)


# Route for the catalog page
@app.route('/')
@app.route('/catalog/')
def landing():
    cats = db.query(Category).all()
    items = db.query(Item).all()
    return render_template('catalog.html', cats = cats, items = items)


# Route to show a categorie's items
@app.route('/catalog/<cat_name>/')
@app.route('/catalog/<cat_name>/items/')
def items(cat_name):
    category = db.query(Category).filter_by(name = cat_name)
    if category.count() == 0:
        return '404 not found'
    items = db.query(Item).filter_by(category_id = category.one().id)
    return render_template('items.html',
                           cat   = cat_name,
                           items = items.all(),
                           cnt   = items.count())


# Route to show a single item within a category
@app.route('/catalog/<cat_name>/<item_name>/')
def itemDesc(cat_name, item_name):
    category = db.query(Category).filter_by(name = cat_name)
    if category.count() == 0:
        return '404 not found'
    item = db.query(Item).filter_by(category_id = category.one().id,
                                    name = item_name)
    if item.count() == 0:
        return '404 not found'
    return render_template('item.html', cat = cat_name, item = item.one())


# Start the server
if __name__ == '__main__':
    app.run(host = '0.0.0.0', port = 8080, debug = True)
