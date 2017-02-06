After navigating to the catalog directory in vagrant,
run the "python database_setup.py" and "python catalog_init.py" in sequence to setup the database.
Then run the "python app.py" to host the server locally.
Visit the page at "http://localhost:5000/catalog". Login to be able to use additional functions.
You can also view a json formatted db at http://localhost:5000/catalog.json.
Individual items can be retrieved via http://localhost:5000/catalog.json/1.
