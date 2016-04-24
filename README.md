# Cataloginator
This is a simple CRUD web application built with the Python Flask framework.
It is backed by a SQLite database.

## Installation
To get the app up and running locally, use the following commands from your shell (you'll need git, python 2.7, sql, flask, sqlalchemy, and a few other python libraries installed).
``` shell
git clone https://github.com/nickmyers217/catalog
cd catalog
python database_setup.py
```
That will create the database on your system and populate it with some intial records.

#### Setting Up Oauth
In order for oauth to work properly for the app, the server and client need to be aware of your google and facebook information. You'll have to go create an app in the developer portal of each before following the instructions below.

#### The server
The next step is to create 2 files in the root directory to hold the client secrets for both google and facebook.
``` shell
touch client_secrets.json
touch fb_client_secrets.json
```
Client_secrets.json can be downloaded after registering your app on the google developer console.
Fb_client_secrets.json will have to be created manually and follow the below format.
``` code
{
    "web": {
	"app_id": "YOUR_FB_APP_ID",
	"app_secret": "YOUR_TB_APP_SECRET"
    }
}
```

#### The Client
The final thing to account for is to make sure the client is aware of your app id's as well.
``` shell
cd static/js
```
In this folder you will find the relevant javascript. First open google_oauth.js and change the client ID in the location shown below.
``` code
    // Initialize the auth2 object
    gapi.load('auth2', function () {
	    gapi.auth2.init({
	        client_id: 'YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com'
	    }).then(signOut)
    })
```
Now open facebook_oauth.js and make a similar modification in the location shown below with your facebook app id.
``` code
// Initialize the Facebook SDK
window.fbAsyncInit = function() {
    FB.init({
      appId      : 'YOUR_FB_APP_ID',
      xfbml      : true,
      version    : 'v2.5'
    });
};
```

### Putting it Together
Now you have taken all the steps neccessary to get oauth working and its time to start the app.
``` shell
python app.py
```
If you recieve any errors of missing libraries, go ahead and use sudo pip install. Once the application is running, you can find it on localhost:8080

