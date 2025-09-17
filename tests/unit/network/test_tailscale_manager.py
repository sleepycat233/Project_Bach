#!/usr/bin/env python3.11
"""Unit tests for the Tailscale networking helpers."""

import json
import os
import subprocess
import tempfile
import shutil
import unittest
from unittest.mock import MagicMock, patch

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from network.tailscale_manager import TailscaleManager


class TestTailscaleManager(unittest.TestCase):
    """Fine-grained tests for TailscaleManager behaviour."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config = {
            'machine_name': 'project-bach-test',
            'timeout': 10
        }

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('subprocess.run')
    def test_check_tailscale_installed_true(self, mock_run):
        mock_result = MagicMock(returncode=0, stdout='tailscale version 1.60.0')
        mock_run.return_value = mock_result

        manager = TailscaleManager(self.config)
        self.assertTrue(manager.check_tailscale_installed())

    @patch('subprocess.run')
    def test_check_tailscale_installed_false_when_missing(self, mock_run):
        mock_run.side_effect = FileNotFoundError('tailscale not found')

        manager = TailscaleManager(self.config)
        self.assertFalse(manager.check_tailscale_installed())

    @patch('subprocess.run')
    def test_check_status_connected(self, mock_run):
        mock_status = {
            'BackendState': 'Running',
            'TailscaleIPs': ['100.64.0.1'],
            'Self': {'ID': 'n1234'}
        }
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(mock_status))

        manager = TailscaleManager(self.config)
        status = manager.check_status()

        self.assertTrue(status['connected'])
        self.assertEqual(status['node_id'], 'n1234')

    @patch('subprocess.run')
    def test_check_status_handles_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr='error')

        manager = TailscaleManager(self.config)
        status = manager.check_status()

        self.assertFalse(status['connected'])
        self.assertEqual(status['error'], 'error')

    @patch.dict(os.environ, {'TAILSCALE_AUTH_KEY': 'tskey-test'}, clear=True)
    @patch('subprocess.run')
    def test_connect_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout='Logged in')

        manager = TailscaleManager(self.config)
        self.assertTrue(manager.connect())

    @patch('subprocess.run')
    @patch.dict(os.environ, {}, clear=True)
    def test_connect_skips_without_auth_key(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout='tailscale version 1.60.0')
        manager = TailscaleManager(self.config)
        self.assertFalse(manager.connect())
        self.assertEqual(mock_run.call_count, 1)
        self.assertEqual(mock_run.call_args[0][0][:2], ['tailscale', 'version'])

    @patch.dict(os.environ, {'TAILSCALE_AUTH_KEY': 'tskey-test'}, clear=True)
    @patch('subprocess.run')
    def test_connect_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr='invalid key')

        manager = TailscaleManager(self.config)
        self.assertFalse(manager.connect())

    @patch('subprocess.run')
    def test_get_network_info_returns_peers(self, mock_run):
        mock_status = {
            'Peer': {
                'n1': {
                    'ID': 'n1',
                    'HostName': 'mac-mini',
                    'DNSName': 'mac-mini.tailnet',
                    'OS': 'macOS',
                    'TailscaleIPs': ['100.64.0.2'],
                    'Online': True
                },
                'n2': {
                    'ID': 'n2',
                    'HostName': 'ipad',
                    'DNSName': 'ipad.tailnet',
                    'OS': 'iOS',
                    'TailscaleIPs': ['100.64.0.3'],
                    'Online': False
                }
            }
        }
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(mock_status))

        manager = TailscaleManager(self.config)
        info = manager.get_network_info()

        self.assertEqual(info['network_status'], 'active')
        self.assertEqual(len(info['peers']), 2)
        self.assertTrue(info['peers'][0]['online'])

    @patch('subprocess.run')
    def test_get_network_info_handles_errors(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr='failure')

        manager = TailscaleManager(self.config)
        info = manager.get_network_info()

        self.assertEqual(info['network_status'], 'error')
        self.assertEqual(info['peers'], [])

    @patch('subprocess.run')
    def test_ping_peer_returns_latency(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout='pong time=15.5ms')

        manager = TailscaleManager(self.config)
        latency = manager.ping_peer('100.64.0.2')

        self.assertAlmostEqual(latency, 15.5)

    @patch('subprocess.run')
    def test_ping_peer_failure_returns_none(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr='timeout')

        manager = TailscaleManager(self.config)
        self.assertIsNone(manager.ping_peer('100.64.0.3'))

    @patch('subprocess.run')
    def test_ping_peer_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=['tailscale', 'ping'], timeout=5)

        manager = TailscaleManager(self.config)
        self.assertIsNone(manager.ping_peer('100.64.0.4'))


if __name__ == '__main__':
    unittest.main()
