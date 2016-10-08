#!/usr/local/bin/python3.5 -u

from flask import Flask, session, escape, request, url_for, redirect, render_template
from collections import defaultdict
import re, sys, os, glob
app = Flask( __name__ )

users_dir = "static/dataset-medium"

@app.route( '/', methods=['GET', 'POST'] )
def index( ):
    if request.method == 'POST':
        session['username'] = request.form['username']
        return redirect(url_for('index'))

    if 'username' in session:
        return """ \
        <h2>Logged in as %s</h2>
        <a href="logout"><button>Logout</button></a>
        """ % escape( session[ 'username'] )
    else:
        return '''
            <form action="" method="post">
                <label>Username</label>
                <p><input type=text name=username>
                <p><input type=submit value=Login>
            </form>
        '''

@app.route( '/user/<user_name>' )
def viewUser( user_name=None ):

    if( user_name == None ):     # Show a random user.
        return "<p>Please enter a username</p>"

    username = re.findall( r'z[0-9]{7}', user_name )    # Sanitize input
    if not username:                                    # No user with the username found
        return "<p>Invalid username %s</p>" % escape( user_name )

    u_ToShow = os.path.join( users_dir, username[ 0 ] )
    u_FileName = os.path.join( u_ToShow, "user.txt" )

    if not os.path.isfile( u_FileName ):
        return "<p>User does not exist.%s</p>" % escape( user_name )

    with open( u_FileName ) as f:
        u_Info = defaultdict( )
        for line in f:
            line = line.rstrip( )   # Chomp
            lineInfo = line.split( "=", 1 ) # Split on '='
            if len( lineInfo ) != 2: break;     # Skip this line if it doesnt have what we need

            if lineInfo[ 0 ] == "mates":
                lineInfo[ 1 ] = re.sub( r'(\[|\])', '', lineInfo[ 1 ] )
                # mates = re.findall( r'\s*([^\s]*),*\s*', lineInfo[ 1 ] )
                mates = lineInfo[ 1 ].split( ', ' )
                mates.pop( )    # Remove last useless element
                # print( mates )
                # print( type( mates ) )
                # for person in iter( mates ):
                    # print( "Person: " + person )

                u_Info[ lineInfo[ 0 ] ] = mates
            else:
                u_Info[ lineInfo[ 0 ] ] = lineInfo[ 1 ]

    #print( u_Info );
    imgLoc = os.path.join( u_ToShow, "profile.jpg" )
    if not os.path.isfile( imgLoc ):
        imgLoc = None
        #imgLoc = url_for( 'static', filename='imgLoc' )
    # else:
        #imgLoc = url_for( 'static', filename='imgLoc' )

    return render_template( "user.html", username=username[ 0 ], uInfo=u_Info, img=imgLoc )
#     return """
# <div class="matelook_user_details">
# %s
# </div>
# """ % ( u_Info )


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['username'] = request.form['username']
        return redirect(url_for('index'))
    else:
        return '<h1>Sorry bicboi.</h1>'

@app.route( '/logout' )
def logout( ):
    session.pop( 'username', None )
    return redirect( url_for( 'index' ) )

if __name__ == "__main__":
    app.run( debug=True, port=5000, host="0.0.0.0" )

app.secret_key = 'yoloswag420'
