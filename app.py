# This file contains the HTTP routes for the website

import random, string, json, httplib2, requests

from flask import Flask, render_template, request, redirect, url_for, session, \
    make_response, flash, jsonify
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


# Utility for querying users in the database
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
    if is_logged_in():
        user_img = session['picture']
        return render_template('catalog.html', cats=cats, items=items, logged_in=True,
                               user_img=user_img)
    else:
        return render_template('catalog.html', cats=cats, items=items, logged_in=False)


# JSON mapping of the catalog
@app.route('/catalog.json')
def catalogJSON():
    def itemToDict(item):
        return item.serialize

    def catToDict(cat):
        tempCat = cat.serialize
        items = db.query(Item).filter_by(category_id = tempCat['id']).all()
        tempCat['items'] = map(itemToDict, items)
        return tempCat

    cats = db.query(Category).all()
    return jsonify(categories=map(catToDict, cats))


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
    session['provider'] = 'google'
    session['user_id'] = create_user()

    flash('Logged in!')
    print 'Success!'
    return 'Success!'


# Route to disconnect a Google user
@app.route('/googleLogout')
def googleLogout():
    # Check to make sure the user is actually logged in
    credentials = session.get('credentials')
    if credentials is None:
        return redirect(url_for('showLogin'))

    # Use the google api to revoke the token
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % credentials
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]

    if result['status'] != '200':
        return 'You were logged out!'


# Route to log in a Facebook user
@app.route('/fbLogin', methods=['POST'])
def fbLogin():
    print 'Beginnig facebook oauth login!'

    # Verify the anti xss forgery token from the client matches
    if request.args.get('state') != session['state']:
        err = 'This might be an xss attack, aborted!'
        print err
        return quick_json_res(err, 401)

    # Since this is not an xss attack, we can proceed
    # and exchange the one time authorization code from facebook
    access_token = request.data
    print "Code exchanged!"
    app_id = json.loads(open('fb_client_secrets.json', 'r').read())['web']['app_id']
    app_secret = json.loads(open('fb_client_secrets.json', 'r').read())['web']['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=%s&client_secret=%s&fb_exchange_token=%s' % (app_id, app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    # Use token to get user info from API
    userinfo_url = "https://graph.facebook.com/v2.4/me"
    # strip expire tag from access token
    token = result.split("&")[0]
    url = 'https://graph.facebook.com/v2.4/me?%s&fields=name,id,email' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    print "url sent for API access:%s"% url
    print "API JSON result: %s" % result
    data = json.loads(result)
    print "Storing info"
    session['provider'] = 'facebook'
    session['username'] = data["name"]
    session['email'] = data["email"]
    session['facebook_id'] = data["id"]
    
    # The token must be stored in the login_session in order to properly logout
    stored_token = token.split("=")[1]
    session['credentials'] = stored_token

    # Get user picture
    url = 'https://graph.facebook.com/v2.4/me/picture?%s&redirect=0&height=200&width=200' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result) 
    session['picture'] = data["data"]["url"]

    # see if user exists
    user_id = get_user_id(session['email'])
    if not user_id:
        user_id = create_user()
    session['user_id'] = user_id 
    
    flash('Logged in!')
    print 'Success!'
    return 'Success!'


# Route to log a facebook user out
@app.route('/fbLogout')
def fbLogout():
    facebook_id = session['facebook_id']
    # The access token must me included to successfully logout
    access_token = session['credentials']
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s' % (facebook_id,access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    return 'you have been logged out'


# Route for logging in
@app.route('/login')
def showLogin():
    # Generate and store an anti forgery token to prevent xss attacks
    # it can be passed to the view, and then to any ajax login requests
    # if it doesn't match the same code still stored, its not the same user
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    session['state'] = state
    if is_logged_in():
        return render_template('login.html', state=session['state'], logged_in=True,
                               user_img=session['picture'])
    else:
        return render_template('login.html', state=session['state'], logged_in=False)


# Route to revoke a current user's token and reset their session
@app.route('/logout')
def logout():
    if 'provider' in session:
        if session['provider'] == 'google':
            googleLogout()
            del session['gplus_id']
            del session['credentials']
        if session['provider'] == 'facebook':
            fbLogout()
            del session['facebook_id']
        del session['username']
        del session['email']
        del session['picture']
        del session['user_id']
        del session['provider']
        flash('You have successfully been logged out.')
        return redirect(url_for('landing'))
    else:
        flash('You were not logged in.')
        return redirect(url_for('langing'))


# Route to show a categorie's items
@app.route('/catalog/<cat_name>/')
@app.route('/catalog/<cat_name>/items/')
def items(cat_name):
    cats = db.query(Category).all()
    category = db.query(Category).filter_by(name=cat_name)
    # Make sure the category exists
    if category.count() == 0:
        return pageNotFound('404')
    items = db.query(Item).filter_by(category_id = category.one().id)
    if is_logged_in():
        return render_template('items.html', cats=cats, cat=cat_name, items=items.all(),
                               cnt=items.count(), logged_in=True, user_img=session['picture'])
    else:
        return render_template('items.html', cats=cats, cat=cat_name, items=items.all(),
                               cnt=items.count(), logged_in=False)


# Route to show a single item within a category
@app.route('/catalog/<cat_name>/<item_name>/')
def itemDesc(cat_name, item_name):
    category = db.query(Category).filter_by(name=cat_name)
    # Make sure the category exists
    if category.count() == 0:
        return pageNotFound('404')
    item = db.query(Item).filter_by(category_id=category.one().id, name=item_name)
    # Make sure th item exists
    if item.count() == 0:
        return pageNotFound('404')
    # See if the user created this item, if so they can edit it
    can_edit = is_logged_in() and get_user_id(session['email']) == item.one().user_id
    if is_logged_in():
        return render_template('item.html', cat=cat_name, item=item.one(), can_edit=can_edit,
                               logged_in=True, user_img=session['picture'])
    else:
        return render_template('item.html', cat=cat_name, item=item.one(), can_edit=can_edit,
                               logged_in=False)


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
                               logged_in=True, user_img=session['picture'])
    
    # Handle the database for POST requests
    if request.method == 'POST':
        item_name = request.form['item_name']
        item_desc = request.form['item_desc']
        item_cat_name = request.form['item_cat_name']
        # Make sure the item's category is valid
        cats = db.query(Category).filter_by(name=item_cat_name)
        if cats.count() > 0:
            # Make sure the item doesn't already exist
            if db.query(Item).filter_by(name=item_name).count() > 0:
                flash('This item already exists! :(')
                return redirect(url_for('itemNew'))
            # Add the item to the database
            user_id = get_user_id(session['email'])
            item = Item(name=item_name, desc=item_desc, category=cats.one(), user_id=user_id)
            db.add(item)
            db.commit()
        # Redirect to landing
        flash('%s succesfully created!' % item_name)
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
            return pageNotFound('404')
        # Make sure the user can edit this item
        if item.one().user_id != get_user_id(session['email']):
            return redirect(url_for('landing'))
        cats = db.query(Category)
        return render_template('item_edit.html', numcats=cats.count(), cats=cats.all(),
                               item=item.one(), logged_in=True, user_img=session['picture'])

    # Handle the database for POST requests
    if request.method == 'POST':
        new_item_name = request.form['item_name']
        new_item_desc = request.form['item_desc']
        old_item_cat_name = request.form['old_item_cat_name']
        new_item_cat_name = request.form['item_cat_name']

        # Make sure the item's old category exists
        old_cat = db.query(Category).filter_by(name=old_item_cat_name)
        if old_cat.count() > 0:
            # Make sure the item exists currently
            items = db.query(Item).filter_by(name=item_name, category_id=old_cat.one().id)
            if items.count() > 0:
                # Make sure the item's proposed category is valid
                cats = db.query(Category).filter_by(name=new_item_cat_name)
                if cats.count() > 0:
                    item = items.one()
                    # It should be a new item
                    duplicate = db.query(Item).filter_by(name=new_item_name)
                    if duplicate.count() != 0:
                        flash('This item already exists! :(')
                        return redirect(url_for('itemEdit', item_name=item_name))
                                        
                    # Make sure the correct user is issuing this request
                    if item.user_id == get_user_id(session['email']):
                        # Edit the item
                        item.name = new_item_name
                        item.desc = new_item_desc
                        item.category = cats.one()
                        db.commit()
        # Redirect to landing
        flash('%s succesfully edited!' % new_item_name)
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
            return pageNotFound('404')
        # Make sure the user can edit this item
        if item.one().user_id != get_user_id(session['email']):
            return redirect(url_for('landing'))
        return render_template('item_delete.html', item=item.one(), logged_in=True,
                               user_img=session['picture'])

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
        flash('%s succesfully deleted!' % item_name)
        return redirect(url_for('landing'))


# A custom 404 route
@app.errorhandler(404)
def pageNotFound(e):
    print e
    if is_logged_in():
        return render_template('404.html', logged_in=True, user_img=session['picture']), 404
    else:
        return render_template('404.html', logged_in=False), 404


# Start the server
if __name__ == '__main__':
    import uuid
    app.secret_key = str(uuid.uuid4())
    app.debug = True
    app.run(host='0.0.0.0', port=8080)
