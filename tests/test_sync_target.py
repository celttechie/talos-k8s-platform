#!/usr/bin/env python3
"""
Unit tests for scripts/sync_target.py target synchronization utility.
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

import sync_target


class TestSyncTarget(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.orig_repo_root = sync_target.REPO_ROOT
        sync_target.REPO_ROOT = self.temp_dir.name

    def tearDown(self):
        sync_target.REPO_ROOT = self.orig_repo_root
        self.temp_dir.cleanup()

    @patch("sync_target.get_terraform_outputs")
    def test_sync_sandbox_target_success(self, mock_get_tf_outputs):
        """sync_sandbox_target extracts IP from tf outputs and writes target.env + tfvars."""
        mock_get_tf_outputs.return_value = {
            "sandbox_ip_address": {"value": "192.168.122.199"},
            "sandbox_libvirt_uri": {"value": "qemu+tcp://192.168.122.199/system"}
        }

        # Seed an existing target.env
        target_env_file = os.path.join(self.temp_dir.name, "target.env")
        with open(target_env_file, "w") as f:
            f.write('TARGET_HOST="192.168.9.110"\nTARGET_USER="admin"\nTARGET_SSH_KEY="/home/user/.ssh/id_ed25519"\n')

        res = sync_target.sync_sandbox_target(quiet=True)
        self.assertTrue(res)

        # Check target.env contents
        with open(target_env_file, "r") as f:
            env_content = f.read()
        self.assertIn('TARGET_HOST="192.168.122.199"', env_content)
        self.assertIn('TARGET_USER="ubuntu"', env_content)
        self.assertIn('TARGET_DEPLOYMENT_MODE="nested-sandbox"', env_content)

        # Check terraform.tfvars
        tfvars_path = os.path.join(self.temp_dir.name, "terraform", "environments", "01-talos-cluster", "terraform.tfvars")
        self.assertTrue(os.path.exists(tfvars_path))
        with open(tfvars_path, "r") as f:
            tfvars_content = f.read()
        self.assertIn('192.168.122.199', tfvars_content)
        self.assertIn('qemu+ssh://ubuntu@192.168.122.199/system', tfvars_content)

    @patch("sync_target.get_terraform_outputs")
    def test_sync_sandbox_target_missing_outputs(self, mock_get_tf_outputs):
        """sync_sandbox_target returns False gracefully when no outputs exist."""
        mock_get_tf_outputs.return_value = None
        res = sync_target.sync_sandbox_target(quiet=True)
        self.assertFalse(res)


if __name__ == "__main__":
    unittest.main()
