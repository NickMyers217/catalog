# This file contains the HTTP routes for the website

from flask import Flask, render_template


# Define the app
app = Flask(__name__)


# Route for the catalog page
@app.route('/')
@app.route('/catalog/')
def landing():
    return render_template('catalog.html')


# Route to show a catedories items
@app.route('/catalog/<category>/')
@app.route('/catalog/<category>/items/')
def items(category):
    return 'Items for %s!' % category


# Route to show a single item within a category
@app.route('/catalog/<category>/<item>/')
def itemDesc(category, item):
    return 'Description page for %s in the %s category!' % (item, category)


# Start the server
if __name__ == '__main__':
    app.run(host = '0.0.0.0', port = 8080, debug = True)
