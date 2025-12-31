"""
DNS Lookup Module - Security Hardened
Implements all P1/P2 security controls from SECURITY_AUDIT.md
"""

import dns.resolver
import dns.exception
import whois
import logging
import re
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class DNSLookup:
    """
    Security-hardened DNS lookup class.
    
    Security Controls Implemented:
    - P1-4: DNS timeout limits (per-query and lifetime)
    - P1-5: Record count limits (MAX_RECORDS_PER_TYPE)
    - P1-6: CNAME chain depth limit (prevents infinite loops)
    - P1-7: SSRF protection (blocks internal/private domains)
    - P1-8: Error message sanitization (no internal path leakage)
    """
    
    # === SECURITY LIMITS ===
    MAX_RECORDS_PER_TYPE = 100     # Cap DNS records to prevent memory exhaustion
    DEFAULT_TIMEOUT = 5.0          # Per-server query timeout (seconds)
    DEFAULT_LIFETIME = 15.0        # Total query lifetime (seconds)
    CNAME_DEPTH_LIMIT = 5          # Prevent infinite CNAME chains
    MAX_DOMAIN_LENGTH = 253        # RFC 1035 limit
    
    # SSRF Protection: Block internal/private domains
    BLOCKED_DOMAIN_PATTERNS = [
        r'\.local$',
        r'\.internal$',
        r'\.corp$',
        r'\.intranet$',
        r'\.home$',
        r'\.lan$',
        r'^localhost$',
        r'^127\.',
        r'^10\.',
        r'^192\.168\.',
        r'^172\.(1[6-9]|2[0-9]|3[0-1])\.',
        r'^0\.',
        r'^169\.254\.',  # Link-local
        r'^::1$',        # IPv6 localhost
        r'^fc00:',       # IPv6 private
        r'^fe80:',       # IPv6 link-local
    ]
    
    # Valid domain regex (RFC 1035 compliant)
    DOMAIN_REGEX = re.compile(
        r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'
    )
    
    # Industry-standard DKIM selectors
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

    def __init__(self, nameservers: Optional[List[str]] = None, 
                 timeout: Optional[float] = None, 
                 lifetime: Optional[float] = None):
        """
        Initialize DNS resolver with security-hardened settings.
        
        Args:
            nameservers: List of DNS resolver IPs (defaults to Cloudflare + Google)
            timeout: Per-server query timeout in seconds
            lifetime: Total query lifetime in seconds
        """
        self.resolver = dns.resolver.Resolver()
        
        # Set timeouts to prevent hanging (P1-4)
        self.resolver.timeout = timeout or self.DEFAULT_TIMEOUT
        self.resolver.lifetime = lifetime or self.DEFAULT_LIFETIME
        
        if nameservers:
            self.resolver.nameservers = nameservers
        else:
            # Use Cloudflare and Google as default public resolvers
            self.resolver.nameservers = ['1.1.1.1', '8.8.8.8']
        
        # Compile blocked patterns for performance
        self._blocked_patterns = [re.compile(p, re.IGNORECASE) for p in self.BLOCKED_DOMAIN_PATTERNS]

    def _is_blocked_domain(self, domain: str) -> bool:
        """
        Check if domain is blocked (SSRF protection - P1-7).
        
        Blocks:
        - Internal TLDs (.local, .internal, .corp, etc.)
        - Private IP ranges
        - Localhost
        """
        domain_lower = domain.lower().strip()
        
        for pattern in self._blocked_patterns:
            if pattern.search(domain_lower):
                logger.warning(f"Blocked SSRF attempt: {domain}")
                return True
        
        return False

    def _is_valid_domain(self, domain: str) -> bool:
        """Validate domain format (RFC 1035 compliant)."""
        if not domain or not isinstance(domain, str):
            return False
        if len(domain) > self.MAX_DOMAIN_LENGTH:
            return False
        return bool(self.DOMAIN_REGEX.match(domain))

    def _sanitize_error(self, error: Exception) -> str:
        """
        Sanitize error messages to prevent information leakage (P1-8).
        
        Removes file paths, internal details, and sensitive information.
        """
        error_str = str(error)
        
        # Remove file paths
        error_str = re.sub(r'/[^\s]+/[^\s]+', '[PATH]', error_str)
        error_str = re.sub(r'C:\\[^\s]+', '[PATH]', error_str)
        
        # Remove line numbers
        error_str = re.sub(r'line \d+', 'line [N]', error_str)
        
        # Truncate long errors
        if len(error_str) > 200:
            error_str = error_str[:200] + '...'
        
        return error_str

    def get_records(self, domain: str, record_type: str) -> List[Dict[str, Any]]:
        """
        Get DNS records with security limits.
        
        Security Controls:
        - Domain validation and SSRF blocking (P1-7)
        - Record count limits (P1-5)
        - Timeout enforcement (P1-4)
        - Error sanitization (P1-8)
        """
        # Security: Validate domain
        if not self._is_valid_domain(domain) and not domain.startswith('_'):
            # Allow underscore prefixes for _dmarc, _domainkey, etc.
            if not self._is_valid_domain(domain.lstrip('_').split('.', 1)[-1] if '.' in domain else ''):
                logger.warning(f"Invalid domain format rejected: {domain}")
                return [{'error': 'Invalid domain format', 'type': record_type}]
        
        # Security: Block internal/private domains (SSRF protection)
        if self._is_blocked_domain(domain):
            return [{'error': 'Domain not allowed', 'type': record_type}]
        
        try:
            answers = self.resolver.resolve(domain, record_type)
            results = []
            record_count = 0
            
            for rdata in answers:
                # Security: Enforce record limit (P1-5)
                record_count += 1
                if record_count > self.MAX_RECORDS_PER_TYPE:
                    results.append({
                        'type': record_type,
                        'warning': f'Response truncated: more than {self.MAX_RECORDS_PER_TYPE} records returned',
                        'truncated': True
                    })
                    logger.warning(f"DNS response truncated for {domain}/{record_type}: {record_count}+ records")
                    break
                
                value = rdata.to_text()
                
                # Handle multi-part TXT records by joining chunks
                if record_type == 'TXT':
                    if hasattr(rdata, 'strings'):
                        value = "".join([
                            s.decode('utf-8') if isinstance(s, bytes) else s 
                            for s in rdata.strings
                        ])
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
                    record_data['priority'] = getattr(rdata, 'preference', 0)
                    record_data['value'] = str(rdata.exchange).rstrip('.')

                results.append(record_data)
            
            return results
            
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
            return []
        except dns.exception.Timeout:
            logger.warning(f"DNS timeout for {domain}/{record_type}")
            return [{'error': 'DNS lookup timed out', 'type': record_type}]
        except Exception as e:
            logger.exception(f"DNS lookup error for {domain}/{record_type}")
            return [{'error': self._sanitize_error(e), 'type': record_type}]

    def resolve_cname_chain(self, domain: str, depth: int = 0) -> Optional[str]:
        """
        Resolve CNAME chain with depth limit (P1-6).
        
        Prevents infinite loops from circular CNAME references.
        Returns the final target or None if chain is too deep/broken.
        """
        if depth >= self.CNAME_DEPTH_LIMIT:
            logger.warning(f"CNAME chain too deep for {domain} (depth={depth})")
            return None
        
        cname_records = self.get_records(domain, 'CNAME')
        
        if not cname_records or cname_records[0].get('error'):
            return domain  # End of chain
        
        target = cname_records[0].get('value', '').rstrip('.')
        if target:
            return self.resolve_cname_chain(target, depth + 1)
        
        return domain

    def get_whois(self, domain: str) -> Dict[str, Any]:
        """
        Get WHOIS information with error sanitization.
        
        Security Controls:
        - Domain validation (SSRF protection)
        - Error sanitization (P1-8)
        """
        # Security: Validate domain
        if not self._is_valid_domain(domain):
            return {'error': 'Invalid domain format', 'registrar': None, 'name_servers': []}
        
        # Security: Block internal domains
        if self._is_blocked_domain(domain):
            return {'error': 'Domain not allowed', 'registrar': None, 'name_servers': []}
        
        try:
            w = whois.whois(domain)
            return {
                'registrar': w.registrar,
                'name_servers': w.name_servers if w.name_servers else []
            }
        except Exception as e:
            # Sanitized error message (P1-8)
            logger.warning(f"WHOIS lookup failed for {domain}: {type(e).__name__}")
            return {
                'error': 'WHOIS lookup unavailable',
                'registrar': None,
                'name_servers': []
            }

    def get_all_records(self, domain: str, check_www: bool = True, 
                        filter_sections: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Retrieves DNS records for the domain with full security controls.
        
        Args:
            domain: Domain to query
            check_www: Whether to check www subdomain
            filter_sections: List of sections to include (web, email, A, CNAME, MX, etc.)
        
        Security Controls:
        - All controls from get_records()
        - Domain validation at entry point
        """
        # Security: Validate domain at entry point
        if not self._is_valid_domain(domain):
            return {'error': 'Invalid domain format'}
        
        if self._is_blocked_domain(domain):
            return {'error': 'Domain not allowed for security reasons'}
        
        all_types = ['A', 'CNAME', 'MX', 'TXT', 'NS']
        results: Dict[str, Any] = {}
        
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

        # WHOIS lookup
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
                if dkim_txt and not dkim_txt[0].get('error'):
                    dkim_records.extend(dkim_txt)
                dkim_cname = self.get_records(dkim_domain, 'CNAME')
                if dkim_cname and not dkim_cname[0].get('error'):
                    dkim_records.extend(dkim_cname)
            
            if dkim_records:
                results['DKIM'] = dkim_records

        return results
