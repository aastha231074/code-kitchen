"""Local-dev-only shim: the Pub/Sub emulator doesn't support push
subscriptions, only pull. This pulls from jobs-raw-pull-relay and forwards
each message to process-worker's HTTP endpoint wrapped in the same envelope
shape a real Pub/Sub push subscription would send -- so process-worker's
code is identical between docker-compose and Cloud Run. Not deployed to
GCP; Terraform wires a real push subscription there instead.
"""
import base64
import json
import sys
import time

import requests

sys.path.insert(0, "/app")

from google.cloud import pubsub_v1

from services.common.config import settings

PROCESS_WORKER_URL = "http://process-worker:8080/"


def run():
    client = pubsub_v1.SubscriberClient()
    sub_path = client.subscription_path(settings.pubsub_project_id, "jobs-raw-pull-relay")

    print("[pubsub-relay] polling jobs-raw-pull-relay ...")
    while True:
        try:
            resp = client.pull(request={"subscription": sub_path, "max_messages": 10}, timeout=10)
        except Exception as exc:  # noqa: BLE001
            print(f"[pubsub-relay] pull failed (retrying): {exc}")
            time.sleep(3)
            continue

        for msg in resp.received_messages:
            envelope = {"message": {"data": base64.b64encode(msg.message.data).decode("utf-8")}}
            try:
                r = requests.post(PROCESS_WORKER_URL, json=envelope, timeout=30)
                r.raise_for_status()
                client.acknowledge(request={"subscription": sub_path, "ack_ids": [msg.ack_id]})
            except Exception as exc:  # noqa: BLE001
                print(f"[pubsub-relay] delivery failed, will redeliver: {exc}")

        if not resp.received_messages:
            time.sleep(1)


if __name__ == "__main__":
    run()
