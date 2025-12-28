import unittest
import json
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from config_loader import ConfigLoader
from email_detector import EmailDetector
from decision_engine import DecisionEngine

class TestCore(unittest.TestCase):
    def setUp(self):
        # Load real config for testing real logic
        self.config = ConfigLoader("domain_rules.yaml")
        self.email_rules = self.config.get_email_rules()
    
    def test_email_provider_google(self):
        detector = EmailDetector(self.email_rules)
        mx_records = [
            {'value': '10 aspmx.l.google.com.'},
            {'value': '20 alt1.aspmx.l.google.com.'}
        ]
        result = detector.detect_provider(mx_records)
        self.assertEqual(result['provider'], 'google_workspace')
        self.assertTrue(result['has_mx'])

    def test_email_provider_unknown(self):
        detector = EmailDetector(self.email_rules)
        mx_records = [
            {'value': '10 mail.random-server.com.'}
        ]
        result = detector.detect_provider(mx_records)
        self.assertEqual(result['provider'], 'unknown')
        self.assertTrue(result['has_mx'])

    def test_dmarc_present(self):
        detector = EmailDetector(self.email_rules)
        dns_snapshot = {
            'DMARC': [
                {'type': 'TXT', 'host': '_dmarc.example.com', 'value': 'v=DMARC1; p=none;', 'ttl': 3600}
            ]
        }
        result = detector.analyze_dns_snapshot(dns_snapshot)
        self.assertTrue(result['has_dmarc'])

    def test_dmarc_absent(self):
        detector = EmailDetector(self.email_rules)
        dns_snapshot = {}
        result = detector.analyze_dns_snapshot(dns_snapshot)
        self.assertFalse(result['has_dmarc'])

    def test_dmarc_multiple_records(self):
        detector = EmailDetector(self.email_rules)
        dns_snapshot = {
            'DMARC': [
                {'type': 'TXT', 'host': '_dmarc.example.com', 'value': 'v=DMARC1; p=quarantine;', 'ttl': 3600},
                {'type': 'TXT', 'host': '_dmarc.example.com', 'value': 'v=DMARC1; p=reject;', 'ttl': 3600}
            ]
        }
        result = detector.analyze_dns_snapshot(dns_snapshot)
        self.assertTrue(result['has_dmarc'])

    def test_dmarc_with_error_record(self):
        detector = EmailDetector(self.email_rules)
        dns_snapshot = {
            'DMARC': [
                {'error': 'NXDOMAIN', 'type': 'TXT'}
            ]
        }
        result = detector.analyze_dns_snapshot(dns_snapshot)
        self.assertFalse(result['has_dmarc'])

    def test_dmarc_policy_extraction_reject(self):
        detector = EmailDetector(self.email_rules)
        dns_snapshot = {
            'DMARC': [
                {'type': 'TXT', 'host': '_dmarc.example.com', 'value': 'v=DMARC1; p=reject; sp=reject; adkim=s; aspf=s;', 'ttl': 3600}
            ]
        }
        result = detector.analyze_dns_snapshot(dns_snapshot)
        self.assertTrue(result['has_dmarc'])
        self.assertEqual(result['dmarc_policy'], 'reject')

    def test_dmarc_policy_extraction_quarantine(self):
        detector = EmailDetector(self.email_rules)
        dns_snapshot = {
            'DMARC': [
                {'type': 'TXT', 'host': '_dmarc.example.com', 'value': 'v=DMARC1; p=quarantine;', 'ttl': 3600}
            ]
        }
        result = detector.analyze_dns_snapshot(dns_snapshot)
        self.assertTrue(result['has_dmarc'])
        self.assertEqual(result['dmarc_policy'], 'quarantine')

    def test_dmarc_policy_extraction_none(self):
        detector = EmailDetector(self.email_rules)
        dns_snapshot = {
            'DMARC': [
                {'type': 'TXT', 'host': '_dmarc.example.com', 'value': 'v=DMARC1; p=none;', 'ttl': 3600}
            ]
        }
        result = detector.analyze_dns_snapshot(dns_snapshot)
        self.assertTrue(result['has_dmarc'])
        self.assertEqual(result['dmarc_policy'], 'none')
    def test_dkim_via_txt(self):
        detector = EmailDetector(self.email_rules)
        dkim_records = [
            {'type': 'TXT', 'host': 'default._domainkey.example.com', 'value': 'v=DKIM1; k=rsa; p=MIGfMA0B...', 'ttl': 3600}
        ]
        result = detector.analyze_dkim(dkim_records)
        self.assertTrue(result['has_dkim'])

    def test_dkim_via_cname(self):
        detector = EmailDetector(self.email_rules)
        dkim_records = [
            {'type': 'CNAME', 'host': 'selector1._domainkey.example.com', 'value': 'selector1._domainkey.external-provider.com.', 'ttl': 3600}
        ]
        result = detector.analyze_dkim(dkim_records)
        self.assertTrue(result['has_dkim'])

    def test_dkim_absent(self):
        detector = EmailDetector(self.email_rules)
        dkim_records = []
        result = detector.analyze_dkim(dkim_records)
        self.assertFalse(result['has_dkim'])

    def test_dkim_absent_with_error_record(self):
        detector = EmailDetector(self.email_rules)
        dkim_records = [
            {'error': 'NXDOMAIN', 'type': 'TXT'}
        ]
        result = detector.analyze_dkim(dkim_records)
        self.assertFalse(result['has_dkim'])


    def test_decision_root_no_external(self):
        engine = DecisionEngine(self.config)
        intent = {
            "has_external_dependencies": False,
            "registrar_known": True,
            "comfortable_editing_dns": True
        }
        email_state = {"has_mx": False}
        dns_snapshot = {}
        
        decision = engine.evaluate("example.com", "attractwell", intent, email_state, dns_snapshot)
        
        self.assertFalse(decision['is_subdomain'])
        self.assertEqual(decision['connection_option'], 'option_1') # Nameserver
        self.assertFalse(decision['delegate_access']['recommended'])

    def test_decision_root_with_external(self):
        engine = DecisionEngine(self.config)
        intent = {
            "has_external_dependencies": True,
            "registrar_known": True,
            "comfortable_editing_dns": True
        }
        email_state = {"has_mx": True, "provider": "google_workspace"}
        dns_snapshot = {}
        
        decision = engine.evaluate("example.com", "attractwell", intent, email_state, dns_snapshot)
        
        self.assertEqual(decision['connection_option'], 'option_2') # Record level

    def test_decision_mx_detected_overrides_to_option_2(self):
        engine = DecisionEngine(self.config)
        intent = {
            "has_external_dependencies": False,
            "registrar_known": True,
            "comfortable_editing_dns": True
        }
        # Even though user says no external dependencies, MX records detected
        email_state = {"has_mx": True, "provider": "unknown"}
        dns_snapshot = {}
        
        decision = engine.evaluate("example.com", "attractwell", intent, email_state, dns_snapshot)
        
        # Should override to option_2 (record-level) to preserve email
        self.assertEqual(decision['connection_option'], 'option_2')
        # Should include warning about custom email
        warning_found = any("Custom email address detected" in w for w in decision['warnings'])
        self.assertTrue(warning_found, "Should warn about custom email when MX is detected")

    def test_strict_dmarc_without_mx_warning(self):
        engine = DecisionEngine(self.config)
        intent = {
            "has_external_dependencies": False,
            "registrar_known": True,
            "comfortable_editing_dns": True
        }
        # DMARC with reject policy but no MX
        email_state = {
            "has_mx": False,
            "has_dmarc": True,
            "dmarc_policy": "reject",
            "provider": None
        }
        dns_snapshot = {}
        
        decision = engine.evaluate("example.com", "attractwell", intent, email_state, dns_snapshot)
        
        # Should have warning about defensive DMARC
        warning_found = any("p=reject" in w and "no MX records" in w for w in decision['warnings'])
        self.assertTrue(warning_found, "Should warn about strict DMARC without MX")

    def test_subdomain_logic(self):
        engine = DecisionEngine(self.config)
        intent = {} # logic shouldn't care about intent for subdomains per rules logic
        email_state = {"has_mx": False}
        dns_snapshot = {}
        
        decision = engine.evaluate("shop.example.com", "getoiling", intent, email_state, dns_snapshot)
        
        self.assertTrue(decision['is_subdomain'])
        self.assertEqual(decision['connection_option'], 'cname_only')

if __name__ == '__main__':
    unittest.main()
