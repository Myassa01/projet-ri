import os
import re
from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize
import nltk
import nltk
try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt")
try:
    nltk.data.find("tokenizers/punkt_tab/english")
except LookupError:
    nltk.download("punkt_tab")


# Vérifier et télécharger les ressources nécessaires
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

# Connexion à MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["RI"]
collection = db["myCollection"]

# Charger la stoplist
def load_stoplist(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        stoplist = set(file.read().splitlines())
    return stoplist

# Charger les documents depuis MongoDB
def load_documents():
    documents = collection.find()
    return {doc['filename']: doc['content'] for doc in documents}

# Analyse lexicale et suppression des mots vides
def preprocess_text(text, stoplist):
    # Convertir en minuscules
    text = text.lower()
    
     # Supprimer les caractères spéciaux spécifiés
    text = re.sub(r"[\'\"\/\\,;.!:?()&$0123456789]", " ", text)  # Remplacer les caractères par des espaces

    # Segmenter le texte en mots
    words = word_tokenize(text)

    # Supprimer les mots vides
    filtered_words = [word for word in words if word not in stoplist]
    return filtered_words

# Normalisation avec Porter Stemmer
def normalize_words(words):
    stemmer = PorterStemmer()
    stems = [stemmer.stem(word) for word in words]
    return stems

# Traiter et stocker les résultats pour chaque document
def process_documents(documents, stoplist):
    processed_index = {}

    for filename, content in documents.items():
        # Étape 1 : Analyse lexicale
        words = preprocess_text(content, stoplist)
        
        # Étape 2 : Normalisation
        normalized_words = normalize_words(words)
        
        # Étape 3 : Stocker dans une structure
        index_name = f"index{filename.split('.')[0].upper()}"
        processed_index[index_name] = normalized_words

    return processed_index

# Sauvegarder les index dans MongoDB
def save_indexes_to_mongo(index):
    index_collection = db["index"]
    for index_name, words in index.items():
        index_collection.insert_one({
            "index_name": index_name,
            "terms": words
        })
    print("Index sauvegardé avec succès dans MongoDB!")
    
def build_inverted_index(indexes):
    inverted_index = {}

    for index_name, terms in indexes.items():
        for term in terms:
            if term not in inverted_index:
                inverted_index[term] = []
            if index_name not in inverted_index[term]:
                inverted_index[term].append(index_name)
    
    return inverted_index

def build_inverted_index_with_frequency(indexes):
    inverted_index = {}

    for index_name, terms in indexes.items():
        for term in terms:
            if term not in inverted_index:
                inverted_index[term] = {}
            if index_name not in inverted_index[term]:
                inverted_index[term][index_name] = 0
            inverted_index[term][index_name] += 1
    
    return inverted_index

def save_inverted_index_to_mongo(inverted_index):
    index_collection = db["inverted_index"]
    for term, postings in inverted_index.items():
        index_collection.insert_one({
            "term": term,
            "postings": postings
        })
    print("Fichier inverse sauvegardé dans MongoDB!")


def main():
    # Charger la stoplist
    stoplist = load_stoplist("stoplist.txt")

    # Charger les documents depuis MongoDB
    documents = load_documents()

    # Traiter les documents
    processed_index = process_documents(documents, stoplist)

    # Sauvegarder les index (MongoDB ou fichiers locaux)
    save_indexes_to_mongo(processed_index)  # Option 1 : MongoDB
    
    # Construire le fichier inverse
    inverted_index = build_inverted_index_with_frequency(processed_index)

    # Sauvegarder le fichier inverse
    save_inverted_index_to_mongo(inverted_index)  # Option 1 : MongoDB


app = Flask(__name__)

# Connexion à MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["RI"]

# Route pour afficher la page HTML
@app.route("/")
def index():
    return render_template("index.html")

# Route pour effectuer une recherche
@app.route("/search", methods=["GET"])
def search():
    query = request.args.get("query", "").lower()  # Obtenir la requête utilisateur
    inverted_index = db["inverted_index"]

    # Rechercher dans l'index inversé
    results = inverted_index.find_one({"term": query})
    if results:
        documents = results.get("postings", {})
        return jsonify({"query": query, "documents": documents})
    else:
        return jsonify({"query": query, "documents": "Aucun résultat trouvé."})

if __name__ == "__main__":
    app.run(debug=True)
