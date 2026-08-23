import platform

import pytest

from keymimic.single_instance import SingleInstanceGuard


@pytest.mark.skipif(platform.system() != "Windows", reason="Windows mutex required")
def test_single_instance_mutex_rejects_a_second_owner():
    first = SingleInstanceGuard("Local\\KeyMimic.Test.SingleInstance")
    second = SingleInstanceGuard("Local\\KeyMimic.Test.SingleInstance")
    try:
        assert first.acquire()
        assert not second.acquire()
    finally:
        second.release()
        first.release()
