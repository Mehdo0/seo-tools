#!/bin/bash
# Email campaign: Send SEO audit to target business
# Usage: ./send_audit.sh "Business Name" "email@example.com" "https://site.com"

BUSINESS="$1"
EMAIL="$2"
URL="$3"
TOKEN=$(grep AUTH_TOKEN /home/ubuntu/.hermes/config.yaml 2>/dev/null || echo "")

# Generate SEO audit using our tool
AUDIT=$(python3 -c "
import urllib.request, json
from backend.services.seo_analyzer import analyze_html, compute_seo_score
try:
    html = urllib.request.urlopen('$URL', timeout=10).read().decode()
    result = analyze_html(html, url='$URL')
    score = compute_seo_score(result)
    print(json.dumps({
        'score': score,
        'title': result['meta_tags'].get('title', 'N/A'),
        'description': result['meta_tags'].get('description', 'N/A')[:200],
        'h1_count': result['headings'].get('h1', {}).get('count', 0),
        'images_without_alt': result['images'].get('without_alt', 0),
        'has_viewport': result['mobile_viewport'].get('has_viewport', False),
    }))
except Exception as e:
    print(json.dumps({'error': str(e)}))
")

echo "$AUDIT"
