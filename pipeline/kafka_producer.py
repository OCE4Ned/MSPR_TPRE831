import csv
import json
import os
import time
from pathlib import Path

from kafka import KafkaProducer


BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = os.getenv("KAFKA_TOPIC", "industrial.raw")
SOURCE_DIR = Path(os.getenv("SOURCE_DIR", "data/raw"))
SEND_DELAY_SECONDS = float(os.getenv("SEND_DELAY_SECONDS", "0.02"))


def iter_dirty_rows():
    for csv_path in sorted(SOURCE_DIR.glob("*_sale.csv")):
        source_system = csv_path.stem.replace("_sale", "")
        with csv_path.open(newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row_number, row in enumerate(reader, start=1):
                yield {
                    "source_file": csv_path.name,
                    "source_system": source_system,
                    "row_number": row_number,
                    "ingestion_mode": "kafka_to_datalake_raw",
                    "payload": row,
                }


def main():
    producer = KafkaProducer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        value_serializer=lambda value: json.dumps(value, ensure_ascii=False).encode("utf-8"),
        key_serializer=lambda value: value.encode("utf-8"),
    )

    sent = 0
    for event in iter_dirty_rows():
        producer.send(TOPIC, key=event["source_system"], value=event)
        sent += 1
        if SEND_DELAY_SECONDS:
            time.sleep(SEND_DELAY_SECONDS)

    producer.flush()
    producer.close()
    print(f"{sent} evenements sales envoyes dans Kafka topic={TOPIC}")


if __name__ == "__main__":
    main()
