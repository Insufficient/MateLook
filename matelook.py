#!/usr/local/bin/python3.5 -u

from flask import Flask
app = Flask( __name__ )

@app.route( '/' )
def hello_world( ):
    return '<h1>Hello there bro.</h1>'

@app.route( '/user/<username>' )
def show_user( username ):
    return '<h2>Username: %s does not exist.' % username

@app.route( '/post/<int:post_id>' )
def show_post( post_id ):
    return 'Post: %d' % post_id

if __name__ == "__main__":
    app.run( debug=True, port=5000, host="0.0.0.0" )
