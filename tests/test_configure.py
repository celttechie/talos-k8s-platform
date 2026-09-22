#!/usr/bin/env python3
"""
Unit tests for scripts/configure.py SSH configuration and key management functions.
"""

import os
import stat
import sys
import tempfile
import unittest

# Ensure scripts directory is on sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

from unittest.mock import patch

from configure import (
    parse_ssh_config,
    ensure_ssh_key,
    append_ssh_config_entry,
    discover_ssh_keys,
    prompt_value,
)


class TestConfigureSSH(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_parse_ssh_config_missing_or_empty_alias(self):
        """parse_ssh_config must raise ValueError if host_alias is omitted or whitespace."""
        with self.assertRaises(ValueError):
            parse_ssh_config("")
        with self.assertRaises(ValueError):
            parse_ssh_config(None)
        with self.assertRaises(ValueError):
            parse_ssh_config("   ")

    def test_parse_ssh_config_file_not_found(self):
        """parse_ssh_config must raise FileNotFoundError if ssh_config_path does not exist."""
        non_existent_file = os.path.join(self.temp_dir.name, "nonexistent_config")
        with self.assertRaises(FileNotFoundError):
            parse_ssh_config("t5600", ssh_config_path=non_existent_file)

    def test_parse_ssh_config_alias_not_found(self):
        """parse_ssh_config must raise KeyError if the host alias is not present in ssh config."""
        config_path = os.path.join(self.temp_dir.name, "config")
        with open(config_path, "w") as f:
            f.write("""Host other-host
    HostName 10.0.0.50
    User admin
    IdentityFile ~/.ssh/id_other
""")
        with self.assertRaises(KeyError):
            parse_ssh_config("t5600", ssh_config_path=config_path)

    def test_parse_ssh_config_success(self):
        """parse_ssh_config must accurately extract HostName, User, and IdentityFile."""
        config_path = os.path.join(self.temp_dir.name, "config")
        with open(config_path, "w") as f:
            f.write("""Host bastion
    HostName 10.10.10.1
    User bastionuser

Host t5600
    HostName 192.168.9.110
    User testuser
    IdentityFile ~/.ssh/test_key

Host node-01
    HostName 192.168.9.111
""")
        result = parse_ssh_config("t5600", ssh_config_path=config_path)
        self.assertEqual(result["host"], "192.168.9.110")
        self.assertEqual(result["user"], "testuser")
        self.assertEqual(result["key"], os.path.expanduser("~/.ssh/test_key"))

    def test_parse_ssh_config_multi_alias_line(self):
        """parse_ssh_config should match host alias on multi-alias Host definitions."""
        config_path = os.path.join(self.temp_dir.name, "config")
        with open(config_path, "w") as f:
            f.write("""Host lab-host t5600 dell-server
    HostName 192.168.9.120
    User myuser
    IdentityFile ~/.ssh/id_rsa
""")
        result = parse_ssh_config("t5600", ssh_config_path=config_path)
        self.assertEqual(result["host"], "192.168.9.120")
        self.assertEqual(result["user"], "myuser")

    def test_append_ssh_config_entry_new_file(self):
        """append_ssh_config_entry must create the file with 0600 permissions and write the block."""
        config_path = os.path.join(self.temp_dir.name, "ssh", "config")
        append_ssh_config_entry(
            host_alias="t5600",
            host="192.168.9.150",
            user="talosadmin",
            key_path="/tmp/test_key",
            ssh_config_path=config_path,
        )

        self.assertTrue(os.path.exists(config_path))
        file_mode = stat.S_IMODE(os.stat(config_path).st_mode)
        self.assertEqual(file_mode, 0o600)

        result = parse_ssh_config("t5600", ssh_config_path=config_path)
        self.assertEqual(result["host"], "192.168.9.150")
        self.assertEqual(result["user"], "talosadmin")
        self.assertEqual(result["key"], "/tmp/test_key")

    def test_append_ssh_config_entry_existing_file(self):
        """append_ssh_config_entry must preserve existing blocks when appending a new host."""
        config_path = os.path.join(self.temp_dir.name, "config")
        with open(config_path, "w") as f:
            f.write("""Host initial-host
    HostName 10.0.0.1
    User root
""")
        append_ssh_config_entry(
            host_alias="t5600",
            host="192.168.9.160",
            user="deployer",
            key_path="/tmp/deploy_key",
            ssh_config_path=config_path,
        )

        # Both hosts must be parseable
        init_res = parse_ssh_config("initial-host", ssh_config_path=config_path)
        self.assertEqual(init_res["host"], "10.0.0.1")

        t5600_res = parse_ssh_config("t5600", ssh_config_path=config_path)
        self.assertEqual(t5600_res["host"], "192.168.9.160")
        self.assertEqual(t5600_res["user"], "deployer")

    def test_ensure_ssh_key_generation(self):
        """ensure_ssh_key must generate an ed25519 key pair with 0600 permissions if not present."""
        key_path = os.path.join(self.temp_dir.name, "test_id_ed25519")
        priv_path, pub_path = ensure_ssh_key(key_path)

        self.assertTrue(os.path.exists(priv_path))
        self.assertTrue(os.path.exists(pub_path))
        self.assertEqual(pub_path, key_path + ".pub")

        file_mode = stat.S_IMODE(os.stat(priv_path).st_mode)
        self.assertEqual(file_mode, 0o600)

        # Calling again on existing key should return existing paths without re-generating
        priv2, pub2 = ensure_ssh_key(key_path)
        self.assertEqual(priv2, priv_path)
        self.assertEqual(pub2, pub_path)

    def test_prompt_value_non_interactive_default(self):
        """prompt_value in non-interactive environment returns default value."""
        with patch("sys.stdin.isatty", return_value=False):
            val = prompt_value("Test Prompt", "default_123")
            self.assertEqual(val, "default_123")

    def test_prompt_value_interactive_input(self):
        """prompt_value in interactive environment returns entered value."""
        with patch("sys.stdin.isatty", return_value=True), patch("builtins.input", return_value="custom_value"):
            val = prompt_value("Test Prompt", "default_123")
            self.assertEqual(val, "custom_value")


if __name__ == "__main__":
    unittest.main()
