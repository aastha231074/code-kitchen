"""Creates the topics (and, for local dev, a pull subscription used by the
pubsub_pull_relay sidecar) against the Pub/Sub emulator. Real GCP topics and
push subscriptions are created by Terraform instead -- see
infra/terraform/pubsub.tf.
"""
import sys
import time

sys.path.insert(0, "/app")

from services.common.config import settings
from services.common.pubsub import ensure_topic


def main():
    for topic in (settings.topic_ingestion_trigger, settings.topic_jobs_raw, settings.topic_jobs_raw_dlq):
        ensure_topic(topic)
        print(f"[bootstrap] ensured topic {topic}")

    from google.cloud import pubsub_v1

    sub_client = pubsub_v1.SubscriberClient()
    project = settings.pubsub_project_id
    topic_path = sub_client.topic_path(project, settings.topic_jobs_raw)
    sub_path = sub_client.subscription_path(project, "jobs-raw-pull-relay")
    try:
        sub_client.create_subscription(request={"name": sub_path, "topic": topic_path})
        print("[bootstrap] ensured pull subscription jobs-raw-pull-relay")
    except Exception as exc:  # noqa: BLE001
        print(f"[bootstrap] subscription probably already exists: {exc}")


if __name__ == "__main__":
    # small retry loop -- the emulator container may still be starting
    for attempt in range(10):
        try:
            main()
            break
        except Exception as exc:  # noqa: BLE001
            print(f"[bootstrap] attempt {attempt + 1} failed: {exc}")
            time.sleep(2)
