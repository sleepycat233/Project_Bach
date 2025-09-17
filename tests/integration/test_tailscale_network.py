#!/usr/bin/env python3.11
"""Integration-style tests for Tailscale networking helpers."""

import json
import os
import subprocess
import unittest
from unittest.mock import MagicMock, patch

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from network.tailscale_manager import TailscaleManager


class TestTailscaleNetworkIntegration(unittest.TestCase):
    """Simulate an end-to-end Tailscale interaction using mocks."""

    def setUp(self):
        self.config = {
            'machine_name': 'project-bach-integration',
            'timeout': 15
        }

    def _make_run_side_effect(self):
        """Provide a stateful side effect for subprocess.run to emulate tailscale CLI."""
        state = {'connected': False}

        def fake_run(cmd, capture_output=True, text=True, timeout=None):
            if cmd[:2] == ['tailscale', 'version']:
                return MagicMock(returncode=0, stdout='tailscale version 1.60.0')

            if cmd[:2] == ['tailscale', 'up']:
                state['connected'] = True
                return MagicMock(returncode=0, stdout='Logged in')

            if cmd[:3] == ['tailscale', 'status', '--json']:
                if not state['connected']:
                    payload = {
                        'BackendState': 'Stopped',
                        'TailscaleIPs': [],
                        'Self': None,
                        'Peer': {}
                    }
                    return MagicMock(returncode=0, stdout=json.dumps(payload))

                payload = {
                    'BackendState': 'Running',
                    'TailscaleIPs': ['100.64.0.1'],
                    'Self': {'ID': 'n-self'},
                    'Peer': {
                        'n-peer-1': {
                            'ID': 'n-peer-1',
                            'HostName': 'dev-mac',
                            'DNSName': 'dev-mac.tailnet',
                            'OS': 'macOS',
                            'TailscaleIPs': ['100.64.0.2'],
                            'Online': True
                        },
                        'n-peer-2': {
                            'ID': 'n-peer-2',
                            'HostName': 'ipad',
                            'DNSName': 'ipad.tailnet',
                            'OS': 'iOS',
                            'TailscaleIPs': ['100.64.0.3'],
                            'Online': True
                        }
                    }
                }
                return MagicMock(returncode=0, stdout=json.dumps(payload))

            if cmd[:2] == ['tailscale', 'ping']:
                peer_ip = cmd[-1]
                if peer_ip == '100.64.0.2':
                    return MagicMock(returncode=0, stdout='pong time=9.81ms')
                return MagicMock(returncode=1, stderr='peer not reachable')

            raise ValueError(f'Unexpected command: {cmd}')

        return fake_run

    @patch.dict(os.environ, {'TAILSCALE_AUTH_KEY': 'tskey-integration'}, clear=True)
    @patch('subprocess.run')
    def test_full_connection_flow(self, mock_run):
        mock_run.side_effect = self._make_run_side_effect()

        manager = TailscaleManager(self.config)

        self.assertTrue(manager.check_tailscale_installed())

        status_before = manager.check_status()
        self.assertFalse(status_before['connected'])

        self.assertTrue(manager.connect())

        status_after = manager.check_status()
        self.assertTrue(status_after['connected'])
        self.assertEqual(status_after['node_id'], 'n-self')

        network_info = manager.get_network_info()
        self.assertEqual(network_info['network_status'], 'active')
        self.assertEqual(len(network_info['peers']), 2)

        latency = manager.ping_peer('100.64.0.2')
        self.assertAlmostEqual(latency, 9.81)

        self.assertIsNone(manager.ping_peer('100.64.0.99'))

    @patch('subprocess.run')
    def test_connect_failure_flow(self, mock_run):
        def failure_run(cmd, capture_output=True, text=True, timeout=None):
            if cmd[:2] == ['tailscale', 'up']:
                return MagicMock(returncode=1, stderr='auth denied')
            return MagicMock(returncode=1, stderr='not connected')

        mock_run.side_effect = failure_run

        os.environ.pop('TAILSCALE_AUTH_KEY', None)
        os.environ['TAILSCALE_AUTH_KEY'] = 'tskey-invalid'

        manager = TailscaleManager(self.config)
        self.assertFalse(manager.connect())

        status = manager.check_status()
        self.assertFalse(status['connected'])


if __name__ == '__main__':
    unittest.main()
