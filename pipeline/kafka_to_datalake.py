import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from kafka import KafkaConsumer


BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = os.getenv("KAFKA_TOPIC", "industrial.raw")
GROUP_ID = os.getenv("KAFKA_GROUP_ID", "datalake-writer")
DATALAKE_RAW_DIR = Path(os.getenv("DATALAKE_RAW_DIR", "data/datalake/raw"))
MAX_IDLE_SECONDS = int(os.getenv("MAX_IDLE_SECONDS", "20"))


def main():
    DATALAKE_RAW_DIR.mkdir(parents=True, exist_ok=True)
    output_path = DATALAKE_RAW_DIR / f"industrial_raw_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.jsonl"

    consumer = KafkaConsumer(
        TOPIC,
        bootstrap_servers=BOOTSTRAP_SERVERS,
        group_id=GROUP_ID,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda raw: json.loads(raw.decode("utf-8")),
        consumer_timeout_ms=1000,
    )

    written = 0
    last_message_at = time.monotonic()
    with output_path.open("a", encoding="utf-8") as file:
        while True:
            received = False
            for message in consumer:
                event = message.value
                event["datalake_ingested_at"] = datetime.now(timezone.utc).isoformat()
                file.write(json.dumps(event, ensure_ascii=False) + "\n")
                written += 1
                received = True
                last_message_at = time.monotonic()

            file.flush()
            if not received and time.monotonic() - last_message_at >= MAX_IDLE_SECONDS:
                break

    consumer.close()
    print(f"{written} evenements ecrits dans le datalake: {output_path}")


if __name__ == "__main__":
    main()
