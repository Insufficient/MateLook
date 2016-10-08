#!/usr/local/bin/python3.5 -u

from flask import Flask, session, escape, request, url_for, redirect
app = Flask( __name__ )

@app.route( '/', methods=['GET', 'POST'] )
def index( ):
    if request.method == 'POST':
        session['username'] = request.form['username']
        return redirect(url_for('index'))

    if 'username' in session:
        return 'Logged in as %s' % escape( session[ 'username'] )
    else:
        return '''
            <form action="" method="post">
                <label>Username</label>
                <p><input type=text name=username>
                <p><input type=submit value=Login>
            </form>
        '''

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
