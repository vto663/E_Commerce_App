import pymongo
print(f"PyMongo version: {pymongo.__version__}")

# Проверка на връзката с MongoDB
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
print(f"Свързах се с MongoDB: {client.server_info()['version']}")

# Списък с базите данни
print("Налични бази данни:", client.list_database_names())

client.close()