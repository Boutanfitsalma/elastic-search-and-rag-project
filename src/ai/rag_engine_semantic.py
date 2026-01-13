"""
RAG Engine SÉMANTIQUE - Version AMÉLIORÉE
Corrections : anti-hallucination, filtres, agrégations
"""
import json
import requests
from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer
from functools import lru_cache
from datetime import datetime

# Config
ES_HOST = 'localhost:9200'
ES_INDEX = 'mozilla-ci-logs-semantic-v2'
OLLAMA_API = 'http://localhost:11434/api/generate'
OLLAMA_MODEL = 'mistral'

print("🧠 Chargement du modèle d'embeddings...")
model = SentenceTransformer('all-MiniLM-L6-v2')
print("✅ Modèle chargé")

es = Elasticsearch([f'http://{ES_HOST}'])

# Historique
conversation_history = []

# ============================================================================
# KEYWORDS AMÉLIORÉS (avec conjugaisons)
# ============================================================================

FILTER_KEYWORDS = {
    "status": {
        "failure": ["échoué", "échouent", "échec", "échoue", "failed", "failure", "erreur", "erreurs"],
        "success": ["réussi", "réussit", "success", "ok", "succès"]
    },
    "platform": {
        "linux": ["linux", "ubuntu"],
        "windows": ["windows", "win"],
        "mac": ["mac", "osx", "macos"]
    }
}

# Patterns pour détecter les questions d'agrégation
AGGREGATION_PATTERNS = {
    "top_builders_errors": ["builders avec le plus d'erreurs", "top builders erreurs", "builders les plus d'erreurs"],
    "average_duration": ["durée moyenne", "temps moyen", "average duration"],
    "count_by_platform": ["nombre par plateforme", "répartition plateforme"],
}

# ============================================================================
# FONCTIONS HISTORIQUE
# ============================================================================

def add_to_history(question, answer, results_count):
    """Ajoute à l'historique"""
    conversation_history.append({
        'timestamp': datetime.now().isoformat(),
        'question': question,
        'answer': answer,
        'results_count': results_count
    })
    if len(conversation_history) > 10:
        conversation_history.pop(0)

def get_conversation_context():
    """Contexte historique"""
    if not conversation_history:
        return ""
    context = "\nHISTORIQUE (3 dernières questions):\n"
    for i, item in enumerate(conversation_history[-3:], 1):
        context += f"Q{i}: {item['question']}\n"
        context += f"R{i}: {item['answer'][:100]}...\n"
    return context

def clear_history():
    global conversation_history
    conversation_history = []
    print("🗑️  Historique effacé")

# ============================================================================
# EMBEDDINGS
# ============================================================================

@lru_cache(maxsize=100)
def get_cached_embedding(query):
    """Cache embeddings"""
    return model.encode(query).tolist()

# ============================================================================
# DÉTECTION DE FILTRES (AMÉLIORÉ)
# ============================================================================

def detect_filters(query_lower):
    """
    Détecte automatiquement les filtres depuis la question
    Retourne une liste de filtres ES
    """
    filters = []
    
    # Filtre STATUS
    for status, keywords in FILTER_KEYWORDS["status"].items():
        if any(kw in query_lower for kw in keywords):
            filters.append({"term": {"metadata.result_status": status}})
            break  # Un seul statut à la fois
    
    # Filtre PLATFORM
    for platform, keywords in FILTER_KEYWORDS["platform"].items():
        if any(kw in query_lower for kw in keywords):
            filters.append({"term": {"context.platform": platform}})
            break  # Une seule plateforme à la fois
    
    return filters

# ============================================================================
# DÉTECTION DE QUESTIONS D'AGRÉGATION
# ============================================================================

def detect_aggregation_query(query_lower):
    """
    Détecte si la question nécessite une agrégation ES plutôt que du RAG
    Retourne le type d'agrégation ou None
    """
    for agg_type, patterns in AGGREGATION_PATTERNS.items():
        if any(pattern in query_lower for pattern in patterns):
            return agg_type
    return None

# ============================================================================
# AGRÉGATIONS ELASTICSEARCH
# ============================================================================

def get_top_builders_by_errors(limit=5):
    """
    Retourne les top N builders avec le plus d'erreurs (agrégation ES)
    """
    agg_query = {
        "size": 0,
        "aggs": {
            "top_builders": {
                "terms": {
                    "field": "metadata.builder.keyword",
                    "order": {"total_errors": "desc"},
                    "size": limit
                },
                "aggs": {
                    "total_errors": {
                        "sum": {"field": "errors.error_count"}
                    }
                }
            }
        }
    }
    
    try:
        results = es.search(index=ES_INDEX, body=agg_query)
        buckets = results['aggregations']['top_builders']['buckets']
        
        response = f"Les {limit} builders avec le plus d'erreurs sont :\n"
        for i, bucket in enumerate(buckets, 1):
            builder = bucket['key']
            total_errors = int(bucket['total_errors']['value'])
            response += f"{i}. {builder} : {total_errors:,} erreurs\n"
        
        return response.strip()
    except Exception as e:
        return f"❌ Erreur agrégation: {e}"

def get_average_duration():
    """
    Calcule la vraie durée moyenne globale (agrégation ES)
    """
    agg_query = {
        "size": 0,
        "aggs": {
            "avg_duration": {
                "avg": {"field": "metrics.duration_seconds"}
            },
            "count": {
                "value_count": {"field": "metrics.duration_seconds"}
            }
        }
    }
    
    try:
        results = es.search(index=ES_INDEX, body=agg_query)
        avg = results['aggregations']['avg_duration']['value']
        count = results['aggregations']['count']['value']
        
        minutes = int(avg // 60)
        seconds = int(avg % 60)
        
        response = f"La durée moyenne globale des builds est de {avg:.0f} secondes "
        response += f"({minutes} minutes et {seconds} secondes), "
        response += f"calculée sur {count:,} builds."
        
        return response
    except Exception as e:
        return f"❌ Erreur agrégation: {e}"

# ============================================================================
# RECHERCHE SÉMANTIQUE
# ============================================================================

def smart_search(query, limit=5, use_hybrid=True):
    """
    Recherche avec filtres automatiques
    """
    query_lower = query.lower()
    filters = detect_filters(query_lower)
    query_embedding = get_cached_embedding(query)
    
    if use_hybrid:
        # Mode hybride
        search_query = {
            "size": limit,
            "query": {
                "bool": {
                    "should": [
                        {
                            "multi_match": {
                                "query": query,
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
                "k": limit,
                "num_candidates": 200,
                "boost": 2.5
            },
            "_source": {
                "excludes": ["embedding"]
            }
        }
        
        # Ajouter filtres SEULEMENT s'ils existent
        if filters:
            search_query["query"]["bool"]["filter"] = filters
            search_query["knn"]["filter"] = filters
    else:
        # Sémantique pur
        search_query = {
            "knn": {
                "field": "embedding",
                "query_vector": query_embedding,
                "k": limit,
                "num_candidates": 200
            },
            "_source": {
                "excludes": ["embedding"]
            }
        }
        
        if filters:
            search_query["knn"]["filter"] = filters
    
    try:
        results = es.search(index=ES_INDEX, body=search_query)
        return results
    except Exception as e:
        print(f"❌ Erreur recherche: {e}")
        # Fallback: recherche simple sans filtres
        try:
            simple_query = {
                "knn": {
                    "field": "embedding",
                    "query_vector": query_embedding,
                    "k": limit,
                    "num_candidates": 200
                },
                "_source": {"excludes": ["embedding"]}
            }
            return es.search(index=ES_INDEX, body=simple_query)
        except:
            return {"hits": {"hits": []}}

# ============================================================================
# FORMATAGE CONTEXTE
# ============================================================================

def format_context_compact(es_results):
    """
    Contexte COMPACT pour éviter timeout Ollama
    """
    context_parts = []
    
    for i, hit in enumerate(es_results['hits']['hits'], 1):
        src = hit['_source']
        m = src.get('metadata', {})
        met = src.get('metrics', {})
        err = src.get('errors', {})
        
        # Format ultra-compact
        doc = f"{i}. {m.get('builder', 'N/A')[:40]} | "
        doc += f"{m.get('result_status', 'N/A')} | "
        doc += f"{met.get('duration_seconds', 0):.0f}s | "
        doc += f"CPU:{met.get('cpu_user', 0):.0f}% | "
        doc += f"Err:{err.get('error_count', 0)}"
        
        context_parts.append(doc)
    
    return "\n".join(context_parts)

# ============================================================================
# LLM GENERATION (PROMPT AMÉLIORÉ)
# ============================================================================

def ask_ollama_improved(question, context, conversation_context):
    """
    Prompt RENFORCÉ contre les hallucinations
    """
    system_prompt = f"""Tu es un expert CI/CD Mozilla. 

RÈGLES STRICTES:
1. Base-toi UNIQUEMENT sur les 5 logs ci-dessous
2. Ne cite QUE des informations présentes dans ces logs
3. Si tu ne peux pas répondre précisément, DIS "Information insuffisante dans ces 5 logs"
4. Si la question demande une moyenne/statistique globale, précise "sur ces 5 logs uniquement"
5. Ne dis JAMAIS "probablement" ou "possiblement" sans preuve dans les logs
6. Réponds en 3-5 phrases maximum

LOGS (5 builds analysés):
{context}

{conversation_context}

QUESTION: {question}

RÉPONSE (basée UNIQUEMENT sur les 5 logs ci-dessus):"""

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": system_prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 200
        }
    }
    
    try:
        response = requests.post(OLLAMA_API, json=payload, timeout=180)
        return response.json().get('response', "Erreur Ollama")
    except requests.exceptions.Timeout:
        return "⏱️ Timeout Ollama (>3min). Réduisez la complexité de la question."
    except Exception as e:
        return f"❌ Erreur Ollama: {e}"

# ============================================================================
# FONCTION PRINCIPALE
# ============================================================================

def ask_question_optimized(question, search_mode="hybrid", show_details=True):
    """
    Orchestration intelligente : RAG vs Agrégation
    """
    print(f"🔍 Analyse de la question: {question}")
    
    if question.lower() in ['clear', 'reset', 'effacer']:
        clear_history()
        return "Historique effacé"
    
    query_lower = question.lower()
    
    # ========================================================================
    # ÉTAPE 1 : Détecter si agrégation nécessaire
    # ========================================================================
    agg_type = detect_aggregation_query(query_lower)
    
    if agg_type == "top_builders_errors":
        print("📊 Détection : Agrégation (top builders par erreurs)")
        answer = get_top_builders_by_errors(limit=5)
        print(f"\n🤖 RÉPONSE:\n{answer}\n")
        add_to_history(question, answer, 0)
        return answer
    
    elif agg_type == "average_duration":
        print("📊 Détection : Agrégation (durée moyenne globale)")
        answer = get_average_duration()
        print(f"\n🤖 RÉPONSE:\n{answer}\n")
        add_to_history(question, answer, 0)
        return answer
    
    # ========================================================================
    # ÉTAPE 2 : RAG classique (recherche sémantique)
    # ========================================================================
    print(f"🔍 Recherche {search_mode} sémantique...")
    use_hybrid = (search_mode == "hybrid")
    results = smart_search(question, limit=5, use_hybrid=use_hybrid)
    
    if not results['hits']['hits']:
        answer = "Aucun log pertinent trouvé. Essayez de reformuler votre question."
        print(f"❌ {answer}")
        return answer
    
    results_count = len(results['hits']['hits'])
    print(f"✅ {results_count} logs pertinents trouvés")
    
    if show_details:
        print("\n📊 Top résultats:")
        for i, hit in enumerate(results['hits']['hits'][:5], 1):
            builder = hit['_source'].get('metadata', {}).get('builder', 'N/A')
            score = hit.get('_score', 0)
            status = hit['_source'].get('metadata', {}).get('result_status', 'N/A')
            duration = hit['_source'].get('metrics', {}).get('duration_seconds', 0)
            print(f"  {i}. [{status}] {builder[:45]}... ({duration:.0f}s, score:{score:.2f})")
        print()
    
    # Contexte compact
    context = format_context_compact(results)
    conversation_context = get_conversation_context()
    
    # Ollama avec prompt amélioré
    print("🧠 Génération de la réponse (Mistral)...")
    answer = ask_ollama_improved(question, context, conversation_context)
    
    print(f"\n🤖 RÉPONSE:\n{answer}")
    print()
    
    add_to_history(question, answer, results_count)
    return answer

# ============================================================================
# STATISTIQUES
# ============================================================================

def show_stats():
    """Stats session"""
    print("\n" + "="*80)
    print("📊 STATISTIQUES DE SESSION")
    print("="*80)
    print(f"Questions posées: {len(conversation_history)}")
    if conversation_history:
        avg = sum(item['results_count'] for item in conversation_history) / len(conversation_history)
        print(f"Moyenne résultats/question: {avg:.1f} logs")
    print("="*80 + "\n")

# ============================================================================
# MODE INTERACTIF
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*80)
    print("🤖 RAG SÉMANTIQUE - Mozilla CI (VERSION AMÉLIORÉE)")
    print("="*80)
    print("\n💡 Commandes:")
    print("  - 'clear' : Effacer historique")
    print("  - 'stats' : Statistiques")
    print("  - 'quit' : Quitter")
    print("\n📝 Questions exemples:")
    print("  1. Quels sont les 5 builds les plus lents ?")
    print("  2. Pourquoi les builds échouent-ils ?")
    print("  3. Compare Windows vs Linux")
    print("  4. Quels sont les 5 builders avec le plus d'erreurs ?  [AGRÉGATION]")
    print("  5. Quelle est la durée moyenne des builds ?  [AGRÉGATION]")
    print("\n" + "="*80 + "\n")
    
    while True:
        try:
            question = input("❓ Question: ").strip()
            
            if question.lower() in ['quit', 'exit', 'q']:
                show_stats()
                print("👋 Au revoir !")
                break
            
            if question.lower() == 'stats':
                show_stats()
                continue
            
            if not question:
                continue
            
            print()
            ask_question_optimized(question, search_mode="hybrid", show_details=True)
            
        except KeyboardInterrupt:
            print("\n\n👋 Arrêt")
            show_stats()
            break
        except Exception as e:
            print(f"\n❌ Erreur: {e}")
            import traceback
            traceback.print_exc()