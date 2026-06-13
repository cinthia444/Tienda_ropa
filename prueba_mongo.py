from pymongo import MongoClient

client = MongoClient(
    "mongodb+srv://cinthialopezku15_db_user:cinthialopez098@inventarioropa.igzcvec.mongodb.net/?retryWrites=true&w=majority&appName=inventarioropa"
)

db = client["inventario_ropa"]

print("✅ Conectado a MongoDB Atlas")