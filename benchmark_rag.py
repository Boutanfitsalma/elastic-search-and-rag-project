"""
Script de Benchmark pour le système RAG
Mesure les latences et génère un rapport pour compléter le document LaTeX
"""
import time
import json
import statistics
from datetime import datetime
from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer
import requests

# Configuration
ES_HOST = 'localhost:9200'
ES_INDEX = 'mozilla-ci-logs-semantic-v2'
OLLAMA_API = 'http://localhost:11434/api/generate'
OLLAMA_MODEL = 'mistral'

print("🚀 BENCHMARK RAG - Mozilla CI Log Analysis")
print("=" * 80)
print()

# Charger le modèle
print("📦 Chargement du modèle Sentence-BERT...")
start = time.time()
model = SentenceTransformer('all-MiniLM-L6-v2')
model_load_time = time.time() - start
print(f"✅ Modèle chargé en {model_load_time:.2f}s")
print()

# Connexion ES
es = Elasticsearch([f'http://{ES_HOST}'])

# Questions de test
test_questions = [
    "Quels sont les 5 builds les plus lents ?",
    "Erreurs de compilation sur Linux",
    "Problèmes de performance CPU",
    "Builds échoués sur Windows",
    "Compare Windows vs Linux",
    "Résume les problèmes principaux",
    "Tests qui crashent",
    "Durée moyenne des builds",
    "Plateforme avec le plus d'erreurs",
    "Builds avec timeout"
]

print(f"📝 {len(test_questions)} questions de test préparées")
print()

# ============================================================================
# BENCHMARK 1 : Génération d'embeddings
# ============================================================================

print("=" * 80)
print("1️⃣  BENCHMARK : Génération d'embeddings")
print("=" * 80)

embedding_times = []
for i, question in enumerate(test_questions, 1):
    start = time.time()
    embedding = model.encode(question).tolist()
    elapsed = (time.time() - start) * 1000  # en ms
    embedding_times.append(elapsed)
    print(f"  Question {i}/10: {elapsed:.1f} ms")

print()
print("📊 Statistiques embeddings:")
print(f"  • Temps moyen: {statistics.mean(embedding_times):.1f} ms")
print(f"  • Temps min: {min(embedding_times):.1f} ms")
print(f"  • Temps max: {max(embedding_times):.1f} ms")
print(f"  • Écart-type: {statistics.stdev(embedding_times):.1f} ms")
print()

# ============================================================================
# BENCHMARK 2 : Recherche Elasticsearch (kNN seul)
# ============================================================================

print("=" * 80)
print("2️⃣  BENCHMARK : Recherche kNN (sémantique pur)")
print("=" * 80)

knn_times = []
for i, question in enumerate(test_questions, 1):
    query_embedding = model.encode(question).tolist()
    
    search_query = {
        "knn": {
            "field": "embedding",
            "query_vector": query_embedding,
            "k": 5,
            "num_candidates": 200
        },
        "_source": {"excludes": ["embedding"]}
    }
    
    start = time.time()
    try:
        results = es.search(index=ES_INDEX, body=search_query)
        elapsed = (time.time() - start) * 1000  # en ms
        knn_times.append(elapsed)
        print(f"  Question {i}/10: {elapsed:.1f} ms ({len(results['hits']['hits'])} résultats)")
    except Exception as e:
        print(f"  Question {i}/10: ERREUR - {e}")
        knn_times.append(0)

print()
print("📊 Statistiques recherche kNN:")
print(f"  • Temps moyen: {statistics.mean([t for t in knn_times if t > 0]):.1f} ms")
print(f"  • Temps min: {min([t for t in knn_times if t > 0]):.1f} ms")
print(f"  • Temps max: {max([t for t in knn_times if t > 0]):.1f} ms")
print()

# ============================================================================
# BENCHMARK 3 : Recherche Hybride (kNN + BM25)
# ============================================================================

print("=" * 80)
print("3️⃣  BENCHMARK : Recherche Hybride (kNN + BM25)")
print("=" * 80)

hybrid_times = []
for i, question in enumerate(test_questions, 1):
    query_embedding = model.encode(question).tolist()
    
    search_query = {
        "size": 5,
        "query": {
            "bool": {
                "should": [
                    {
                        "multi_match": {
                            "query": question,
                            "fields": ["text_content^2", "metadata.builder"],
                            "boost": 1.0
                        }
                    }
                ]
            }
        },
        "knn": {
            "field": "embedding",
            "query_vector": query_embedding,
            "k": 5,
            "num_candidates": 200,
            "boost": 2.5
        },
        "_source": {"excludes": ["embedding"]}
    }
    
    start = time.time()
    try:
        results = es.search(index=ES_INDEX, body=search_query)
        elapsed = (time.time() - start) * 1000  # en ms
        hybrid_times.append(elapsed)
        print(f"  Question {i}/10: {elapsed:.1f} ms ({len(results['hits']['hits'])} résultats)")
    except Exception as e:
        print(f"  Question {i}/10: ERREUR - {e}")
        hybrid_times.append(0)

print()
print("📊 Statistiques recherche Hybride:")
print(f"  • Temps moyen: {statistics.mean([t for t in hybrid_times if t > 0]):.1f} ms")
print(f"  • Temps min: {min([t for t in hybrid_times if t > 0]):.1f} ms")
print(f"  • Temps max: {max([t for t in hybrid_times if t > 0]):.1f} ms")
print()

# ============================================================================
# BENCHMARK 4 : Génération LLM (Mistral)
# ============================================================================

print("=" * 80)
print("4️⃣  BENCHMARK : Génération LLM (Mistral)")
print("=" * 80)
print("⚠️  Ceci peut prendre 2-5 minutes...")
print()

llm_times = []

# Prendre seulement 5 questions pour le benchmark LLM (trop long sinon)
sample_questions = test_questions[:5]

for i, question in enumerate(sample_questions, 1):
    # Simuler un contexte compact
    context = """1. mozilla-esr52_ubuntu64 | failure | 2134s | CPU:45% | Err:12
2. mozilla-esr52_win7 | failure | 1987s | CPU:67% | Err:8
3. mozilla-esr52_linux64 | success | 1543s | CPU:32% | Err:2
4. mozilla-esr52_mac | success | 1876s | CPU:41% | Err:3
5. mozilla-esr52_win8 | failure | 2341s | CPU:78% | Err:15"""
    
    prompt = f"""Expert CI/CD Mozilla. Réponds en 3-5 phrases max.

LOGS:
{context}

QUESTION: {question}
RÉPONSE COURTE:"""
    
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 200
        }
    }
    
    start = time.time()
    try:
        response = requests.post(OLLAMA_API, json=payload, timeout=180)
        elapsed = time.time() - start
        llm_times.append(elapsed)
        answer = response.json().get('response', 'N/A')
        tokens = len(answer.split())
        print(f"  Question {i}/5: {elapsed:.2f}s ({tokens} tokens générés)")
    except requests.exceptions.Timeout:
        print(f"  Question {i}/5: TIMEOUT (>180s)")
        llm_times.append(180)
    except Exception as e:
        print(f"  Question {i}/5: ERREUR - {e}")
        llm_times.append(0)

print()
if llm_times and any(t > 0 for t in llm_times):
    print("📊 Statistiques génération LLM:")
    valid_times = [t for t in llm_times if t > 0]
    print(f"  • Temps moyen: {statistics.mean(valid_times):.2f}s")
    print(f"  • Temps min: {min(valid_times):.2f}s")
    print(f"  • Temps max: {max(valid_times):.2f}s")
    if len(valid_times) > 1:
        print(f"  • Écart-type: {statistics.stdev(valid_times):.2f}s")
else:
    print("⚠️  Pas de mesures LLM valides (Ollama non démarré ?)")
print()

# ============================================================================
# BENCHMARK 5 : Latence End-to-End
# ============================================================================

print("=" * 80)
print("5️⃣  BENCHMARK : Latence End-to-End (1 question complète)")
print("=" * 80)

test_question = "Quels sont les builds les plus lents ?"
print(f"Question test: {test_question}")
print()

# Mesurer chaque étape
start_total = time.time()

# Étape 1: Embedding
start = time.time()
query_embedding = model.encode(test_question).tolist()
time_embedding = (time.time() - start) * 1000
print(f"  1. Génération embedding: {time_embedding:.1f} ms")

# Étape 2: Recherche ES
start = time.time()
search_query = {
    "size": 5,
    "query": {
        "bool": {
            "should": [
                {
                    "multi_match": {
                        "query": test_question,
                        "fields": ["text_content^2", "metadata.builder"],
                        "boost": 1.0
                    }
                }
            ]
        }
    },
    "knn": {
        "field": "embedding",
        "query_vector": query_embedding,
        "k": 5,
        "num_candidates": 200,
        "boost": 2.5
    },
    "_source": {"excludes": ["embedding"]}
}
results = es.search(index=ES_INDEX, body=search_query)
time_search = (time.time() - start) * 1000
print(f"  2. Recherche ES: {time_search:.1f} ms")

# Étape 3: Préparation contexte
start = time.time()
context_parts = []
for hit in results['hits']['hits'][:5]:
    src = hit['_source']
    m = src.get('metadata', {})
    met = src.get('metrics', {})
    err = src.get('errors', {})
    
    doc = f"{m.get('builder', 'N/A')[:40]} | "
    doc += f"{m.get('result_status', 'N/A')} | "
    doc += f"{met.get('duration_seconds', 0):.0f}s"
    context_parts.append(doc)

context = "\n".join(context_parts)
time_context = (time.time() - start) * 1000
print(f"  3. Préparation contexte: {time_context:.1f} ms")

# Étape 4: Génération LLM
start = time.time()
prompt = f"""Expert CI/CD. Réponds brièvement.

LOGS:
{context}

QUESTION: {test_question}
RÉPONSE:"""

payload = {
    "model": OLLAMA_MODEL,
    "prompt": prompt,
    "stream": False,
    "options": {"temperature": 0.1, "num_predict": 200}
}

try:
    response = requests.post(OLLAMA_API, json=payload, timeout=180)
    time_llm = time.time() - start
    print(f"  4. Génération LLM: {time_llm:.2f}s")
except:
    time_llm = 0
    print(f"  4. Génération LLM: ERREUR")

time_total = time.time() - start_total
print()
print(f"⏱️  LATENCE TOTALE END-TO-END: {time_total:.2f}s")
print()

# ============================================================================
# RAPPORT FINAL
# ============================================================================

print("=" * 80)
print("📋 RAPPORT FINAL POUR LE DOCUMENT LATEX")
print("=" * 80)
print()

report = {
    "timestamp": datetime.now().isoformat(),
    "embeddings": {
        "mean_ms": round(statistics.mean(embedding_times), 1),
        "min_ms": round(min(embedding_times), 1),
        "max_ms": round(max(embedding_times), 1)
    },
    "search_knn": {
        "mean_ms": round(statistics.mean([t for t in knn_times if t > 0]), 1),
        "min_ms": round(min([t for t in knn_times if t > 0]), 1),
        "max_ms": round(max([t for t in knn_times if t > 0]), 1)
    },
    "search_hybrid": {
        "mean_ms": round(statistics.mean([t for t in hybrid_times if t > 0]), 1),
        "min_ms": round(min([t for t in hybrid_times if t > 0]), 1),
        "max_ms": round(max([t for t in hybrid_times if t > 0]), 1)
    },
    "llm_generation": {
        "mean_s": round(statistics.mean([t for t in llm_times if t > 0]), 2) if llm_times else 0,
        "min_s": round(min([t for t in llm_times if t > 0]), 2) if llm_times else 0,
        "max_s": round(max([t for t in llm_times if t > 0]), 2) if llm_times else 0
    },
    "end_to_end": {
        "total_s": round(time_total, 2)
    }
}

# Sauvegarder le rapport
with open('benchmark_report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("✅ Rapport sauvegardé dans: benchmark_report.json")
print()

# Afficher les valeurs à copier dans le LaTeX
print("=" * 80)
print("📝 VALEURS À COPIER DANS LE LATEX")
print("=" * 80)
print()

print("Table 4.2 (Temps parsing moyen):")
print(f"  [Temps hors scope - parsing fait en amont]")
print()

print("Table 4.7 (Performance du système RAG):")
print(f"  Recherche kNN: {report['search_knn']['mean_ms']} ms")
print(f"  Recherche hybride: {report['search_hybrid']['mean_ms']} ms")
print(f"  Génération Mistral: {report['llm_generation']['mean_s']} secondes")
print(f"  Latence end-to-end: {report['end_to_end']['total_s']} secondes")
print()

print("Table 4.8 (Comparaison modes):")
print(f"  Mode Hybride - Latence: {report['search_hybrid']['mean_ms']} ms")
print(f"  Mode Sémantique Pur - Latence: {report['search_knn']['mean_ms']} ms")
print()

print("=" * 80)
print("🎉 BENCHMARK TERMINÉ !")
print("=" * 80)