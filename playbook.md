# 🛠 Playbook: DNS & Email Delivery Diagnostics

**Goal**: Empower the support team to resolve 90% of "Email not working" or "Domain not connecting" tickets using the DNS Diagnostic App.

## 1. The 5-Second Triage
When a customer reports that their professional email is "not working" or "not saving copies," follow this flow:
- **Run the Domain**: Enter the domain (e.g., alliebryan.com) into the Diagnostic App.
- **Check Nameservers**: Are they pointing to our managed servers (`ns.liquidweb.com` / `ns1.liquidweb.com`)?
- **Check MX Records**: Are the values pointing to `emailsrvr.com`?

## 2. Symptom & Resolution Matrix

| Symptom | App Diagnostic Result | Resolution Path |
| :--- | :--- | :--- |
| "I'm not receiving any emails." | **MX Records**: None found or pointing to old host (e.g., GoDaddy). | **Action**: Provide the MX, SPF, and DKIM records. If we manage DNS, apply them for the user. |
| "My email is going to spam." | **SPF/DMARC**: Fail or Missing. | **Action**: Add the `v=spf1 include:emailsrvr.com ~all` TXT record. |
| "I don't use [Provider] anymore." | **Nameservers**: Pointing to an old registrar (e.g., Hostinger). | **Action**: Explain that the domain is still "parked" there. Recommend a Nameserver change or a full Transfer. |
| "Emails aren't saving in Webmail." | **DNS**: Correct. **Client**: Using POP3. | **Action**: This is a client-side setting. Advise switching to IMAP or checking "Leave a copy on server." |

## 3. How to use the DNS Diagnostic App
- **Step 1**: Open the app URL.
- **Step 2**: Input the domain name without `https://`.
- **Step 3**: Look for **Red** indicators. Anything in red is a misconfiguration that needs a DNS update.
