import dns.resolver
import dns.exception
import whois

class DNSLookup:
    # Industry-standard DKIM selectors used across providers
    # These are common, not provider-specific
    STANDARD_DKIM_SELECTORS = [
        'default',
        'k1',
        'selector1',
        'selector2',
        'google',
        'msmtp',
        'smtp',
        'mail'
    ]

    def __init__(self, nameservers=None):
        self.resolver = dns.resolver.Resolver()
        if nameservers:
            self.resolver.nameservers = nameservers
        else:
            # Use Cloudflare and Google as default public resolvers
            self.resolver.nameservers = ['1.1.1.1', '8.8.8.8']

    def get_records(self, domain, record_type):
        try:
            answers = self.resolver.resolve(domain, record_type)
            results = []
            for rdata in answers:
                value = rdata.to_text()
                
                # Handle multi-part TXT records by joining chunks
                if record_type == 'TXT':
                    # dnspython's TXT rdata.strings is a list of chunks
                    if hasattr(rdata, 'strings'):
                        value = "".join([s.decode('utf-8') if isinstance(s, bytes) else s for s in rdata.strings])
                    else:
                        value = value.strip('"')

                record_data = {
                    'type': record_type,
                    'host': domain,
                    'value': value,
                    'ttl': answers.ttl
                }

                # Specialized handling for MX priority
                if record_type == 'MX':
                    # MX rdata has .preference and .exchange
                    record_data['priority'] = getattr(rdata, 'preference', 0)
                    # For value, we might want just the exchange
                    record_data['value'] = str(rdata.exchange).rstrip('.')

                results.append(record_data)
            return results
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
            return []
        except dns.exception.Timeout:
            return [{'error': 'Timeout', 'type': record_type}]
        except Exception as e:
            return [{'error': str(e), 'type': record_type}]

    def get_whois(self, domain):
        try:
            w = whois.whois(domain)
            return {
                'registrar': w.registrar,
                'name_servers': w.name_servers if w.name_servers else []
            }
        except Exception as e:
            return {'error': str(e), 'registrar': None, 'name_servers': []}

    def get_all_records(self, domain, check_www=True, filter_sections=None):
        """
        Retrieves DNS records for the domain.
        filter_sections: List of sections to include. 
                         Options: 'web', 'email', 'A', 'CNAME', 'MX', 'TXT', 'NS', 'DMARC', 'DKIM'
        """
        all_types = ['A', 'CNAME', 'MX', 'TXT', 'NS']
        results = {}
        
        # Map logical sections to record types
        mapping = {
            'web': ['A', 'CNAME', 'NS'],
            'email': ['MX', 'TXT', 'DMARC', 'DKIM'],
            'SPF': ['TXT']
        }
        
        requested_types = []
        if filter_sections:
            if 'all' in filter_sections:
                requested_types = all_types + ['DMARC', 'DKIM']
            else:
                for s in filter_sections:
                    if s in mapping:
                        requested_types.extend(mapping[s])
                    else:
                        requested_types.append(s)
            requested_types = list(set(requested_types))
        else:
            requested_types = all_types + ['DMARC', 'DKIM']

        # ALWAYS perform WHOIS lookup for general context
        results['WHOIS'] = self.get_whois(domain)

        # Root lookups
        for t in all_types:
            if t in requested_types:
                records = self.get_records(domain, t)
                if records:
                    results[t] = records

        # www lookup (if applicable and web-related)
        if check_www and not domain.startswith('www.'):
             is_web_requested = any(t in requested_types for t in ['A', 'CNAME'])
             if is_web_requested:
                 www_domain = f"www.{domain}"
                 www_records = self.get_records(www_domain, 'CNAME')
                 www_a_records = self.get_records(www_domain, 'A')
                 
                 if www_records:
                     results['WWW_CNAME'] = www_records
                 if www_a_records:
                     results['WWW_A'] = www_a_records

        # DMARC lookup
        if 'DMARC' in requested_types:
            dmarc_domain = f"_dmarc.{domain}"
            dmarc_records = self.get_records(dmarc_domain, 'TXT')
            if dmarc_records:
                results['DMARC'] = dmarc_records

        # DKIM lookup
        if 'DKIM' in requested_types:
            dkim_records = []
            for selector in self.STANDARD_DKIM_SELECTORS:
                dkim_domain = f"{selector}._domainkey.{domain}"
                dkim_txt = self.get_records(dkim_domain, 'TXT')
                if dkim_txt:
                    dkim_records.extend(dkim_txt)
                dkim_cname = self.get_records(dkim_domain, 'CNAME')
                if dkim_cname:
                    dkim_records.extend(dkim_cname)
            
            if dkim_records:
                results['DKIM'] = dkim_records

        return results
