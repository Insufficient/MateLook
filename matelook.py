#!/usr/local/bin/python3.5 -u

from flask import Flask, session, escape, request, url_for, redirect
import re, sys, os, glob
app = Flask( __name__ )

users_dir = "dataset-medium"

@app.route( '/', methods=['GET', 'POST'] )
def index( ):
    if request.method == 'POST':
        session['username'] = request.form['username']
        return redirect(url_for('index'))

    if 'username' in session:
        return """ \
        <h2>Logged in as %s</h2>
        <a href="/logout"><button>Logout</button></a>
        """ % escape( session[ 'username'] )
    else:
        return '''
            <form action="" method="post">
                <label>Username</label>
                <p><input type=text name=username>
                <p><input type=submit value=Login>
            </form>
        '''

@app.route( '/users' )
@app.route( '/users/' )
@app.route( '/user/<user_name>' )
def viewUser( user_name=None ):

    if( user_name == None ):     # Show a random user.
        users = sorted( glob.glob( os.path.join( users_dir, "*" ) ) )
        u_ToShow = users[ 0 ];
        print( "Showing " + str( u_ToShow ) )
    else:
        username = re.findall( r'z[0-9]{7}', user_name )    # Sanitize input
        if not username:                                    # No user with the username found
            return "<p>Invalid username %s</p>" % escape( user_name )

        u_ToShow = os.path.join( users_dir, username[ 0 ] )

    u_FileName = os.path.join( u_ToShow, "user.txt" )
    with open( u_FileName ) as f:
        u_Info = [ ]
        for line in f:
            line.rstrip( )
            lineInfo = line.split( "=", 1 )
            if len( lineInfo ) != 2: break;     # Skip this line if it doesnt have what we need
            u_Info.append( "{} => {}".format( lineInfo[ 0 ], lineInfo[ 1 ] ) )

    return """
<div class="matelook_user_details">
%s
</div>
""" % ( u_Info )


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
