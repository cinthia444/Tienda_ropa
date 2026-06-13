from pymongo import MongoClient

MONGO_URI = "mongodb+srv://cinthialopezku15_db_user:cinthialopez098@inventarioropa.igzcvec.mongodb.net/?retryWrites=true&w=majority&appName=inventarioropa"

client = MongoClient(MONGO_URI)

db = client["inventarioropa"]

productos_collection = db["productos"]
usuarios_collection = db["usuarios"]
ventas_collection = db["ventas"]
carrito_collection = db["carrito"]

print("✅ MongoDB conectado correctamente")
