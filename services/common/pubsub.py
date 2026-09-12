"""Pub/Sub wrapper. Talks to the real service on GCP and to the Pub/Sub
emulator locally -- the google-cloud-pubsub client picks the emulator up
automatically from the PUBSUB_EMULATOR_HOST env var, so this file doesn't
need an if/else for that.
"""
import json

from google.cloud import pubsub_v1

from .config import settings

_publisher: pubsub_v1.PublisherClient | None = None


def _publisher_client() -> pubsub_v1.PublisherClient:
    global _publisher
    if _publisher is None:
        _publisher = pubsub_v1.PublisherClient()
    return _publisher


def topic_path(topic: str) -> str:
    return _publisher_client().topic_path(settings.pubsub_project_id, topic)


def publish(topic: str, payload: dict) -> str:
    client = _publisher_client()
    data = json.dumps(payload).encode("utf-8")
    future = client.publish(topic_path(topic), data)
    return future.result(timeout=10)


def ensure_topic(topic: str) -> None:
    client = _publisher_client()
    path = topic_path(topic)
    try:
        client.create_topic(request={"name": path})
    except Exception:
        pass  # already exists


def ensure_push_subscription(topic: str, subscription: str, push_endpoint: str) -> None:
    from google.cloud import pubsub_v1 as _p

    sub_client = _p.SubscriberClient()
    topic_p = topic_path(topic)
    sub_path = sub_client.subscription_path(settings.pubsub_project_id, subscription)
    try:
        sub_client.create_subscription(
            request={
                "name": sub_path,
                "topic": topic_p,
                "push_config": {"push_endpoint": push_endpoint},
                "ack_deadline_seconds": 30,
            }
        )
    except Exception:
        pass  # already exists
