from flask import Flask, request, make_response, jsonify
from flask import render_template, redirect, url_for
from flask import session as login_session
from pprint import pprint

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, CatalogCategory, CategoryItem

from oauth2client.client import flow_from_clientsecrets, FlowExchangeError

import random
import string
import httplib2
import json
import requests

app = Flask(__name__)
clientFile = open('client_secrets.json', 'r').read()
CLIENT_ID = json.loads(clientFile)['web']['client_id']

engine = create_engine('sqlite:///catalog.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()


# check if username is present in the login session,
# otherwise, direct them to login
def isValidUser():
    if 'username' not in login_session:
        return False
    else:
        return True


@app.route('/')
@app.route('/catalog')
def CatalogFront():
    possibleChars = string.ascii_uppercase + string.digits
    state = ''.join(random.choice(possibleChars) for x in xrange(32))
    login_session['state'] = state
    return redirect(url_for('viewCategoryItems', categoryId=1))


@app.route('/catalog/<int:categoryId>')
def viewCategoryItems(categoryId):
    isLoggedIn = isValidUser()
    catalog = session.query(CatalogCategory)
    items = session.query(CategoryItem).filter_by(category_id=categoryId)
    category = session.query(CatalogCategory).filter_by(id=categoryId).one()
    return render_template('items.html', catalog=catalog,
                           items=items,
                           category=category,
                           state=login_session['state'],
                           loggedIn=isLoggedIn)


@app.route('/catalog/new', methods=['GET', 'POST'])
def addCategoryItem():
    # direct invalid user back to main page
    if not isValidUser():
        return CatalogFront()
    catalog = session.query(CatalogCategory)
    if request.method == 'POST':
        print login_session.get('gplus_id')
        # get new item params from form submitted
        newItem = CategoryItem(title=request.form['title'],
                               description=request.form['description'],
                               category_id=request.form['category'],
                               user=login_session.get('gplus_id'))
        session.add(newItem)
        session.commit()
        return redirect(url_for('viewCategoryItems', categoryId=1))
    return render_template('newItem.html', catalog=catalog)


@app.route('/catalog/edit/<int:itemId>', methods=['GET', 'POST'])
def editCategoryItem(itemId):
    item = session.query(CategoryItem).filter_by(id=itemId).one()
    # direct invalid user back to main page
    if not isValidUser() or not item.user == login_session.get('gplus_id'):
        return CatalogFront()
    catalog = session.query(CatalogCategory)
    if request.method == 'POST':
        # get new item params from form submitted
        item.title = request.form['title']
        item.description = request.form['description']
        item.category_id = request.form['category']
        session.add(item)
        session.commit()
        return redirect(url_for('viewCategoryItems', categoryId=1))
    return render_template('editItem.html', catalog=catalog,
                           item=item)


@app.route('/catalog/delete/<int:categoryId>/<int:itemId>',
           methods=['GET', 'POST'])
def deleteCategoryItem(categoryId, itemId):
    item = session.query(CategoryItem).filter_by(id=itemId).one()
    # direct invalid user back to main page
    if not isValidUser() or not item.user == login_session.get('gplus_id'):
        return CatalogFront()
    catalog = session.query(CatalogCategory)
    category = session.query(CatalogCategory).filter_by(id=categoryId).one()
    if request.method == 'POST':
        session.delete(item)
        session.commit()
        return redirect(url_for('viewCategoryItems', categoryId=1))
    return render_template('deleteItem.html', category=category,
                           item=item)


@app.route('/catalog.json')
def catalogJsonAll():
    jsonList = []
    items = session.query(CategoryItem)
    for item in items:
        jsonList.append(item.serialize)
    return jsonify(catalogItems=jsonList)


@app.route('/catalog.json/<int:itemId>')
def catalogJson(itemId):
    item = session.query(CategoryItem).filter_by(id=itemId).one()
    return jsonify(catalogItem=item.serialize)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    print login_session
    # print request.args
    if request.args.get('state') != login_session['state']:
        print "invalid state name"
        response = make_response(json.dumps('Invalid state name'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    code = request.data
    try:
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        print "Flow Error"
        err = 'Failed to update the authorization code.'
        response = make_response(json.dumps(err), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # check validity of access token
    googleApi = 'https://www.googleapis.com/oauth2/v1/tokeninfo'
    url = googleApi + '?access_token=' + credentials.access_token
    h = httplib2.Http()
    req = h.request(url, 'GET')
    result = json.loads(h.request(url, 'GET')[1])
    print result
    # abort if an error occured
    if result.get('error') is not None:
        print "valid token error"
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response
    # verify token is for intended user
    gplus_id = credentials.id_token.values()[0]
    if result['user_id'] != gplus_id:
        print "error token -> user"
        err = 'Token\'s user id doesn\'t match given user id.'
        response = make_response(json.dumps(err), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    if result['issued_to'] != CLIENT_ID:
        print "error client -> app"
        err = 'Token\'s client id doesn\'t match application id.'
        response = make_response(json.dumps(err), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # check if user is already logged in
    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        print "already logged in"
        # login_session['credentials'] = credentials
        note = 'Current user is already connected.'
        response = make_response(json.dumps(note), 200)
        response.headers['Content-Type'] = 'application/json'

    print "logged in"
    print credentials.access_token
    # store token in session for later use
    login_session['credentials'] = credentials
    login_session['gplus_id'] = gplus_id

    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)
    data = json.loads(answer.text)
    print data
    login_session['username'] = data["name"]
    login_session['picture'] = data["picture"]
    login_session['email'] = data["email"]
    return redirect(url_for('viewCategoryItems', categoryId=1))


@app.route('/gdisconnect', methods=['POST'])
def gdisconnect():
    # only target connected user
    credentials = login_session.get('credentials')
    if credentials is None:
        print "no credentials"
        err = 'Current user not connected.'
        response = make_response(json.dumps(err), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # revoke token
    # res = credentials.revoke(httplib2.Http())
    # print res
    access_token = credentials.access_token
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print result
    if result['status'] == '200':
        print "logged out"
        del login_session['username']
        del login_session['picture']
        del login_session['email']

        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        print "failed to revoke"
        response = make_response(json.dumps('Failed to revoke token.'), 400)
        response.headers['Content-Type'] = 'application/json'
        return response


if __name__ == '__main__':
    app.secret_key = 'super secret key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
