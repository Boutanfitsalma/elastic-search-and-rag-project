"""
Kafka Producer - Envoie les logs parsés vers Kafka
"""
from confluent_kafka import Producer
import json
from pathlib import Path
import time

# Config
KAFKA_BOOTSTRAP_SERVERS = 'localhost:9092'
KAFKA_TOPIC = 'mozilla-builds'
PARSED_DIR = Path(__file__).parent.parent.parent / "data" / "parsed"

print("📤 KAFKA PRODUCER")
print(f"Kafka: {KAFKA_BOOTSTRAP_SERVERS}")
print(f"Topic: {KAFKA_TOPIC}")
print(f"Source: {PARSED_DIR}")
print()

# Créer producer
conf = {
    'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
    'client.id': 'mozilla-ci-producer',
    'message.max.bytes': 52428800,  # 10MB
    'compression.type': 'gzip'
}

print("⏳ Attente de Kafka...")
time.sleep(10)  # Attendre que Kafka soit prêt
print("✅ Connexion à Kafka...")

producer = Producer(conf)

def delivery_report(err, msg):
    """Callback pour confirmer envoi"""
    if err:
        print(f'❌ Erreur: {err}')

# Trouver tous les JSON
all_json = list(PARSED_DIR.rglob("*.json"))
total = len(all_json)
print(f"📄 {total:,} fichiers JSON trouvés")
print()

# Envoyer
sent = 0
for i, json_file in enumerate(all_json, 1):
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # --- ENRICHISSEMENT À LA VOLÉE ---
        if 'metrics' in data:
            m = data['metrics']
            # On remplit les champs qui étaient à 0 avec les vraies valeurs
            if 'timing' in m:
                data['metrics']['duration_seconds'] = m['timing'].get('total_duration', 0)
            if 'cpu' in m:
                data['metrics']['cpu_user'] = m['cpu'].get('user', 0)
            if 'io' in m:
                data['metrics']['io_read'] = m['io'].get('read_bytes', 0)
        # --------------------------------
        # Envoyer vers Kafka
        producer.produce(
            KAFKA_TOPIC,
            key=json_file.stem.encode('utf-8'),
            value=json.dumps(data).encode('utf-8'),
            callback=delivery_report
        )
        
        sent += 1
        
        if i % 100 == 0:
            producer.flush()
            print(f"[{i}/{total}] {sent} envoyés")
        
        # Simuler temps réel (optionnel)
        # time.sleep(0.01)
    
    except Exception as e:
        print(f"❌ Erreur {json_file.name}: {e}")

# Flush final
producer.flush()

print()
print(f"✅ Terminé: {sent}/{total} messages envoyés")