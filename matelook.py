#!/usr/bin/env python3.5 -u
#!/usr/local/bin/python3.5 -u

from flask import Flask, session, escape, request, url_for, redirect,           \
                    render_template, Markup, flash, send_file
from collections import defaultdict
from werkzeug.utils import secure_filename
from lxml.html.clean import clean_html, Cleaner
import re, sys, os, glob, jinja2, io
import sqlite3 as sql
import datetime, logging, smtplib
from email.mime.text import MIMEText

ALLOWED_EXTENSIONS = set( ['png', 'jpg', 'jpeg' ] )
users_dir = "static/dataset-large"
db = "sql.db"

app = Flask( __name__ )
app.secret_key = "AS:DKLASDKaz.c,zxAS>a,szxvc.zA,.asdzkx.AS" #os.urandom( 32 )
# app.config[ 'MAX_CONTENT_LENGTH' ] = 1 * 1024 * 1024        # 512 KB


"""
    Attribution to http://flask.pocoo.org/docs/0.11/patterns/fileuploads/
"""
def allowed_file( filename ):
    return '.' in filename and \
           filename.rsplit( '.', 1 )[ 1 ] in ALLOWED_EXTENSIONS

"""
    Users can update their privacy settings
"""
@app.route( '/privPref', methods=[ 'POST' ] )
def privPref( ):
    if request.method == 'POST':
        zID = request.form.get( 'zID' )
        priv1 = request.form.get( 'priv1' )
        priv2 = request.form.get( 'priv2' )
        priv3 = request.form.get( 'priv3' )
        priv4 = request.form.get( 'priv4' )

        con = sql.connect( db )
        cur = con.cursor( )
        if priv1:
            cur.execute( "UPDATE User SET priv1='1' WHERE zID=?", [ zID ] )
        else:
            cur.execute( "UPDATE User SET priv1='0' WHERE zID=?", [ zID ] )
        if priv2:
            cur.execute( "UPDATE User SET priv2='1' WHERE zID=?", [ zID ] )
        else:
            cur.execute( "UPDATE User SET priv2='0' WHERE zID=?", [ zID ] )
        if priv3:
            cur.execute( "UPDATE User SET priv3='1' WHERE zID=?", [ zID ] )
        else:
            cur.execute( "UPDATE User SET priv3='0' WHERE zID=?", [ zID ] )
        if priv4:
            cur.execute( "UPDATE User SET priv4='1' WHERE zID=?", [ zID ] )
        else:
            cur.execute( "UPDATE User SET priv4='0' WHERE zID=?", [ zID ] )
        con.commit( )
        con.close( )

    return redirect( url_for( 'auth' ) )


"""
    Users can update their email preferences
"""
@app.route( '/emailPref', methods=[ 'POST' ] )
def emailPref( ):
    if request.method == 'POST':
        logger = logging.getLogger( __name__ )
        logger.info( '\t[Request: %s]', request.form )
        zID = request.form.get( 'zID' )
        emailReq1 = request.form.get( 'emailReq1' )
        emailReq2 = request.form.get( 'emailReq2' )

        con = sql.connect( db )
        cur = con.cursor( )
        if emailReq1:
            cur.execute( "UPDATE User SET emailReq1='1' WHERE zID=?", [ zID ] )
        else:
            cur.execute( "UPDATE User SET emailReq1='0' WHERE zID=?", [ zID ] )
        if emailReq2:
            cur.execute( "UPDATE User SET emailReq2='1' WHERE zID=?", [ zID ] )
        else:
            cur.execute( "UPDATE User SET emailReq2='0' WHERE zID=?", [ zID ] )
        con.commit( )
        con.close( )
        # logger.info( "\temailReq1: %d, emailReq2: %d", eReq1, eReq2 )
        return redirect( url_for( 'auth' ) )

    else:
        return redirect( url_for( 'auth' ) )


"""
    Users can upload a profile or background picture.
"""
@app.route( '/uploadPicture', methods=['GET', 'POST'] )
def uploadPic( ):
    if request.method == 'POST':
        zID = request.form[ 'zID' ]
        cType = request.form[ 'type' ]
        if request.files:
            file = request.files[ 'file' ]

        if 'action' in request.form and request.form[ 'action' ] == 'Delete Current Picture':
            user = getSess( )
            if user != None:
                userDir = os.path.join( users_dir, user )
                if not os.path.exists( userDir ):                                   # Create a user directory if it doesnt exist.
                    os.makedirs( userDir )

                if 'pBg' in cType:
                    filename = 'bg.jpg'
                elif 'pPic' in cType:
                    filename = 'profile.jpg'
                else:
                    return render_template( 'error0.html', message="Invalid type." )

                if not os.path.isfile( os.path.join( userDir, filename ) ):
                    return render_template( 'error0.html', message="You did not have a picture." )

                os.remove( os.path.join( userDir, filename ) )
                return redirect( url_for( 'auth' ) )

            return render_template( 'error0.html', message="You cannot delete your profile picture without being logged in." )

        if file and allowed_file(file.filename):
            if 'pBg' in cType:
                filename = secure_filename( 'bg.jpg' )
            elif 'pPic' in cType:
                filename = secure_filename( 'profile.jpg' )
            else:
                return render_template( 'error0.html', message="Invalid type." )

            userDir = os.path.join( users_dir, zID )
            if not os.path.exists( userDir ):                                   # Create a user directory if it doesnt exist.
                os.makedirs( userDir )

            file.save( os.path.join( userDir, filename ) )
            return redirect( url_for( 'auth' ) )

        return render_template( 'error0.html', message="Please specify an image with jpg/jpeg/png extension." )

    return render_template( 'error0.html', message="Please specify an image with jpg/jpeg/png extension." )

"""
    Serve static files
"""
@app.route( '/static/<path:path>' )
def send_static_file(path):
    return send_from_directory( 'static', path )

"""
    Allows users to verify their account!
"""
@app.route( '/verify/<zID>' )
def verify( zID ):
    if getSess( ) != None:
        return render_template( "error.html", message="You cannot verify an account while being logged in." )

    username = re.findall( r'z[0-9]{7}', zID[::-1] )    # Sanitize input
    if not username:                                    # No user with the username found
        return render_template( "error.html", message="Invalid username %s" % escape( zID[::-1] ) )

    con = sql.connect( db )
    cur = con.cursor( )
    cur.execute( "SELECT zID FROM User WHERE zID=? AND verified=?", ( username[ 0 ], False) )
    results = cur.fetchone( )
    if not results:
        con.close( )
        return render_template( "error.html", message="The user does not need to be verified" )
    else:
        cur.execute( "UPDATE User SET verified=? WHERE zID=?", ( True, username[ 0 ] ) )
        con.commit( )
        con.close( )
        session[ 'username' ] = username[ 0 ]
        return redirect( url_for( 'viewUsers', user_name=username[ 0 ] ) )

"""
    View Mate Suggestions
"""
@app.route( '/mate_suggestions' )
def mateSuggest( ):
    if not getSess( ):
        flash( "You need to be logged in to view suggestions" )
        return redirect( url_for( 'auth' ) )

    zID = getSess( )
    con = sql.connect( db )
    cur = con.cursor( )

    cur.execute( "SELECT courseID FROM Course WHERE zID=?", [ zID ] )
    results = cur.fetchall( )
    string = [', '.join(w) for w in results]
    string = '","'.join( string )
    sCourses = "(\"{}\")".format( string )
    logger = logging.getLogger( __name__ )
    cur.execute( "SELECT mateID FROM Mate WHERE zID=?", [ zID ] )
    results = cur.fetchall( )
    string = [', '.join(w) for w in results]
    string = '","'.join( string )
    sMates = "(\"{}\")".format( string )
    # logger.info( "\t[zID: %s] Mates: %s\n", zID, sMates )

    mateSugg = defaultdict( lambda: 0 )
    reasons = defaultdict( lambda: '' )
    # Search for mates of mates
    cur.execute( "SELECT mateID FROM Mate WHERE zID IN {}".format( sMates ) )
    results = cur.fetchall( )
    for row in results:
        mateSugg[ row[ 0 ] ] += 2
        reasons[ row[ 0 ] ] += "Mate of Mate, "

    # Search for users with similar courses
    if sCourses:
        cur.execute( "SELECT zID, COUNT(zID) FROM Course WHERE courseID IN {} GROUP BY zID".format( sCourses ) )
        results = cur.fetchall( )
        for row in results:
            mateSugg[ row[ 0 ] ] = row[ 1 ] # factor 2?
            reasons[ row[ 0 ] ] += "Similar courses ({}), ".format( row[ 1 ] )

    # Search for users living in the same suburb
    userSub = getInfo( zID, "home_suburb" )
    if userSub:
        cur.execute( "SELECT zID FROM User WHERE home_suburb=?", [ userSub ] )
        results = cur.fetchall( )
        for row in results:
            mateSugg[ row[ 0 ] ] += 4   # factor 4?
            reasons[ row[ 0 ] ] += "Same suburb, "

    # Search for users in the same program.
    userProg = getInfo( zID, "program" )
    if userProg:
        cur.execute( "SELECT zID FROM User WHERE program=?", [ userProg ] )
        results = cur.fetchall( )
        for row in results:
            mateSugg[ row[ 0 ] ] += 4   # factor 3
            reasons[ row[ 0 ] ] += "Same program, "

    if zID in mateSugg:
        del mateSugg[ zID ]   # Remove themselves from suggestions.
    # Debug print suggestions
    for user in sorted( mateSugg, key=mateSugg.get, reverse=True ):
        # Remove them from suggestions if they are already friends
        # Remove them if they have scores of lesser than 0.5 of the suggestions
        if( isMate( zID, user ) or mateSugg[ user ] < 3 ):
            del mateSugg[ user ]    # Remove them from suggestions if they are already friends
            continue
        logger.info( "\t[Mate Suggest] %s[%d] - %s", user, mateSugg[ user ], reasons[ user ] )

    con.row_factory = sql.Row
    cur = con.cursor( )
    n_Info = tuple( )
    if zID:
        cur.execute( "SELECT * FROM Notes WHERE zID=? ORDER BY time DESC LIMIT 5", [ zID ] )
        result = cur.fetchall( )
        n_Info = result

    con.close( )
    return render_template( "suggest.html", users=sorted( mateSugg, key=mateSugg.get, reverse=True ), reasons=reasons, nInfo=n_Info )

"""
    View a user's profile page.
"""
@app.route( '/users/<user_name>' )
def viewUsers( user_name=None ):
    if( user_name == None ):     # Show a random user.
        return render_template( "error.html", message="Please enter a username" )

    username = re.findall( r'z[0-9]{7}', user_name )    # Sanitize input
    if not username:                                    # No user with the username found
        return render_template( "error.html", message="Invalid username %s" % escape( user_name ) )

    u_Info = tuple( )
    m_Info = tuple( )
    n_Info = tuple( )
    if username[ 0 ] == getInfo( username[ 0 ], 'zID' ): # User exists
        con = sql.connect( db )
        con.row_factory = sql.Row
        cur = con.cursor( )

        cur.execute( "SELECT * FROM User WHERE zID=?", [ username[ 0 ] ] )
        result = cur.fetchone( )
        u_Info = result
        tmpUInfo = dictFromRow( u_Info )
        if tmpUInfo[ 'verified' ] == 0:
            flash( "The user profile you are trying to visit has not yet verified their email address." )
            return redirect( url_for( 'auth' ) )

        cur.execute( "SELECT mateID FROM Mate WHERE zID=?", [ username[ 0 ] ] )
        result = cur.fetchall( )
        m_Info = result
        sessName = getSess( )
        if sessName:
            cur.execute( "SELECT * FROM Notes WHERE zID=? ORDER BY time DESC LIMIT 5", [ sessName ] )
            result = cur.fetchall( )
            n_Info = result

        con.close( )
    else:
        return render_template( "error.html", message="User %s does not exist." % escape( user_name ) )
    return render_template( "user.html", username=username[ 0 ], uInfo=u_Info, mInfo=m_Info, nInfo=n_Info )

"""
    Edit a user's information
"""
@app.route( '/edit', methods=[ 'POST' ] )
def editInfo( ):
    if request.method != 'POST':
        return redirect( url_for( 'auth' ) )

    zID = request.form[ 'zID' ]
    full_name = request.form[ 'full_name' ]
    email = request.form[ 'email' ]
    password = request.form[ 'password' ]
    birthday = request.form[ 'birthday' ]
    home_suburb = request.form[ 'home_suburb' ]
    program = request.form[ 'program' ]
    blurb = request.form[ 'blurb' ]
    newPass = request.form.get( 'password2' )

    if not zID or not full_name or not email or not password:
        return render_template( 'error0.html', message="zID, full name, email and password are all required." )

    if getSess( ) != zID:
        return render_template( 'error0.html', message="You cannot edit another users' information." )


    con = sql.connect( db )
    cur = con.cursor( )
    cur.execute( "SELECT zID FROM User WHERE zID=? AND password=?", ( zID, password ) )
    results = cur.fetchone( )
    if not results:
        flash( "You have entered the incorrect password." )
        return redirect( url_for( 'viewUsers', user_name=zID ) )

    cur.execute( "UPDATE User SET full_name=?, email=?, birthday=?,             \
                    home_suburb=?, program=?, blurb=? WHERE zID=?",             \
                    ( full_name, email, birthday, home_suburb, program,         \
                    blurb, zID ) )

    if newPass != None and len( newPass ) > 2:
        cur.execute( "UPDATE User SET password=? WHERE zID=?", ( newPass, zID ) )
    con.commit( )
    return redirect( url_for( 'viewUsers', user_name=zID ) )

"""
    Users can deactivate their account.
"""
@app.route( '/deactivate_account', methods=[ 'GET', 'POST' ] )
def deact_acc( ):
    if request.method == 'POST':
        formPass = request.form[ 'password' ]
        sess = getSess( )

        if not sess:
            return render_template( "error0.html", message="You cannot deactivate or reactivate your account when you are not logged in." )

        con = sql.connect( db )
        cur = con.cursor( )
        cur.execute( "SELECT zID FROM User WHERE zID=? AND password=?", ( sess, formPass ) )
        results = cur.fetchone( )
        if not results:
            flash( "You have entered an incorrect password." )
            return render_template( "disableAcc.html" )

        isPrivate = getInfo( sess, "private" )
        isPrivate = int( not isPrivate )    # Invert private status
        cur.execute( "UPDATE User SET private=? WHERE zID=?", ( isPrivate, sess ) )
        con.commit( )
        con.close( )

        return redirect( url_for( 'auth' ) )

    else:
        return render_template( 'disableAcc.html' )
"""
    Users can completely delete their account.
"""
@app.route( '/delete_account', methods=[ 'GET', 'POST'] )
def delete_acc( ):
    if request.method == 'POST':
        formzID = request.form[ 'zID' ]
        formPass = request.form[ 'password' ]
        sess = getSess( )

        if formzID != sess:
            return render_template( "error.html", message="You cannot delete an account you do not own." )

        con = sql.connect( db )
        cur = con.cursor( )
        cur.execute( "SELECT zID FROM User WHERE zID=? AND password=?", ( sess, formPass ) )
        results = cur.fetchone( )
        if not results:
            flash( "You have entered an incorrect password." )
            return render_template( "deleteAcc.html" )

        cur.execute( "DELETE FROM Reply WHERE zID=?", [ sess ] )
        cur.execute( "DELETE FROM Comment WHERE zID=?", [ sess ] )
        cur.execute( "DELETE FROM Post WHERE zID=?", [ sess ] )
        cur.execute( "DELETE FROM Course WHERE zID=?", [ sess ] )
        cur.execute( "DELETE FROM Mate WHERE zID=?", [ sess ] )
        cur.execute( "DELETE FROM User WHERE zID=?", [ sess ] )
        con.commit( )
        con.close( )

        session.pop( 'username', None )
        flash( "You have successfully deleted your account." )
        return redirect( url_for( 'auth' ) )

    else:
        return render_template( 'deleteAcc.html' )


"""
    Users can delete their comments, posts and replies.
"""
@app.route( '/delete', methods=[ 'POST' ] )
def delete( ):
    cParent = request.form[ 'parent' ]
    cType = request.form[ 'type' ]
    zID = request.form[ 'zID' ]

    if 'Post' in cType:
        colName = 'pID'
        # Check if session username is the parent username.
    elif 'Comment' in cType:
        colName = 'cID'
    elif 'Reply' in cType:
        colName = 'rID'
    else:
        return "You cannot access that column."

    if zID != getSess( ):
        return "You cannot delete this comment/post/reply."

    con = sql.connect( db )
    cur = con.cursor( )
    cur.execute( "SELECT zID FROM {} WHERE {} = ?".format( cType, colName ), [ cParent ] )
    results = cur.fetchone( )
    if not results:
        return "The comment/post/reply does not exist."

    try:
        if 'Post' in cType:
            cur.execute( "DELETE FROM Comment WHERE pID = ?", [ cParent ] )
            cur.execute( "DELETE FROM Reply WHERE pID = ?", [ cParent ] )
        if 'Comment' in cType:
            cur.execute( "DELETE FROM Reply WHERE cID = ?", [ cParent ] )

        cur.execute( "DELETE FROM {} WHERE {} = ?".format( cType, colName ), [ cParent ] )
    except sql.Error as e:
        print( "An error occurred!", e.args[ 0 ] )

    con.commit( )
    con.close( )
    return "You have deleted the comment."

"""
    Create posts/comments/replies
"""
@app.route( '/create', methods=[ 'POST' ] )
def create( ):
    cType = request.form[ 'type' ]              # Post, Comment or Reply
    cParent = request.form[ 'parent' ]
    cMessage = request.form[ 'message' ]
    zID = request.form[ 'zID' ]                 # Person making the post

    if not cMessage or not cParent or len( cMessage ) == 0:
        flash( "Please enter a message." )
        return render_template( "user.html" )

    if 'Post' in cType:
        colName = 'zID'
        cType = 'User'
        # Check if session username is the parent username.
    elif 'Comment' in cType:
        colName = 'pID'
        cType = 'Post'
    elif 'Reply' in cType:
        colName = 'cID'
        cType = 'Comment'
    else:
        flash( "You cannot access that column.")
        return render_template( "user.html" )

    con = sql.connect( db )
    cur = con.cursor( )
    cur.execute( "SELECT zID FROM {} WHERE {} = ?".format( cType, colName ), [ cParent ] )
    con.commit( )
    result = cur.fetchone( )

    if not result:
        flash( "You cannot make a post/comment/reply to that parent." )
        return render_template( "user.html" )

    cDate = datetime.datetime.now( )
    cMessage = cMessage.replace( '\n', '\\n' )
    matches = re.findall( r'@(z[0-9]{7})', cMessage )
    for match in matches:
        notify( match, zID, 4, url_for( 'viewUsers', user_name=zID, _external=True ) )
    # TODO: Individual POSTS

    # We need to preserve newlines and etc somehow.

    if colName == 'zID':                            # New post
        cur.execute( "INSERT INTO Post VALUES (?,?,?,?,?,?)", (   \
            None, cParent, cMessage, cDate, None, None ) )
    elif colName == 'pID':
        cur.execute( "INSERT INTO Comment VALUES (?,?,?,?,?)", (   \
            None, cParent, zID, cMessage, cDate ) )
    elif colName == 'cID':
        cur = con.cursor( )
        cur.execute( "SELECT cID FROM Comment WHERE pID = ?", [ cParent ] )
        result = cur.fetchone( )
        if not result:
            flash( "You cannot make a post/comment/reply to that parent." )
            return render_template( "user.html" )
        else:
            cur.execute( "INSERT INTO Reply VALUES (?,?,?,?,?,?)", (   \
                None, result[ 0 ], cParent, zID, cMessage, cDate ) )

    con.commit( )
    con.close( )
    return redirect( url_for( 'viewUsers', user_name=cParent ) )



"""
    Search AJAX page
"""
@app.route('/search', methods=['POST'] )
def search( ):
    searchQuery = request.form[ 'search' ]
    if searchQuery != None and len( searchQuery ) > 1:
        u_Info = defaultdict( lambda: None )
        p_Info = defaultdict( lambda: None )
        c_Info = defaultdict( lambda: None )
        r_Info = defaultdict( lambda: None )
        # print( "Search Query: " + searchQuery )
        con = sql.connect( db )
        con.row_factory = sql.Row
        cur = con.cursor( )
        cur.execute( "SELECT * FROM User WHERE full_name LIKE ?", [ '%'+searchQuery+'%' ] )
        result = cur.fetchall( )
        u_Info = result
        cur = con.cursor( )
        cur.execute( "SELECT * FROM Post WHERE message LIKE ?", [ '%'+searchQuery+'%' ] )
        result = cur.fetchall( )
        p_Info = result
        cur = con.cursor( )
        cur.execute( "SELECT * FROM Comment WHERE message LIKE ?", [ '%'+searchQuery+'%' ] )
        result = cur.fetchall( )
        c_Info = result
        cur = con.cursor( )
        cur.execute( "SELECT * FROM Reply WHERE message LIKE ?", [ '%'+searchQuery+'%' ] )
        result = cur.fetchall( )
        r_Info = result
        cur = con.cursor( )
        con.close( )
        return render_template( "search.html", uInfo=u_Info, pInfo=p_Info, cInfo=c_Info, rInfo=r_Info )
    else:
        flash( "Please enter at least two characters to search." )
        return render_template( "search.html" )

"""
    Users can view individual posts (/<type>/<id>)
"""

"""
    Users can recover their passwords
"""
@app.route( '/begin_recover', methods=[ "POST" ] )
def begin_recover( ):
    zID = request.form[ 'zID' ]

    formUser = re.findall( r'z[0-9]{7}', zID )     # Store only zID
    if not formUser:
        return "You must enter a valid zID. E.g: z5555555"
    formzID = formUser[ 0 ]

    if getInfo( formzID, "zID" ) == None:
        return "The user does not exist."

    dDate = datetime.datetime.now( )
    secretFormat = dDate.strftime( "%m%I%B%M%S%p" )
    con = sql.connect( db )
    cur = con.cursor( )
    uEmail = getInfo( formzID, "email" )
    uPassw = getInfo( formzID, "password" )
    cur.execute( "INSERT INTO Recover VALUES (?,?,?)", ( secretFormat[::-1], \
                    uEmail, uPassw ) )
    con.commit( )
    # print( "Secret: " + secretFormat[::-1] )
    msg = """You have requested for a password recovery.<br>To complete this
    process, please go to the link below:<br>
    <a href="{}">Recover Password</a>
    """.format( url_for( 'recover', secret=secretFormat[::-1], _external=True ) )
    sendEmail( uEmail, "Password Recovery", msg )
    return "A recovery link has been sent to your email."

@app.route( '/recover/<secret>' )
def recover( secret ):
    con = sql.connect( db )
    cur = con.cursor( )
    reverse = secret
    cur.execute( "SELECT password, email FROM Recover WHERE sId=?", ( reverse, ) )
    results = cur.fetchone( )
    if not results:
        return render_template( "error.html", message="Invalid recover key." )

    msg = "You have successfully recovered your password - {}".format( results[ 0 ] )
    cur.execute( "DELETE FROM Recover WHERE sID=?", ( reverse, ) )
    con.commit( )
    con.close( )
    sendEmail( results[ 1 ], "Password Recovery", msg )
    return redirect( url_for( 'auth' ) )


"""
    Login page
"""
@app.route('/', methods=['GET', 'POST'])
def auth( ):
    loggedIn = getSess( )
    if loggedIn != None:                                # Redirect users to view page if they are logged in
        return redirect( url_for( 'viewUsers', user_name=loggedIn ) )
    if request.method == 'POST':
        formUser = request.form[ 'zID' ]                    # Store username from form
        formPass = request.form[ 'password' ]               # Store password from form
        formEmail = request.form[ 'email' ]                 # Store email from form
        formName = request.form[ 'name' ]

        formUser = re.findall( r'z[0-9]{7}', formUser )     # Store only zID
        formzID = formUser[ 0 ]
        if not formUser:
            flash( "Please enter your zID in the form: z5555555." )
            return render_template( "login.html" )
        if not formPass:
            flash( "Please enter a password." )
            return render_template( "login.html", user=formzID )

        if request.form[ 'action' ] == 'Sign Up':
            if not formEmail:
                flash( "Please enter a email!" )
                return render_template( "login.html", user=formzID, pw=formPass )

            con = sql.connect( db )
            cur = con.cursor( )
            cur.execute( "SELECT zID FROM User WHERE zID=?", [ formzID ] )
            con.commit( )
            result = cur.fetchone( )
            if not result:
                try:
                    cur.execute( "INSERT INTO User VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", ( \
                    formzID, formName, formEmail, formPass, None, None, None, None, 0, 0, 0, 0, 0, 0, 0, 0 ) )
                    con.commit( )
                    flash( "An email has been sent to %s. Please click on the link to verify your account." % formEmail )
                    msg = """ Hello {},<br>
                    Welcome to MateLook, please verify your account by clicking on the link below:<br>
                    <a href="{}">Verify Account</a>
                    """.format( formName,  url_for( 'verify', zID=formzID[ ::-1 ], _external=True ) )
                    sendEmail( formEmail, "Account Verification", msg )
                    return redirect( url_for( 'auth' ) )
                except sql.Error as e:
                    print( "An error occurred!", e.args[ 0 ] )
            else:
                flash( "The user " + formUser[ 0 ] + " already exists." )
                return render_template( "login.html" )

            flash( "Signing up!" )
            return render_template( "login.html" )
        else:
            con = sql.connect( db )
            cur = con.cursor( )
            # Pls change
            query = "SELECT password FROM User WHERE zID = \"{}\"".format( formUser[ 0 ] )
            cur.execute( query )
            con.commit( )
            tmpPass = cur.fetchone( )
            if not tmpPass:
                flash( "The user does not exist" )
                return render_template( "login.html" );
            else:
                if tmpPass[ 0 ] == formPass:
                    session[ 'username' ] = formUser[ 0 ]
                    return redirect( url_for( 'viewUsers', user_name=formUser[ 0 ] ) )
                else:
                    flash( "Incorrect password." )
                    return render_template( "login.html", user=formUser[ 0 ] )
        return render_template( "login.html", message="Dead" )
    else:
        return render_template( "login.html" )

"""
    Send mate requests

    TODO:: Make sure everything is working fine.
        - Add option to accept or reject by adding another parameter in the URL
    MateReq
    | zID | mID | accepted |
"""
@app.route( '/mate/<mID>/<int:option>',  )
def mate( mID, option ):
    zID = getSess( )
    if not zID:
        return render_template( "error.html", message="You cannot do this when you're not logged in." )

    mUser = re.findall( r'z[0-9]{7}', mID )     # Sanitize input

    if not mUser:                               # No user with the username found
        return render_template( "error.html", message="Invalid username %s" % escape( user_name ) )
    if isMate( zID, mUser[ 0 ] ) and option < 2:
        return render_template( "error.html", message="You are already mates with this user." )
    if mUser[ 0 ] == zID:
        return render_template( "error.html", message="You cannot attempt to mate yourself.")

    con = sql.connect( db )
    cur = con.cursor( )
    # Swap zID and mID to find previous entry perhaps?
    cur.execute( "SELECT zID FROM MateReq WHERE zID=? AND mID=?", ( mUser[ 0 ], zID ) )
    results = cur.fetchone( )
    if option == 1:                 # We want to send a mate request.
        if not results:             # User is sending a mate request
            cur.execute( "SELECT zID FROM MateReq WHERE zID=? AND mID=?", ( zID, mUser[ 0 ] ) )
            results = cur.fetchone( )
            if results:
                return "You have already sent that user a mate request."

            cur.execute( "INSERT INTO MateReq VALUES (?,?)", ( zID, mUser[ 0 ] ) )

            con.commit( )
            con.close( )
            msg = """<a href="{}">{}</a> has sent you a mate request.<br>
            If you wish to accept this request, visit the link below:<br>
            <a href="{}">Accept Request</a><br>
            Otherwise, click the link below to decline this request.<br>
            <a href="{}">Decline Request</a>
            """.format( url_for( 'viewUsers', user_name=zID, _external=True ),      \
                        getInfo( zID, "full_name" ),                                \
                        url_for( 'mate', mID=zID, option=1, _external=True ),       \
                        url_for( 'mate', mID=zID, option=0, _external=True ) )

            if getInfo( mUser[ 0 ], "emailReq1" ):
                sendEmail( getInfo( mUser[ 0 ], "email" ), "MateLook - Mate Request", msg )

            notify( mUser[ 0 ], zID, 0, url_for( 'viewUsers', user_name=zID ,_external=True ) )
            return "You have sent that user a mate request."
        else:                       # User is accepting another request.
            cur.execute( "DELETE FROM MateReq WHERE zID=? AND mID=?", ( mUser[ 0 ], zID ) )
            cur.execute( "INSERT INTO Mate VALUES (?,?)", ( zID, mUser[ 0 ] ) )
            cur.execute( "INSERT INTO Mate VALUES (?,?)", ( mUser[ 0 ], zID ) )
            con.commit( )
            con.close( )
            notify( mUser[ 0 ], zID, 1, url_for( 'viewUsers', user_name=zID ,_external=True ) )
            return "You have added that user as a mate."
    elif option == 0:               # We want to remove that mate request.
        if results:
            cur.execute( "DELETE FROM MateReq WHERE zID=? and mID=?", ( mUser[ 0 ], zID ) )
            con.commit( )
            con.close( )
            notify( mUser[ 0 ], zID, 2, url_for( 'viewUsers', user_name=zID ,_external=True ) )
            return "You have delinced that users mate request."
        else:
            return "You cannot decline a request that does not exist."
    else:                           # We want to remove mates.
        cur.execute( "SELECT zID FROM Mate WHERE ( zID=? AND mateID=? ) OR ( zID=? AND mateID=? )" \
                        , ( zID, mUser[ 0 ], mUser[ 0 ], zID ) )
        results = cur.fetchone( )
        if results:
            cur.execute( "DELETE FROM Mate WHERE ( zID=? AND mateID=? ) OR ( zID=? AND mateID=? )" \
                        , ( zID, mUser[ 0 ], mUser[ 0 ], zID ) )
            con.commit( )
            notify( mUser[ 0 ], zID, 3, url_for( 'viewUsers', user_name=zID ,_external=True ) )
            return "You have unmated that user."
        else:
            con.close( )
            return "You cannot unmate a user that is not your mate."

"""
    Users can view individual posts
"""
@app.route( '/view/<pID>' )
def viewIndivPost( pID ):
    p_Info = tuple( )

    con = sql.connect( db )
    con.row_factory = sql.Row
    cur = con.cursor( )
    cur.execute( "SELECT * FROM Post WHERE pID=?", [ pID ] )
    results = cur.fetchall( )
    p_Info = results
    print( p_Info )
    con.close( )
    return render_template( "singlePost.html", pInfo=p_Info )

"""
    Logout page
"""
@app.route( '/logout' )
def logout( ):
    session.pop( 'username', None )
    return redirect( url_for( 'auth' ) )

# sneaky
""" SELECT pID FROM Post WHERE Message LIKE '%z50%' UNION
    SELECT pID FROM Reply WHERE Message LIKE '%z50%' UNION
    SELECT pID FROM Comment WHERE Message LIKE '%50%'"""

"""
    Render posts (AJAX)
"""
@app.route( '/post', methods=[ 'POST' ] )
def viewPost( ):
    user_name = request.form[ 'zID' ]
    pageNum = request.form[ 'pageNum' ]

    if( user_name == None ):     # Show a random user.
        return render_template( "error.html", message="Please enter a username" )

    username = re.findall( r'z[0-9]{7}', user_name )    # Sanitize input
    if not username:                                    # No user with the username found
        return render_template( "error.html", message="Invalid username %s" % escape( user_name ) )

    p_Info = tuple( )
    if username[ 0 ] == getInfo( username[ 0 ], 'zID' ): # User exists
        con = sql.connect( db )
        con.row_factory = sql.Row
        cur = con.cursor( )

        cur.execute( "SELECT mateID FROM Mate WHERE zID = ?", [ username[ 0 ] ] )
        results = cur.fetchall( )
        string = [', '.join(w) for w in results]
        string = '","'.join( string )
        mates = "(\"{}\",\"{}\")".format( username[ 0 ], string )
        # Get their mates and store it into a string to be used in the SQL query.

        # Obtain postIDs of replies and comments where a user is mentioned.
        userQuery = "%" + username[ 0 ] + "%"
        cur.execute( "SELECT pID FROM Reply WHERE Message LIKE ? UNION SELECT pID FROM Comment WHERE Message LIKE ?", ( userQuery, userQuery ) )
        results = cur.fetchall( )
        string = [', '.join(w) for w in results]
        string = '","'.join( string )
        sPosts = "(\"{}\")".format( string )
        logger = logging.getLogger( __name__ )
        logger.info( "\t[zID: %s] Related pIDs: %s\n", username[ 0 ], sPosts )

        # cur.execute( "SELECT * FROM Post WHERE zID IN {} OR Message LIKE ? ORDER BY time DESC LIMIT {}, 5".format( mates, pageNum ), [ "%" + username[ 0 ] + "%" ] )
        cur.execute( "SELECT * FROM Post WHERE zID IN {} OR Message LIKE ? OR pID IN {} ORDER BY time DESC LIMIT {}, 5".format( mates, sPosts, pageNum ), [ "%" + username[ 0 ] + "%" ] )

        result = cur.fetchall( )
        p_Info = result

        con.close( )
    else:
        return render_template( "error.html", message="User %s does not exist." % escape( user_name ) )
    return render_template( "post.html", pInfo=p_Info )

"""
    Serve profile images statically
"""
@app.route( '/profile_picture/<zID>' )
def showProfPict( zID ):
    username = re.findall( r'z[0-9]{7}', zID )                      # Sanitize input
    if not username:                                                # No user with the username found
        return "<p>Invalid username %s</p>" % escape( zID )

    u_ToShow = os.path.join( users_dir, username[ 0 ] )
    imgLoc = os.path.join( u_ToShow, "profile.jpg" )
    if not os.path.isfile( imgLoc ):
        imgLoc = os.path.join( users_dir, "default.png" )
    return send_file( imgLoc, mimetype='image/jpg' )

"""
    Serve profile background statically
"""
@app.route( '/profile_bg/<zID>' )
def showProfBg( zID ):
    username = re.findall( r'z[0-9]{7}', zID )                      # Sanitize input
    if not username:                                                # No user with the username found
        return "<p>Invalid username %s</p>" % escape( zID )

    u_ToShow = os.path.join( users_dir, username[ 0 ] )
    imgLoc = os.path.join( u_ToShow, "bg.jpg" )
    if not os.path.isfile( imgLoc ):
        imgLoc = os.path.join( users_dir, "default_bg.png" )
    return send_file( imgLoc, mimetype='image/jpg' )

""" getSess( )
 => returns the username of the session if any.
"""
def getSess( ):
    if 'username' in session:
        return session[ 'username' ]
    else:
        return None


""" isMate( zID, tID )
    zID     - user
    tID     - zID of target user
 => return 0 if they are not mates, 1 if they are.
"""
def isMate( zID, tID ):
    con = sql.connect( db )
    cur = con.cursor( )
    cur.execute( "SELECT zID FROM Mate WHERE zID = ? AND mateID=?", ( zID, tID ) )
    resultOne = cur.fetchone( )
    cur.execute( "SELECT zID FROM Mate WHERE zID = ? AND mateID=?", ( tID, zID ) )
    resultTwo = cur.fetchone( )
    con.close( )
    if not resultOne and not resultTwo:
        return 0
    else:
        return 1

""" getInfo( zID, infoName )
    zID         - zID of user  to be searched
    infoName    - the columns to retrieve.
"""
def getInfo( zID, infoName="*" ):
    con = sql.connect( db )
    cur = con.cursor( )
    cur.execute( "SELECT {} FROM User WHERE zID = ?".format( infoName ), (zID, ) )
    con.commit( )
    result = cur.fetchone( )
    con.close( )
    if result:
        return result[ 0 ]
    else:
        return None

""" getNotes( zID )
    zID         - zID to be searched
    returns notifications found
"""
def getNotes( zID ):
    n_Info = tuple( )
    con = sql.connect( db )
    cur = con.cursor( )
    cur.execute( "SELECT * FROM Notes WHERE zID=? ORDER BY time", [ zID ] )
    result = cur.fetchall( )
    n_Info = result
    return n_Info

""" getPost( tID, type )
    tID     - ID of post/comment/reply
    zID     - zID of user that made this post.
    type    - 0 (post), 1 (comment), 2 (reply)
"""
def getPost( tID, type="Post" ):
    if type == "Post":
        colID = "zID"
    elif type == "Comment":
        colID = "pId"
    else:
        colID = "cID"
    con = sql.connect( db )
    con.row_factory = sql.Row
    cur = con.cursor( )
    cur.execute( "SELECT * FROM {} WHERE {} = ?".format( type, colID ), ( tID, ) )
    #print( "SELECT zID, message FROM {} WHERE {} = {}".format( type, colID, tID ) )
    con.commit( )
    result = cur.fetchall( )
    # print( result )
    con.close( )
    return result

""" sendEmail( receiver, subject, message )
    receiver    - email of recipient
    subject     - subject of email
    message     - contents of email
"""
def sendEmail( receiver, subject, message ):
    logger = logging.getLogger( __name__ )
    msg = MIMEText( message, 'html')
    sender = "MateLook <noreply@matelook.com>"
    msg[ 'Subject' ] = subject
    msg[ 'From' ] = sender
    msg[ 'To' ] = receiver

    try:
        logger.info( "\tEmail Sent.\n[Sender]: %s, [Recv]: %s, [Msg] %s", sender, receiver, msg.as_string( ) )
        smtpObj = smtplib.SMTP('smtp.cse.unsw.edu.au')
        smtpObj.sendmail(sender, receiver, msg.as_string( ) )
    except smtplib.SMTPException:
        logger.info( "\tUnable to send email.\n[Sender]: %s, [Recv]: %s, [Msg] %s", sender, receiver, msg.as_string( ) )

""" notify( zID, initiator, nType, URL )
    zID         - recv
    initiator   - sender
    type        - type of notification
        [0] => Friend Request Sent
        [1] => Friend Request Accepted
        [2] => Friend Request Declined
        [3] => Friend Removed
        [4] => Mentioned
    URL         - location to-go-to.
"""
def notify( zID, initiator, nType, URL ):
    if not getInfo( zID, "zID" ) or not getInfo( initiator, "zID" ):
        return
    # emailNotif1 = getInfo( zID, "emailReq1" )   # Check if this user wants to be emailed friend requests.
    emailNotif2 = getInfo( zID, "emailReq2" )   # Check if this user wants to be emailed for mentions

    if nType == 0:
        msg = "@{} sent you a mate request.".format( initiator )
    elif nType == 1:
        msg = "@{} has accepted your mate request.".format( initiator )
    elif nType == 2:
        msg = "@{} has declined your mate request.".format( initiator )
    elif nType == 3:
        msg = "@{} has removed you from their mates list.".format( initiator )
    elif nType == 4:
        msg = "@{} has mentioned you in a post/comment/reply.".format( initiator )

    if nType == 4 and emailNotif2 == 1:
        sendEmail( getInfo( zID, "email" ), "MateLook - Notification", "<br>" + msg )

    cDate = datetime.datetime.now( )
    con = sql.connect( db )
    cur = con.cursor( )
    cur.execute( "INSERT INTO Notes VALUES( ?, ?, ?, ?, ?, ? )", ( zID, initiator, msg, nType, cDate, URL ) )
    con.commit( )
    con.close( )

""" sanitise( zID )
    zID     - zID to be sanitised
"""
def sanitise( zID ):
    zRe = re.compile( r'z[0-9]{7}' )
    return zRe.match( zID )
"""
    doMention converts a message string into HTML Markup.
    (\n => <br>)
    (@z5117924 => <a href="/users/z5117924">Full Name</a>)
"""
def doMention( longString ):
    if not longString:
        return Markup( "None" )
    # longString = re.sub( r'\n', '<br/>', str( longString ), flags=re.DEBUG )
    longString = longString.replace( r'\n', '<br>' )
    longString = longString.replace( r'\\n', '<br>' )
    cleaner = Cleaner( page_structure=False )
    longString = cleaner.clean_html( str( longString ) )
    longString = re.sub( r'@(z[0-9]{7})', r'<a href="\1">@\1</a>', longString )
    matches = re.findall( r'>@(z[0-9]{7})<', longString )
    for match in matches:
        swapFrom = ">@{}<".format( match )
        swapInto = ">@{}<".format( getInfo( match, "full_name" ) )
        longString = re.sub( swapFrom, swapInto, longString )
    # Embed images!
    imgRe = re.compile( r'([^\>]*http(:?s)*[^\s]+\/[\w]+\.(?:jpg|png|gif|jpeg))' )
    longString = re.sub( imgRe, r'<img class="embed-img" src="\1">', longString )
    vidRe = re.compile( r'([^\>]*http(?:s)*[^\s\>\<]+(:?youtube\.com\/embed\/[^\s\>\<]+))' )
    longString = re.sub( vidRe, r'<iframe class="embed-vid" src="\1"></iframe>', longString )
    return Markup( longString )

"""
    Converts SQL row format into a dictionary
    Credits to bbengfort from StackOverflow.
"""
def dictFromRow( row ):
    return dict( zip( row.keys( ), row ) )

def main( ):

    # Make functions callable from Jinja.
    app.jinja_env.globals.update( getInfo=getInfo )
    app.jinja_env.globals.update( getSess=getSess )
    app.jinja_env.globals.update( dictFromRow=dictFromRow )
    app.jinja_env.globals.update( getPost=getPost )
    app.jinja_env.globals.update( getNotes=getNotes )
    app.jinja_env.globals.update( isMate=isMate )

    app.jinja_env.filters['doMention'] = doMention

    # logger = logging.getLogger( __name__ )
    # logging.basicConfig( filename='hello.log', level=logging.DEBUG)

    logger = logging.getLogger( __name__ )
    logging.basicConfig( filename='out.log', level=logging.INFO )
    logging.info( "Starting MateLook.py ...\n" )
    if os.path.isfile( db ): return
    # We don't need to recreate the database if it already exists.

    # print( "Creating Database..." )
    con = sql.connect( db )
    cur = con.cursor( )
    cur.execute( '''\
    CREATE TABLE IF NOT EXISTS "User"
        ("zID" TEXT PRIMARY KEY  NOT NULL  UNIQUE ,
        "full_name" TEXT,
        "email" TEXT,
        "password" TEXT,
        "birthday" TEXT,
        "home_suburb" TEXT,
        "program" TEXT )''' )
    cur.execute( ''' \
    CREATE TABLE "Post" ("pID" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL UNIQUE  DEFAULT 0,
    "zID" TEXT,
    "message" TEXT,
    "time" TEXT,
    "longitude" TEXT,
    "latitude" TEXT)''' )
    cur.execute( ''' \
    CREATE TABLE "Comment" ("cID" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL UNIQUE  DEFAULT 0,
    "pID" TEXT,
    "zID" TEXT,
    "message" TEXT,
    "time" TEXT)''' )
    cur.execute( ''' \
    CREATE TABLE "Reply" ("rID" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL UNIQUE  DEFAULT 0,
    "cID" TEXT,
    "pID" TEXT,
    "zID" TEXT,
    "message" TEXT,
    "time" TEXT)''' )
    cur.execute( '''CREATE TABLE "Mate" ("zID" TEXT NOT NULL , "mateID" TEXT)''' )
    cur.execute( '''CREATE TABLE "Course" ("zID" TEXT NOT NULL , "courseID" TEXT)''' )
    con.commit( );

    con.close( )
    parseDataset( )

def parseDataset( ):
    users = sorted( glob.glob( os.path.join( users_dir, "*" ) ) )
    con = sql.connect( db )
    pInc = 0
    cInc = 0
    for user in users:
        """
            Read user information from user.txt
        """
        u_FileDetails = os.path.join( user, "user.txt" )
        u_Info = defaultdict( lambda: None )
        uID = re.findall( r'z[0-9]{7}', user )
        with open( u_FileDetails ) as f:
            for line in f:
                line = line.rstrip( )   # Chomp
                lineInfo = line.split( "=", 1 ) # Split on '='
                if len( lineInfo ) != 2: break;     # Skip this line if it doesnt have what we need

                if lineInfo[ 0 ] == "mates" or lineInfo[ 0 ] == "courses":            # Special case for parsing mates/courses
                    lineInfo[ 1 ] = re.sub( r'(\[|\])', '', lineInfo[ 1 ] )
                    infoList = lineInfo[ 1 ].split( ', ' )
                    infoList.pop( )    # Remove last useless element

                    if lineInfo[ 0 ] == "mates":
                        for mate in infoList:  # Loop through the mates of each user
                            cur = con.cursor( )
                            cur.execute( "INSERT INTO Mate VALUES( ?, ? )", ( uID[ 0 ], mate ) )
                    else:
                        for course in infoList:
                            cur = con.cursor( )
                            cur.execute( "INSERT INTO Course VALUES( ?, ? )", ( uID[ 0 ], course ) )

                u_Info[ lineInfo[ 0 ] ] = lineInfo[ 1 ]

        cur = con.cursor( )
        cur.execute( "INSERT INTO User VALUES (?, ?, ?, ?, ?, ?, ?)", ( u_Info[ "zid"],     \
                u_Info[ "full_name" ], u_Info[ "email" ], u_Info[ "password" ],             \
                u_Info[ "birthday" ], u_Info[ "home_suburb" ], u_Info[ "program" ] ) )
        """
            Read posts/comments/replies
            ( zID, message, time, from, longitude, latitude )
        """
        posts = sorted( glob.glob( os.path.join( user, "posts", "*" ) ) )
        for post in posts:
            p_Info = defaultdict( lambda: None )
            u_PostDetails = os.path.join( post, "post.txt" )
            with io.open( u_PostDetails, 'r', encoding='utf-8') as p:
                for line in p:
                    line = line.rstrip( )   # Chomp
                    lineInfo = line.split( "=", 1 ) # Split on '='
                    if len( lineInfo ) != 2: break;     # Skip this line if it doesnt have what we need

                    p_Info[ lineInfo[ 0 ] ] = lineInfo[ 1 ]

            pInc += 1
            cur = con.cursor( )
            cur.execute( "INSERT INTO Post VALUES( ?, ?, ?, ?, ?, ? )", (       \
                None, p_Info[ "from" ], p_Info[ "message" ], p_Info[ "time" ],  \
                p_Info[ "longitude" ], p_Info[ "latitude" ] ) )


            """ Store comments """
            if not os.path.isdir( os.path.join( post, "comments" ) ):      # Check if a comments folder exists.
                continue

            comments = sorted( glob.glob( os.path.join( post, "comments", "*" ) ) )
            for comment in comments:
                c_Info = defaultdict( lambda: None )
                u_CommDetails = os.path.join( comment, "comment.txt" )
                with io.open( u_CommDetails, 'r', encoding='utf-8') as p:
                    for line in p:
                        line = line.rstrip( )   # Chomp
                        lineInfo = line.split( "=", 1 ) # Split on '='
                        if len( lineInfo ) != 2: break;     # Skip this line if it doesnt have what we need

                        if( lineInfo[ 0 ] == "message" ):       # If we find z5555555, convert it into @z5555555
                            lineInfo[ 1 ] = re.sub( r'(z[0-9]{7})', r'@\1', lineInfo[ 1 ] )

                        c_Info[ lineInfo[ 0 ] ] = lineInfo[ 1 ]

                cInc += 1
                cur = con.cursor( )
                cur.execute( "INSERT INTO Comment VALUES( ?, ?, ?, ?, ? )", (       \
                    None, pInc, c_Info[ "from" ], c_Info[ "message" ],              \
                    c_Info[ "time" ] ) )

                if not os.path.isdir( os.path.join( comment, "replies" ) ):      # Check if a comments folder exists.
                    continue

                replies = sorted( glob.glob( os.path.join( comment, "replies", "*" ) ) )
                for reply in replies:
                    r_Info = defaultdict( lambda: None )
                    u_ReplDetails = os.path.join( reply, "reply.txt" )
                    with io.open( u_ReplDetails, 'r', encoding='utf-8') as p:
                        for line in p:
                            line = line.rstrip( )   # Chomp
                            lineInfo = line.split( "=", 1 ) # Split on '='
                            if len( lineInfo ) != 2: break;     # Skip this line if it doesnt have what we need

                            if( lineInfo[ 0 ] == "message" ):       # If we find z5555555, convert it into @z5555555
                                lineInfo[ 1 ] = re.sub( r'(z[0-9]{7})', r'@\1', lineInfo[ 1 ] )

                            r_Info[ lineInfo[ 0 ] ] = lineInfo[ 1 ]

                    cur = con.cursor( )
                    cur.execute( "INSERT INTO Reply VALUES( ?, ?, ?, ?, ?, ? )", (      \
                        None, cInc, pInc, r_Info[ "from" ], r_Info[ "message" ],        \
                        c_Info[ "time" ] ) )

    con.commit( )
    con.close( )

main( )

if __name__ == "__main__":
    app.run( debug=True, port=5000, host="0.0.0.0") #, threaded=True) # 0.0.0.0
