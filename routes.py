# This file contains the HTTP routes for the website

import random, string, json, httplib2, requests

from flask import Flask, render_template, request, redirect, url_for, session, make_response
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base, Category, Item
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError


# Set up the database session
engine = create_engine('sqlite:///catalog.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind = engine)
db = DBSession()


# Read the Google client id from the google provided client_secrets.json file
CLIENT_ID = json.loads(open('client_secrets.json', 'r').read())['web']['client_id']


# Define the app
app = Flask(__name__)


# Utility for making JSON responses
def quick_json_res(msg, code):
    ''' This function returns a constructed JSON response
      Args:
        msg: The message
        code: The http result code
    '''
    response = make_response(json.dumps(msg), code)
    response.headers['Content-Type'] = 'application/json'
    return response


# Ajax route for google oauth
@app.route('/googleLogin', methods=['POST'])
def googleLogin():
    print 'Beginnig google oauth login!'

    # Verify the anti xss forgery token from the client matches
    if request.args.get('state') != session['state']:
        err = 'This might be an xss attack, aborted!'
        print err
        return quick_json_res(err, 401)

    # Since this is not an xss attack, we can proceed
    # and exchange the one time authorization code from google
    code = request.data
    try:
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
        print 'Code exchanged!'
    except FlowExchangeError:
        err = 'Error while exchanging Code!'
        print err
        return quick_json_res(err, 401)

    # If we get back an access token, we can validate it is valid
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    if result.get('error') is not None:
        print result.get('error')
        return quick_json_res(result.get('error'), 400)

    # The access token is valid, but is it for the correct user?
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        err = 'Token for wrong user!'
        print err
        return quick_json_res(err, 401)

    # Make sure the token has the same client ID as this app
    if result['issued_to'] != CLIENT_ID:
        err = 'Token for wrong app!'
        print err
        return quick_json_res(err, 401)

    # See if the user is already logged in
    stored_credentials = session.get('credentials')
    stored_gplus_id = session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        err = 'User already logged in!'
        print err
        return quick_json_res(err, 200)

    # The user is not logged in, so we need to store his stuff
    session['credentials'] = credentials.to_json()
    session['gplus_id'] = gplus_id
    userinfo_url = 'https://www.googleapis.com/oauth2/v1/userinfo'
    params = { 'access_token': credentials.access_token, 'alt': 'json' }
    answer = requests.get(userinfo_url, params = params)
    data = answer.json()
    session['username'] = data['name']
    session['picture'] = data['picture']
    session['email'] = data['email']

    output = ''
    output += '<h1>Welcome, '
    output += session['username']
    output += '!</h1>'
    output += '<img src="'
    output += session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '

    print 'Success!'
    return output


# Route to disconnect a Google user
@app.route('/googleLogout')
def googleLogout():
    # Check to make sure the user is actually logged in
    credentials = session.get('credentials')
    if credentials is None:
        return quick_json_res('Current user not logged in.', 401)

    # Use the google api to revoke the token
    credentials = credentials.from_json()
    token = credentials.access_token
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]

    # Delete their information
    if result['status'] == '200':
        del session['credentials']
        del session['gplus_id']
        del session['username']
        del session['email']
        del session['picture']
        return quick_json_res('Disconnected!', 200)
    else:
        return quick_json_res('Failed to revoke token!', 400)


# Route for the catalog page
@app.route('/')
@app.route('/catalog')
def landing():
    cats = db.query(Category).all()
    items = db.query(Item).all()
    return render_template('catalog.html', cats = cats, items = items)


# Route for logging in
@app.route('/login')
def showLogin():
    # Generate and store an anti forgery token to prevent xss attacks
    # it can be passed to the view, and then to any ajax login requests
    # if it doesn't match the same code still stored, its not the same user
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    session['state'] = state
    return render_template('login.html', state = session['state'])


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


# Route to edit items
@app.route('/catalog/<item_name>/edit/', methods = ['GET', 'POST'])
def itemEdit(item_name):
    if request.method == 'GET':
        item = db.query(Item).filter_by(name = item_name)
        if item.count() == 0:
            return '404 not found'
        return render_template('item_edit.html', item = item.one())
    if request.method == 'POST':
        item = db.query(Item).filter_by(name = item_name)
        if item.count() == 0:
            return redirect(url_for('landing'))
        item = item.one()
        item.name = request.form['name']
        item.desc = request.form['desc']
        db.add(item)
        db.commit()
        return redirect(url_for('landing'))


# Route to delete items
@app.route('/catalog/<item_name>/delete/', methods = ['GET', 'POST'])
def itemDelete(item_name):
    if request.method == 'GET':
        item = db.query(Item).filter_by(name = item_name)
        if item.count() == 0:
            return '404 not found'
        return render_template('item_delete.html', item = item.one())
    if request.method == 'POST':
        item = db.query(Item).filter_by(name = item_name)
        if item.count() == 0:
            return redirect(url_for('landing'))
        db.delete(item.one())
        db.commit()
        return redirect(url_for('landing'))


# Start the server
if __name__ == '__main__':
    import uuid
    app.secret_key = str(uuid.uuid4())
    app.debug = True
    app.run(host = '0.0.0.0', port = 8080)
