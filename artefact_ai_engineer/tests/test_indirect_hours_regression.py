"""S1 indirect opening-hours regression: no generic offer to look up policy."""
from music_store.application.agent import _opening_hours_answer
from music_store.application.policies import find_policies


def test_s1_weekend_after_lunch():
    result = _opening_hours_answer('could i stop by after lunch on the weekend?', find_policies)
    assert '1:00 PM' in result and 'Sundays' in result
    assert 'look up' not in result


def test_s1b_saturday_at_two():
    result = _opening_hours_answer('i am planning to visit your shop on saturday around 2 in the afternoon.', find_policies)
    assert '1:00 PM' in result and 'closed' in result


def test_no_unrelated_weekend_trigger():
    assert _opening_hours_answer('do you have guitar deals this weekend?', find_policies) is None


def test_unverified_policy_cannot_authorize_hours():
    assert _opening_hours_answer('could i stop by after lunch on the weekend?', lambda _: []) is None
