# This file contains the HTTP routes for the website

import random, string, json, httplib2, requests

from flask import Flask, render_template, request, redirect, url_for, session, make_response
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base, Category, Item, User
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


# Utility for seeing if a user is logged in
def is_logged_in():
    ''' Returns true if the user is logged in '''
    return 'username' in session


# Utility for querying usert in the database
def get_user_info(user_id):
    ''' Returns a user from the database
      Args:
        user_id: The id of the user to retrieve
    '''
    return db.query(User).filter_by(id=user_id).one()


# Utility for querying users based on an email
def get_user_id(email):
    ''' Returns the id of the user if found, or None
      Args:
        email: The email of the user to look up
    '''
    try:
        return db.query(User).filter_by(email=email).one().id
    except:
        return None


# Utility for creating a user
def create_user():
    ''' Creates a user in the database and returns their id '''
    # Query the user email to see if they already exist
    user_id = get_user_id(session['email'])

    # Create them if needed, otherwise just return the ID
    if user_id is None:
        new_user = User(name=session['username'], email=session['email'], picture=session['picture'])
        db.add(new_user)
        db.commit()
        return db.query(User).filter_by(email=session['email']).one().id
    else:
        return user_id


# Route for the catalog page
@app.route('/')
@app.route('/catalog')
def landing():
    cats = db.query(Category).all()
    items = db.query(Item).limit(10).all()
    return render_template('catalog.html', cats=cats, items=items, logged_in=is_logged_in())


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
    session['credentials'] = credentials.access_token
    session['gplus_id'] = gplus_id
    userinfo_url = 'https://www.googleapis.com/oauth2/v1/userinfo'
    params = { 'access_token': credentials.access_token, 'alt': 'json' }
    answer = requests.get(userinfo_url, params=params)
    data = answer.json()
    session['username'] = data['name']
    session['picture'] = data['picture']
    session['email'] = data['email']
    create_user()

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
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % credentials
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


# Route for logging in
@app.route('/login')
def showLogin():
    # Generate and store an anti forgery token to prevent xss attacks
    # it can be passed to the view, and then to any ajax login requests
    # if it doesn't match the same code still stored, its not the same user
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    session['state'] = state
    return render_template('login.html', state=session['state'], logged_in=is_logged_in())


# Route to show a categorie's items
@app.route('/catalog/<cat_name>/')
@app.route('/catalog/<cat_name>/items/')
def items(cat_name):
    cats = db.query(Category).all()
    category = db.query(Category).filter_by(name=cat_name)
    # Make sure the category exists
    if category.count() == 0:
        return '404 not found'
    items = db.query(Item).filter_by(category_id = category.one().id)
    return render_template('items.html', cats=cats, cat=cat_name, items=items.all(), cnt=items.count(),
                           logged_in=is_logged_in())


# Route to show a single item within a category
@app.route('/catalog/<cat_name>/<item_name>/')
def itemDesc(cat_name, item_name):
    category = db.query(Category).filter_by(name=cat_name)
    # Make sure the category exists
    if category.count() == 0:
        return '404 not found'
    item = db.query(Item).filter_by(category_id=category.one().id, name=item_name)
    # Make sure th item exists
    if item.count() == 0:
        return '404 not found'
    # See if the user created this item, if so they can edit it
    can_edit = is_logged_in() and get_user_id(session['email']) == item.one().user_id
    return render_template('item.html', cat=cat_name, item=item.one(), can_edit=can_edit,
                           logged_in=is_logged_in())


# Route to add a new item
@app.route('/catalog/new/', methods = ['GET', 'POST'])
def itemNew():
    # Force user to log in
    if not is_logged_in():
        return redirect(url_for('showLogin'))

    # Display the form for GET requests
    if request.method == 'GET':
        cats = db.query(Category)
        return render_template('item_new.html', numcats=cats.count(), cats=cats.all(),
                               logged_in=is_logged_in())
    
    # Handle the database for POST requests
    if request.method == 'POST':
        item_name = request.form['item_name']
        item_desc = request.form['item_desc']
        item_cat_name = request.form['item_cat_name']
        cats = db.query(Category).filter_by(name=item_cat_name)
        # Make sure the item's category is valid
        if cats.count() > 0:
            # Add the item to the database
            user_id = get_user_id(session['email'])
            item = Item(name=item_name, desc=item_desc, category=cats.one(), user_id=user_id)
            db.add(item)
            db.commit()
        # Redirect to landing
        return redirect(url_for('landing'))


# Route to edit items
@app.route('/catalog/<item_name>/edit/', methods=['GET', 'POST'])
def itemEdit(item_name):
    # Force user to log in
    if not is_logged_in():
        return redirect(url_for('showLogin'))

    # Display the form for GET requests
    if request.method == 'GET':
        item = db.query(Item).filter_by(name=item_name)
        # Make sure the item exists
        if item.count() == 0:
            return '404 not found'
        cats = db.query(Category)
        return render_template('item_edit.html', numcats=cats.count(), cats=cats.all(),
                               item=item.one(), logged_in=is_logged_in())

    # Handle the database for POST requests
    if request.method == 'POST':
        new_item_name = request.form['item_name']
        new_item_desc = request.form['item_desc']
        item_cat_name = request.form['item_cat_name']
        cats = db.query(Category).filter_by(name=item_cat_name)
        # Make sure the item's category is valid
        if cats.count() > 0:
            items = db.query(Item).filter_by(category_id=cats.one().id, name=item_name)
            # Make sure the item exists
            if items.count() > 0:
                item = items.one()
                # Make sure the correct user is issuing this request
                if item.user_id == get_user_id(session['email']):
                    # Edit the item
                    item.name = new_item_name
                    item.desc = new_item_desc
                    # TODO: get this bug fixed
                    item.category = cats.one()
                    db.commit()
        # Redirect to landing
        return redirect(url_for('landing'))


# Route to delete items
@app.route('/catalog/<item_name>/delete/', methods = ['GET', 'POST'])
def itemDelete(item_name):
    # Force the user to log in
    if not is_logged_in():
        return redirect(url_for('showLogin'))

    # Show the delete form for GET requests
    if request.method == 'GET':
        item = db.query(Item).filter_by(name=item_name)
        # Make sure the item exists
        if item.count() == 0:
            return '404 not found'
        return render_template('item_delete.html', item=item.one(), logged_in=is_logged_in())

    # Handle the database for post requests
    if request.method == 'POST':
        item = db.query(Item).filter_by(name=item_name)
        # Make sure the item exists
        if item.count() > 0:
            # Make sure the correct user is issuing this request
            if item.one().user_id == get_user_id(session['email']):
                db.delete(item.one())
                db.commit()
        # Redirect to the landing
        return redirect(url_for('landing'))


# Start the server
if __name__ == '__main__':
    import uuid
    app.secret_key = str(uuid.uuid4())
    app.debug = True
    app.run(host='0.0.0.0', port=8080)
