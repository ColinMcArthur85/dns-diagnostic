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
            
            # Normalize registrar (some libraries return a list)
            registrar = w.registrar
            if isinstance(registrar, list):
                registrar = registrar[0] if registrar else None
            
            # Normalize name_servers (ensure it's always a list of strings)
            ns = w.name_servers
            if ns is None:
                ns = []
            elif isinstance(ns, str):
                ns = [ns]
            elif isinstance(ns, list):
                # Ensure all elements are strings and cleaned
                ns = [str(item) for item in ns if item]
            
            return {
                'registrar': registrar,
                'name_servers': ns
            }
        except Exception as e:
            # Sanitized error message (P1-8)
            logger.warning(f"WHOIS lookup failed for {domain}: {type(e).__name__}")
            return {
                'error': 'WHOIS lookup unavailable',
                'registrar': None,
                'name_servers': []
            }

    # === AUTHORITATIVE LOOKUP METHODS (Phase 3: Trace Functionality) ===
    
    def get_authoritative_nameservers(self, domain: str) -> List[str]:
        """
        Find the authoritative nameservers for the domain.
        
        This queries the NS records to find which nameservers are authoritative
        for this domain. Used for direct lookups that bypass cache.
        
        Args:
            domain: Domain to find authoritative NS for
            
        Returns:
            List of authoritative nameserver hostnames, or empty list on error
        """
        if not self._is_valid_domain(domain):
            logger.warning(f"Invalid domain for auth NS lookup: {domain}")
            return []
        if self._is_blocked_domain(domain):
            logger.warning(f"Blocked domain for auth NS lookup: {domain}")
            return []
            
        try:
            answers = self.resolver.resolve(domain, 'NS')
            return [str(r.target).rstrip('.') for r in answers]
        except dns.resolver.NXDOMAIN:
            logger.warning(f"Domain does not exist: {domain}")
            return []
        except dns.resolver.NoAnswer:
            logger.warning(f"No NS records found for: {domain}")
            return []
        except Exception as e:
            logger.warning(f"Could not find authoritative NS for {domain}: {self._sanitize_error(e)}")
            return []

    def bypass_cache_lookup(self, domain: str, record_type: str) -> List[Dict[str, Any]]:
        """
        Query the authoritative nameservers directly, bypassing public resolver cache.
        
        This is useful for 'I just fixed it!' scenarios where users want to verify 
        their DNS changes before full propagation completes.
        
        Security Controls:
        - Domain validation and SSRF blocking
        - Timeout enforcement
        - Error sanitization
        
        Args:
            domain: Domain to query
            record_type: DNS record type (A, CNAME, MX, etc.)
            
        Returns:
            List of records from authoritative source, with 'source': 'authoritative'
        """
        # Security validation
        if not self._is_valid_domain(domain):
            return [{"error": "Invalid domain format", "type": record_type, "source": "authoritative"}]
        if self._is_blocked_domain(domain):
            return [{"error": "Domain not allowed", "type": record_type, "source": "authoritative"}]
        
        auth_ns_list = self.get_authoritative_nameservers(domain)
        if not auth_ns_list:
            return [{"error": "Could not find authoritative nameservers", "type": record_type, "source": "authoritative"}]

        # Create a temporary resolver pointing to the auth NS
        custom_resolver = dns.resolver.Resolver()
        custom_resolver.timeout = self.DEFAULT_TIMEOUT
        custom_resolver.lifetime = self.DEFAULT_LIFETIME
        
        # Try each authoritative nameserver until one works
        last_error = None
        for auth_ns in auth_ns_list[:3]:  # Try up to 3 nameservers
            try:
                # Resolve the IP of the auth NS (we need an IP, not a hostname)
                ns_ip_answers = self.resolver.resolve(auth_ns, 'A')
                ns_ip = str(ns_ip_answers[0])
                custom_resolver.nameservers = [ns_ip]
                
                # Now query using this resolver
                answers = custom_resolver.resolve(domain, record_type)
                results = []
                
                for rdata in answers:
                    value = rdata.to_text()
                    
                    # Handle TXT record formatting
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
                        'ttl': answers.ttl,
                        'source': 'authoritative',
                        'nameserver': auth_ns
                    }
                    
                    # Handle MX priority
                    if record_type == 'MX':
                        record_data['priority'] = getattr(rdata, 'preference', 0)
                        record_data['value'] = str(rdata.exchange).rstrip('.')
                    
                    results.append(record_data)
                
                return results
                
            except dns.resolver.NXDOMAIN:
                return [{"error": "Domain does not exist", "type": record_type, "source": "authoritative"}]
            except dns.resolver.NoAnswer:
                return []  # Record type doesn't exist (not an error)
            except Exception as e:
                last_error = e
                logger.debug(f"Auth lookup via {auth_ns} failed, trying next: {e}")
                continue
        
        # All nameservers failed
        error_msg = self._sanitize_error(last_error) if last_error else "All nameservers failed"
        logger.warning(f"Authoritative lookup failed for {domain}/{record_type}: {error_msg}")
        return [{"error": f"Direct lookup failed: {error_msg}", "type": record_type, "source": "authoritative"}]

    def trace_record(self, domain: str, record_type: str) -> Dict[str, Any]:
        """
        Compare cached (public resolver) vs authoritative (direct) DNS records.
        
        This is the main method for diagnosing propagation issues. It shows:
        - What public resolvers (Cloudflare, Google) currently see
        - What the authoritative nameservers actually have
        - Whether the change has fully propagated
        - Estimated time remaining until propagation completes
        
        Args:
            domain: Domain to trace
            record_type: DNS record type to compare
            
        Returns:
            {
                "domain": str,
                "record_type": str,
                "cached": [...],        # What public resolvers see
                "authoritative": [...], # What the actual DNS servers have
                "propagated": bool,     # Whether they match
                "ttl_remaining": int,   # Seconds until cache expires (estimate)
                "message": str          # Human-readable status
            }
        """
        # Get both cached and authoritative records
        cached = self.get_records(domain, record_type)
        authoritative = self.bypass_cache_lookup(domain, record_type)
        
        # Filter out error records for comparison
        cached_clean = [r for r in cached if not r.get('error')]
        auth_clean = [r for r in authoritative if not r.get('error')]
        
        # Compare values (ignore TTL, source, and nameserver for matching)
        cached_values = set(r.get('value', '').lower().rstrip('.') for r in cached_clean)
        auth_values = set(r.get('value', '').lower().rstrip('.') for r in auth_clean)
        
        propagated = cached_values == auth_values
        
        # Estimate TTL remaining (from cached records)
        ttl_remaining = 0
        if cached_clean:
            ttl_remaining = max(r.get('ttl', 0) for r in cached_clean)
        
        # Build human-readable message
        if propagated:
            message = "✓ Records match - DNS is fully propagated"
        elif not auth_clean and not cached_clean:
            message = "No records found in either source"
        elif not auth_clean:
            message = "Record exists in cache but not at authoritative NS (recently deleted?)"
        elif not cached_clean:
            message = f"Record exists at authoritative NS but not in cache yet (propagating, ~{ttl_remaining}s remaining)"
        else:
            message = f"Records differ - propagation in progress (~{ttl_remaining}s remaining)"
        
        return {
            "domain": domain,
            "record_type": record_type,
            "cached": cached,
            "authoritative": authoritative,
            "propagated": propagated,
            "ttl_remaining": ttl_remaining,
            "message": message,
            "cached_values": list(cached_values),
            "authoritative_values": list(auth_values)
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
        
        all_types = ['A', 'AAAA', 'CNAME', 'MX', 'TXT', 'NS']
        results: Dict[str, Any] = {}
        
        # Map logical sections to record types
        mapping = {
            'web': ['A', 'AAAA', 'CNAME', 'NS'],  # AAAA for IPv6 detection
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
                results[t] = records

        # www lookup (if applicable and web-related)
        if check_www and not domain.startswith('www.'):
            is_web_requested = any(t in requested_types for t in ['A', 'AAAA', 'CNAME'])
            if is_web_requested:
                www_domain = f"www.{domain}"
                www_records = self.get_records(www_domain, 'CNAME')
                www_a_records = self.get_records(www_domain, 'A')
                www_aaaa_records = self.get_records(www_domain, 'AAAA')  # IPv6
                
                results['WWW_CNAME'] = www_records
                results['WWW_A'] = www_a_records
                results['WWW_AAAA'] = www_aaaa_records  # IPv6

        # DMARC lookup
        if 'DMARC' in requested_types:
            dmarc_domain = f"_dmarc.{domain}"
            dmarc_records = self.get_records(dmarc_domain, 'TXT')
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
            
            results['DKIM'] = dkim_records

        return results
