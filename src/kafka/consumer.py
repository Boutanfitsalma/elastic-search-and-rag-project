"""
Kafka Consumer - Consomme et indexe dans Elasticsearch
"""
from confluent_kafka import Consumer, KafkaError
from elasticsearch import Elasticsearch
import json

# Config
KAFKA_BOOTSTRAP_SERVERS = 'localhost:9092'
KAFKA_TOPIC = 'mozilla-builds'
KAFKA_GROUP_ID = 'mozilla-ci-consumer'

ES_HOST = 'localhost:9200'
ES_INDEX = 'mozilla-ci-logs'

print("📥 KAFKA CONSUMER")
print(f"Kafka: {KAFKA_BOOTSTRAP_SERVERS}")
print(f"Topic: {KAFKA_TOPIC}")
print(f"Elasticsearch: {ES_HOST}")
print(f"Index: {ES_INDEX}")
print()

# Créer consumer
conf = {
    'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
    'group.id': KAFKA_GROUP_ID,
    'auto.offset.reset': 'earliest',
    'fetch.message.max.bytes': 52428800,
    'session.timeout.ms': 30000,
    'max.poll.interval.ms': 300000,
    'request.timeout.ms': 30000
}
consumer = Consumer(conf)
consumer.subscribe([KAFKA_TOPIC])

# Connexion Elasticsearch
es = Elasticsearch([f'http://{ES_HOST}'])

# Créer index si nécessaire
try:
    if not es.indices.exists(index=ES_INDEX):
        es.indices.create(index=ES_INDEX)
        print(f"✅ Index {ES_INDEX} créé")
except:
    # Index existe déjà ou erreur mineure
    pass

print("🔄 En attente de messages...")
print()

indexed = 0

try:
    while True:
        msg = consumer.poll(1.0)
        
        if msg is None:
            continue
        
        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                continue
            print(f'❌ Erreur: {msg.error()}')
            break
        
        try:
            # Décoder message
            data = json.loads(msg.value().decode('utf-8'))
            
            # Indexer dans ES
            doc_id = msg.key().decode('utf-8')
            es.index(index=ES_INDEX, id=doc_id, document=data)
            
            indexed += 1
            
            if indexed % 100 == 0:
                print(f"📊 {indexed} documents indexés")
        
        except Exception as e:
            print(f"❌ Erreur indexation: {e}")

except KeyboardInterrupt:
    print()
    print("⏹️  Arrêt...")

finally:
    consumer.close()
    print(f"✅ Total indexé: {indexed}")