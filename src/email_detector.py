class EmailDetector:
    def __init__(self, email_rules):
        self.rules = email_rules

    def detect_provider(self, mx_records):
        if not mx_records:
            return {'has_mx': False, 'provider': None}

        mx_values = [r['value'].lower() for r in mx_records]
        
        # Check against fingerprints
        providers = self.rules.get('email_providers', {})
        for key, provider in providers.items():
            if key == 'unknown': continue
            
            for pattern in provider.get('mx_patterns', []):
                pattern_lower = pattern.lower()
                for mx in mx_values:
                    if pattern_lower in mx:
                        return {'has_mx': True, 'provider': key, 'display_name': provider['display_name']}

        return {'has_mx': True, 'provider': 'unknown', 'display_name': 'Unknown Provider'}

    def analyze_txt_records(self, txt_records):
        data = {
            'has_spf': False,
            'spf_record': None,
            'has_dmarc': False,
            'dmarc_record': None
        }
        
        spf_id = self.rules.get('spf_identifier', 'v=spf1')

        for r in txt_records:
            val = r['value']
            if spf_id in val:
                data['has_spf'] = True
                data['spf_record'] = val
            if "v=DKIM1" in val:
                data['has_dkim'] = True
                data['dkim_record'] = val
                
        return data

    def analyze_dkim(self, dkim_records):
        data = {'has_dkim': False, 'dkim_detected': False}
        
        if not dkim_records:
            return data
        
        for record in dkim_records:
            if 'error' in record:
                continue
            
            record_type = record.get('type', '')
            value = record.get('value', '')
            
            if record_type == 'TXT' and 'v=DKIM1' in value:
                data['has_dkim'] = True
                data['dkim_detected'] = True
                data['dkim_record'] = value
                break
            
            if record_type == 'CNAME' and '._domainkey.' in record.get('host', ''):
                data['has_dkim'] = True
                data['dkim_detected'] = True
                data['dkim_record'] = value
                break
        
        return data

    def analyze_dns_snapshot(self, dns_snapshot):
        data = {'has_dmarc': False, 'dmarc_policy': None, 'dmarc_record': None}
        
        dmarc_records = dns_snapshot.get('DMARC', [])
        if dmarc_records and len(dmarc_records) > 0:
            for record in dmarc_records:
                if 'error' not in record:
                    data['has_dmarc'] = True
                    value = record.get('value', '')
                    data['dmarc_record'] = value
                    policy = self._extract_dmarc_policy(value)
                    if policy:
                        data['dmarc_policy'] = policy
                    break
        
        # Fallback: check TXT records on root if DMARC lookup failed or didn't find anything
        if not data['has_dmarc']:
            for r in dns_snapshot.get('TXT', []):
                if r.get('value', '').startswith('v=DMARC1'):
                    data['has_dmarc'] = True
                    data['dmarc_record'] = r.get('value')
                    data['dmarc_policy'] = self._extract_dmarc_policy(r.get('value'))
                    break

        return data
    
    def _extract_dmarc_policy(self, dmarc_value):
        """
        Extract the 'p=' policy from a DMARC record value.
        
        Args:
            dmarc_value: The DMARC TXT record value string
        
        Returns:
            The policy value ('none', 'quarantine', 'reject') or None
        """
        if not dmarc_value:
            return None
        
        parts = dmarc_value.split(';')
        for part in parts:
            part = part.strip()
            if part.startswith('p='):
                return part.split('=')[1].strip()
        
        return None
