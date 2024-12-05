import os
from pymongo import MongoClient

# Connexion à MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["RI"]  # Nom de la base de données
collection = db["myCollection"]  # Nom de la collection

# Chemin du dossier contenant les fichiers
folder_path = "Collection_TIME"  # Remplacez par le chemin réel

# Parcourir tous les fichiers du dossier
for filename in os.listdir(folder_path):
    if filename.endswith(".txt"):  # Filtrer uniquement les fichiers .txt
        file_path = os.path.join(folder_path, filename)
        
        # Lire le contenu du fichier
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
        
        # Échapper les caractères spéciaux
        content = content.replace('"', '\\"').replace('\n', '\\n')
        
        # Créer le document JSON
        document = {
            "filename": filename,  # Nom du fichier
            "content": content     # Contenu du fichier
        }
        
        # Insérer le document dans MongoDB
        collection.insert_one(document)
        print(f"Document '{filename}' inséré avec succès!")

print("Tous les documents ont été insérés avec succès!")