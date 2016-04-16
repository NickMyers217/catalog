# This file contains the HTTP routes for the website

from flask import Flask

app = Flask(__name__)

# Route for the landing page
@app.route('/')
def landing():
    return 'Landing page'


if __name__ == '__main__':
    app.run(host = '0.0.0.0', port = 8080, debug = True)
