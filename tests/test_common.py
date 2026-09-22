#!/usr/bin/env python3
"""
Unit tests for scripts/common.py shared automation and verification utilities.
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

from common import (
    TestReporter,
    check_tcp_port,
    get_repo_root,
    get_target_host,
    get_terraform_outputs,
    load_target_env,
    run_cmd,
)


class TestCommonUtilities(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_get_repo_root(self):
        """get_repo_root should return existing repository path."""
        root = get_repo_root()
        self.assertTrue(os.path.exists(root))
        self.assertTrue(os.path.isdir(root))

    def test_load_target_env(self):
        """load_target_env must correctly parse key-value pairs ignoring comments."""
        env_file = os.path.join(self.temp_dir.name, "target.env")
        with open(env_file, "w") as f:
            f.write("""# Test comment
TARGET_HOST="192.168.9.110"
TARGET_USER='admin'
TARGET_POOL=default
""")
        parsed = load_target_env(env_file)
        self.assertEqual(parsed.get("TARGET_HOST"), "192.168.9.110")
        self.assertEqual(parsed.get("TARGET_USER"), "admin")
        self.assertEqual(parsed.get("TARGET_POOL"), "default")

    def test_load_target_env_nonexistent(self):
        """load_target_env returns empty dict if file does not exist."""
        parsed = load_target_env(os.path.join(self.temp_dir.name, "nonexistent.env"))
        self.assertEqual(parsed, {})

    @patch.dict(os.environ, {"TARGET_HOST": "env-host-1"})
    def test_get_target_host_from_env(self):
        """get_target_host prioritizes TARGET_HOST environment variable."""
        self.assertEqual(get_target_host(self.temp_dir.name), "env-host-1")

    @patch.dict(os.environ, {}, clear=True)
    def test_get_target_host_from_target_env(self):
        """get_target_host extracts host from target.env when env var is absent."""
        env_file = os.path.join(self.temp_dir.name, "target.env")
        with open(env_file, "w") as f:
            f.write('TARGET_HOST="192.168.10.5"\n')
        self.assertEqual(get_target_host(self.temp_dir.name), "192.168.10.5")

    @patch.dict(os.environ, {}, clear=True)
    def test_get_target_host_from_tfvars(self):
        """get_target_host parses host from libvirt_uri in terraform.tfvars."""
        tf_dir = os.path.join(self.temp_dir.name, "terraform", "environments", "01-talos-cluster")
        os.makedirs(tf_dir, exist_ok=True)
        with open(os.path.join(tf_dir, "terraform.tfvars"), "w") as f:
            f.write('libvirt_uri = "qemu+ssh://deployer@10.20.30.40/system"\n')

        self.assertEqual(get_target_host(self.temp_dir.name), "10.20.30.40")

    @patch.dict(os.environ, {}, clear=True)
    def test_get_target_host_none_when_empty(self):
        """get_target_host returns None when no target configuration is found."""
        self.assertIsNone(get_target_host(self.temp_dir.name))

    def test_get_terraform_outputs_missing_dir(self):
        """get_terraform_outputs returns None for nonexistent environment."""
        self.assertIsNone(get_terraform_outputs("nonexistent-stage", repo_root=self.temp_dir.name))

    def test_run_cmd_success(self):
        """run_cmd successfully executes shell command and captures output."""
        res = run_cmd("echo 'hello common'", check=True, capture=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("hello common", res.stdout)

    def test_run_cmd_failure(self):
        """run_cmd handles nonzero exit code without raising unhandled exceptions."""
        res = run_cmd("false", check=False, capture=True)
        self.assertNotEqual(res.returncode, 0)

    @patch("socket.socket")
    def test_check_tcp_port_direct_success(self, mock_socket_cls):
        """check_tcp_port returns True when local socket connection succeeds."""
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 0
        mock_socket_cls.return_value = mock_sock

        self.assertTrue(check_tcp_port("127.0.0.1", 50000))

    @patch("socket.socket")
    def test_check_tcp_port_direct_fail_no_target(self, mock_socket_cls):
        """check_tcp_port returns False when direct socket fails and no remote target exists."""
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 111
        mock_socket_cls.return_value = mock_sock

        with patch("common.get_target_host", return_value=None):
            self.assertFalse(check_tcp_port("10.0.0.1", 50000))

    def test_test_reporter_lifecycle(self):
        """TestReporter records pass/fail checks and computes exit code."""
        reporter = TestReporter("Unit Test Suite")
        self.assertFalse(reporter.all_passed)  # no checks yet

        reporter.record("Check 1", True, "Detail 1")
        self.assertTrue(reporter.all_passed)
        self.assertEqual(reporter.summary(), 0)

        reporter.record("Check 2", False, "Detail 2")
        self.assertFalse(reporter.all_passed)
        self.assertEqual(reporter.summary(), 1)


if __name__ == "__main__":
    unittest.main()
