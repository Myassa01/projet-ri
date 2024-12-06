import os
import re
from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize
import nltk

# Télécharger les ressources NLTK si nécessaire
try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt")

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

# Prétraitement des textes
def preprocess_text(text, stoplist):
    text = text.lower()
    text = re.sub(r"[\'\"\/\\,;.!:?()&$0123456789]", " ", text)  # Supprimer caractères spéciaux
    words = word_tokenize(text)  # Segmenter le texte
    return [word for word in words if word not in stoplist]

# Normalisation avec Porter Stemmer
def normalize_words(words):
    stemmer = PorterStemmer()
    return [stemmer.stem(word) for word in words]

# Traiter les documents pour créer un index
def process_documents(documents, stoplist):
    processed_index = {}
    for filename, content in documents.items():
        words = preprocess_text(content, stoplist)
        normalized_words = normalize_words(words)
        index_name = f"index{filename.split('.')[0].upper()}"
        processed_index[index_name] = normalized_words
    return processed_index

# Sauvegarder les index dans MongoDB
def save_indexes_to_mongo(index):
    index_collection = db["index"]
    index_collection.delete_many({})  # Effacer les anciens index
    for index_name, words in index.items():
        index_collection.insert_one({
            "index_name": index_name,
            "terms": list(words)  # Convertir en liste
        })
    print("Index sauvegardé avec succès dans MongoDB!")

# Construire un fichier inverse
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

# Sauvegarder le fichier inverse dans MongoDB
def save_inverted_index_to_mongo(inverted_index):
    inverted_index_collection = db["inverted_index"]
    inverted_index_collection.delete_many({})  # Effacer les anciens fichiers inverses
    for term, postings in inverted_index.items():
        inverted_index_collection.insert_one({
            "term": term,
            "postings": postings
        })
    print("Fichier inverse sauvegardé avec succès dans MongoDB!")

# Prétraiter une requête booléenne
def preprocess_query(query):
    query = query.lower()
    query = re.sub(r"[\'\"\/\\,;.!:?()&$0123456789]", " ", query)  # Supprimer caractères spéciaux
    return query

# Obtenir les documents contenant un terme donné
def get_postings(term, inverted_index):
    result = inverted_index.find_one({"term": term})
    if result:
        return set(result.get("postings", {}).keys())
    return set()

# Traiter une requête booléenne
def process_boolean_query(query, inverted_index):
    query = preprocess_query(query)
    tokens = re.split(r"\s+(et|ou|not)\s+", query)
    tokens = [token.strip() for token in tokens]

    if len(tokens) == 1:
        return get_postings(tokens[0], inverted_index)

    results = set()
    current_operator = None

    for token in tokens:
        if token in {"et", "ou", "not"}:
            current_operator = token
        else:
            postings = get_postings(token, inverted_index)
            if current_operator is None:
                results = postings
            elif current_operator == "et":
                results = results & postings
            elif current_operator == "ou":
                results = results | postings
            elif current_operator == "not":
                results = results - postings

    return results

# Fonction principale
def main():
    stoplist = load_stoplist("stoplist.txt")
    documents = load_documents()
    processed_index = process_documents(documents, stoplist)
    save_indexes_to_mongo(processed_index)
    inverted_index = build_inverted_index_with_frequency(processed_index)
    save_inverted_index_to_mongo(inverted_index)

# Application Flask
app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/search", methods=["GET"])
def search():
    query = request.args.get("query", "").strip()
    if not query:
        return jsonify({"query": query, "documents": "Veuillez entrer une requête."})

    inverted_index = db["inverted_index"]
    results = process_boolean_query(query, inverted_index)

    if results:
        return jsonify({"query": query, "documents": list(results)})
    else:
        return jsonify({"query": query, "documents": "Aucun résultat trouvé."})

if __name__ == "__main__":
    main()  # Construire les index et fichiers inverses
    app.run(debug=True)
