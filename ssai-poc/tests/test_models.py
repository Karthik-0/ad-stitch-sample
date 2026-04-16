import unittest

from models import AdPod, AdState, ConditionedAd, Session, TrackingEvent


class ModelsTestCase(unittest.TestCase):
    def test_tracking_event_defaults(self) -> None:
        event = TrackingEvent(event="start", url="https://example.test")
        self.assertFalse(event.fired)

    def test_session_defaults(self) -> None:
        session = Session(session_id="s1", created_at=1.0, content_id="demo")
        self.assertEqual(session.ad_state, AdState.NONE)
        self.assertIsNone(session.pending_pod)
        self.assertIsNone(session.active_pod)
        self.assertEqual(session.pod_history, [])

    def test_ad_pod_segments_default(self) -> None:
        ad = ConditionedAd(creative_id="c1", duration_sec=30.0)
        pod = AdPod(pod_id="p1", ads=[ad], total_duration=30.0)
        self.assertEqual(pod.segments_served, {})


if __name__ == "__main__":
    unittest.main()
