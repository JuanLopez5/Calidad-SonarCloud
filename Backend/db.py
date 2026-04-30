
# The MongoDB connection is commented out for now while we wait for access.
# When your teammate provides permissions uncomment the lines below.
# from pymongo.mongo_client import MongoClient
# from pymongo.server_api import ServerApi
#
# uri = "mongodb+srv://admin:$admin1@fridgedb.ri4ezxk.mongodb.net/?appName=FridgeDB"
#
# # Create a new client and connect to the server
# client = MongoClient(uri, server_api=ServerApi('1'))
#
# # Send a ping to confirm a successful connection
# try:
#     client.admin.command('ping')
#     print("Pinged your deployment. You successfully connected to MongoDB!")
# except Exception as e:
#     print(e)
#
# mongo_db = client["FridgeDB"]

# DB is disabled for now; provide a minimal placeholder object so imports
# that do `mongo_db["collection"]` don't crash at import time. The
# placeholder returns a collection-like object that provides safe read
# defaults (empty lists / None) and non-destructive write responses.
class _DisabledCollection:
	def __init__(self, name):
		self._name = name

	def insert_one(self, doc):
		# Writes are disabled in this mode; inform the caller.
		raise RuntimeError('MongoDB disabled in development: insert_one is unavailable')

	def find_one(self, query=None):
		return None

	def find(self, query=None, projection=None):
		return []

	def update_one(self, filt, update):
		return type('R', (), {'modified_count': 0})()


class _DisabledDB:
	def __getitem__(self, name):
		return _DisabledCollection(name)


mongo_db = _DisabledDB()
