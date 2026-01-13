"""
Consumer SÉMANTIQUE FINAL - Avec timeouts corrects
"""
from confluent_kafka import Consumer, KafkaError
from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer
import json
from datetime import datetime
import time

# Config
KAFKA_BOOTSTRAP_SERVERS = 'localhost:9092'
KAFKA_TOPIC = 'mozilla-builds'
KAFKA_GROUP_ID = 'mozilla-semantic-2025-01-11'  # Unique !

ES_HOST = 'localhost:9200'
ES_INDEX_SEMANTIC = 'mozilla-ci-logs-semantic-v2'

MAX_EMPTY_POLLS = 10
POLL_TIMEOUT = 1.0

print("🔥 CONSUMER SÉMANTIQUE FINAL (timeouts corrigés)")
print(f"Kafka: {KAFKA_BOOTSTRAP_SERVERS}")
print(f"Topic: {KAFKA_TOPIC}")
print(f"Group ID: {KAFKA_GROUP_ID}")
print(f"Index ES: {ES_INDEX_SEMANTIC}")
print()

# Modèle
print("🧠 Chargement modèle...")
model = SentenceTransformer('all-MiniLM-L6-v2')
print("✅ Modèle chargé\n")

# Consumer
conf = {
    'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
    'group.id': KAFKA_GROUP_ID,
    'auto.offset.reset': 'earliest',
    'enable.auto.commit': True,
    'auto.commit.interval.ms': 1000,
    'fetch.message.max.bytes': 52428800,
    'session.timeout.ms': 30000,
    'max.poll.interval.ms': 300000,
}
consumer = Consumer(conf)
consumer.subscribe([KAFKA_TOPIC])

# ✅ ELASTICSEARCH AVEC TIMEOUT AUGMENTÉ
es = Elasticsearch(
    [f'http://{ES_HOST}'],
    request_timeout=60,      # ← 60 secondes au lieu de 10 !
    max_retries=3,
    retry_on_timeout=True
)

# Mapping
index_mapping = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,  # Pas de replicas pour aller plus vite
        "refresh_interval": "30s"  # Refresh moins fréquent
    },
    "mappings": {
        "properties": {
            "metadata": {
                "properties": {
                    "builder": {"type": "keyword"},
                    "slave": {"type": "keyword"},
                    "result_status": {"type": "keyword"},
                    "result_code": {"type": "integer"},
                    "buildid": {"type": "keyword"},
                    "builduid": {"type": "keyword"},
                    "revision": {"type": "keyword"},
                    "starttime": {"type": "double"},
                    "starttime_iso": {"type": "date"}
                }
            },
            "errors": {"type": "object"},
            "metrics": {
                "properties": {
                    "duration_seconds": {"type": "float"},
                    "cpu_user": {"type": "float"},
                    "io_read": {"type": "long"}
                }
            },
            "context": {
                "properties": {
                    "platform": {"type": "keyword"},
                    "test_type": {"type": "keyword"},
                    "architecture": {"type": "keyword"}
                }
            },
            "raw": {"type": "object"},
            "text_content": {"type": "text"},
            "embedding": {
                "type": "dense_vector",
                "dims": 384,
                "index": True,
                "similarity": "cosine"
            }
        }
    }
}

# Créer index
try:
    if es.indices.exists(index=ES_INDEX_SEMANTIC):
        user_input = input(f"⚠️  Index {ES_INDEX_SEMANTIC} existe. Supprimer ? (o/n): ")
        if user_input.lower() == 'o':
            es.indices.delete(index=ES_INDEX_SEMANTIC)
            print("🗑️  Index supprimé")
        else:
            print("✅ Utilisation de l'index existant")
    
    if not es.indices.exists(index=ES_INDEX_SEMANTIC):
        es.indices.create(index=ES_INDEX_SEMANTIC, body=index_mapping)
        print(f"✅ Index créé\n")
except Exception as e:
    print(f"❌ Erreur index: {e}")
    import traceback
    traceback.print_exc()

def fix_timestamps(data):
    """Corrige les timestamps"""
    if 'metadata' in data:
        m = data['metadata']
        
        if 'starttime' in m and isinstance(m['starttime'], str):
            try:
                m['starttime'] = float(m['starttime'])
            except:
                m['starttime'] = None
        
        if 'starttime_iso' in m and m['starttime_iso']:
            iso = m['starttime_iso']
            if 'T' not in iso:
                m['starttime_iso'] = None
        
        if m.get('starttime') and not m.get('starttime_iso'):
            try:
                dt = datetime.fromtimestamp(m['starttime'])
                m['starttime_iso'] = dt.isoformat()
            except:
                pass
    
    return data

def create_text_for_embedding(data):
    """Texte pour embedding"""
    parts = []
    
    if 'metadata' in data:
        m = data['metadata']
        parts.append(f"Builder: {m.get('builder', '')}")
        parts.append(f"Status: {m.get('result_status', '')}")
    
    if 'errors' in data and data['errors'].get('errors_list'):
        errors = data['errors']['errors_list'][:3]
        error_texts = [e.get('line', '') for e in errors]
        parts.append(f"Errors: {' | '.join(error_texts)}")
    
    if 'context' in data:
        c = data['context']
        parts.append(f"Platform: {c.get('platform', '')}")
        parts.append(f"Test: {c.get('test_type', '')}")
    
    if 'metrics' in data:
        parts.append(f"Duration: {data['metrics'].get('duration_seconds', 0)}s")
    
    return " | ".join(filter(None, parts))

# Variables
indexed = 0
errors = 0
duplicates = 0
empty_polls = 0
processed_ids = set()

print("📄 Démarrage...\n")
start_time = time.time()

try:
    while True:
        msg = consumer.poll(POLL_TIMEOUT)
        
        if msg is None:
            empty_polls += 1
            if empty_polls % 5 == 1:  # Afficher tous les 5
                print(f"⏸️  Poll vide ({empty_polls}/{MAX_EMPTY_POLLS})")
            
            if empty_polls >= MAX_EMPTY_POLLS:
                print(f"\n🛑 Arrêt après {MAX_EMPTY_POLLS} polls vides")
                break
            
            continue
        
        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                empty_polls += 1
                if empty_polls >= MAX_EMPTY_POLLS:
                    break
                continue
            else:
                print(f'❌ Kafka error: {msg.error()}')
                break
        
        empty_polls = 0
        
        try:
            doc_id = msg.key().decode('utf-8')
            
            if doc_id in processed_ids:
                duplicates += 1
                if duplicates <= 5:  # Montrer les 5 premiers
                    print(f"⚠️  Duplicate: {doc_id}")
                continue
            
            processed_ids.add(doc_id)
            
            data = json.loads(msg.value().decode('utf-8'))
            data = fix_timestamps(data)
            
            text_content = create_text_for_embedding(data)
            embedding = model.encode(text_content).tolist()
            
            data['text_content'] = text_content
            data['embedding'] = embedding
            
            # ✅ INDEXER AVEC RETRY
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    es.index(index=ES_INDEX_SEMANTIC, id=doc_id, document=data)
                    indexed += 1
                    break
                except Exception as e:
                    if attempt < max_retries - 1:
                        print(f"⚠️  Retry {attempt+1}/{max_retries} pour {doc_id}")
                        time.sleep(2)  # Attendre 2s avant retry
                    else:
                        raise  # Lever l'erreur au dernier essai
            
            if indexed % 50 == 0:
                elapsed = time.time() - start_time
                rate = indexed / elapsed if elapsed > 0 else 0
                print(f"📊 {indexed} indexés | {duplicates} dup | {rate:.1f} docs/s")
        
        except Exception as e:
            print(f"❌ Erreur: {e}")
            errors += 1
            if errors > 10:
                print("🛑 Trop d'erreurs, arrêt")
                break

except KeyboardInterrupt:
    print("\n⏹️  Arrêt manuel\n")

finally:
    consumer.close()
    
    elapsed = time.time() - start_time
    
    print("\n" + "="*80)
    print("📊 RAPPORT FINAL")
    print("="*80)
    print(f"✅ Documents indexés: {indexed}")
    print(f"⚠️  Duplicates évités: {duplicates}")
    print(f"❌ Erreurs: {errors}")
    print(f"⏱️  Temps: {elapsed:.1f}s ({indexed/elapsed if elapsed > 0 else 0:.1f} docs/s)")
    print(f"📁 Index: {ES_INDEX_SEMANTIC}")
    print("="*80)
    
    try:
        # Forcer un refresh
        es.indices.refresh(index=ES_INDEX_SEMANTIC)
        count = es.count(index=ES_INDEX_SEMANTIC)
        print(f"\n✅ ES count: {count['count']} documents")
        
        if count['count'] != indexed:
            print(f"⚠️  Différence: indexés={indexed}, ES={count['count']}")
    except Exception as e:
        print(f"❌ Vérification ES: {e}")