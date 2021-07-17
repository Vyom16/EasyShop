import os
import sqlite3
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import apology, login_required, usd
import json

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Loading Database
conn = sqlite3.connect("easyshop.db", check_same_thread=False)
db = conn.cursor()

# Loading Items from Database
ITEMS_CURSOR = db.execute("SELECT * FROM items")

ITEMS_LIST = []
COLS = ['uniq_id','name','product_category_tree','retail_price','price','image_link','description','product_rating','overall_rating','brand','product_specifications']
for row in ITEMS_CURSOR:
    new_val = {}
    for i in range(len(row)):
        if i != 5:
            new_val[COLS[i]] = row[i]
        else:
            new_val[COLS[i]] = row[i].replace('{','').replace('}','').replace('"','').replace('[','').replace(']','').split(',')
    ITEMS_LIST.append(new_val)

@app.route("/")
def index():
    """Show Products"""

    return render_template("index.html", items=ITEMS_LIST)

@app.route("/scan", methods=["GET", "POST"])
@login_required
def scan():
    """Scan and add item to cart"""

    if request.method == "POST":

        Item_id = request.form.get("Item_id")
        Number = request.form.get("Number")
        User_id = session["user_id"]

        # Query the database for Item_ID
        cursor = db.execute("SELECT * FROM items WHERE uniq_id = ?",
                                (Item_id,))
        
        # Reading Result
        rows = []
        for row in cursor:
            rows.append(row)
        
        # Error Check
        if (len(rows) == 0):
            return apology("Item Not Found", 402)
        
        # Reading User Data
        cursor = db.execute("SELECT * FROM users WHERE id = ?",
                            (User_id,))
        
        rows = []
        for row in cursor:
            rows.append(row)
        
        cart_data = rows[0][3]

        data = cart_data.split(',')
        flag = 1
        cart_data = ""
        for i in data[:-1]:
            k = i.split(":")
            if k[0] == Item_id :
                k[1] = int(k[1]) + int(Number)
                cart_data = cart_data + k[0] + ":"+ str(k[1]) + ','
                flag = 0
            else:
                cart_data = cart_data + i + ','
        if flag:
            cart_data = cart_data + Item_id + ":" + str(Number) + ','

        # Updating Database
        db.execute("UPDATE users SET cart=? WHERE id=?",(
                    cart_data,
                    User_id,))
        conn.commit()
        
        return redirect("/")

    return render_template("scan.html")

@app.route("/cart")
@login_required
def cart():
    """Show users cart"""

    User_id = session["user_id"]

    cursor = db.execute("SELECT * FROM users WHERE id = ?",
                                (User_id,))
        
    # Reading Result
    rows = []
    for row in cursor:
        rows.append(row)
    cart_data = rows[0][3]

    new_dat = ""
    new_dict = {}
    for data in cart_data.split(",")[:-1]:
        new_dat = new_dat + "'" + data.split(':')[0] + "'" + ","
        new_dict[data.split(":")[0]] = int(data.split(":")[1])
    new_dat = new_dat[:-1]
    
    # If Cart Is Empty
    if (cart_data == ""):
        return apology("No Item Selected", 402)

    # Reading Items from Table
    cursor = db.execute("SELECT * FROM items WHERE uniq_id IN (%s)" %(new_dat))

    items = []
    total = 0
    for row in cursor:
        new_val = {}
        for i in range(len(row)):
            if i != 5:
                new_val[COLS[i]] = row[i]
            else:
                new_val[COLS[i]] = row[i].replace('{','').replace('}','').replace('"','').replace('[','').replace(']','').split(',')
        new_val["number"] = new_dict[new_val["uniq_id"]]

        total += new_val["number"] * float(new_val["price"])
        items.append(new_val)

    return render_template("cart.html", items=items, total=round(total,2))


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("Must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("Must provide password", 403)

        # Query database for username
        cursor = db.execute("SELECT * FROM users WHERE username = ?",
                          (request.form.get("username"),))

        rows = []
        for row in cursor:
            rows.append(row)

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0][2], request.form.get("password")):
            return apology("Invalid username or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0][0]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    
    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("Must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("Must provide password", 403)

        # Ensure Confirmation password was submitted
        elif not request.form.get("Cpassword"):
            return apology("Must Confirm Password", 403)

        # Checks if Password Entered is correct
        elif request.form.get("password") != request.form.get("Cpassword"):
            return apology("Passwords Not Matching", 403)

        # Query database for username
        cursor = db.execute("SELECT * FROM users WHERE username = ?",
                          (request.form.get("username"),))

        for row in cursor:
            if (row[1] == request.form.get("username")):
                return apology("Username already in use", 403)

        # Inserting Username and Password-Hash to database.users
        db.execute("INSERT INTO users (username, hash) VALUES (?, ?)",(
                    request.form.get("username"),
                    generate_password_hash(request.form.get("password")),))

        conn.commit()

        # Query database for username
        cursor = db.execute("SELECT * FROM users WHERE username = ?",
                          (request.form.get("username"),))

        for row in cursor:
            if (row[1] == request.form.get("username")):
                session["user_id"] = row[0]

        return render_template("index.html", items=ITEMS_LIST)
    
    else:
        return render_template("register.html")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)