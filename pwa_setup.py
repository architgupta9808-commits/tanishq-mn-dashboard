"""
Run: python pwa_setup.py
Creates the manifest.json and service worker needed for PWA installation.
"""
import json, os

manifest = {
    "name": "Tanishq MN Dashboard",
    "short_name": "Tanishq MN",
    "description": "Performance & incentive dashboard for Tanishq Malviya Nagar RSOs",
    "start_url": "/",
    "display": "standalone",
    "background_color": "#FBF7F0",
    "theme_color": "#C9A227",
    "orientation": "portrait",
    "icons": [
        {
            "src": "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>💎</text></svg>",
            "sizes": "any",
            "type": "image/svg+xml",
            "purpose": "any maskable"
        }
    ]
}

os.makedirs("static", exist_ok=True)
with open("static/manifest.json", "w") as f:
    json.dump(manifest, f, indent=2)

sw_js = """
const CACHE_NAME = 'tanishq-mn-v1';
const urlsToCache = ['/'];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(urlsToCache))
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request).then(response => response || fetch(event.request))
  );
});
"""

with open("static/sw.js", "w") as f:
    f.write(sw_js)

print("PWA files created: static/manifest.json, static/sw.js")
print("Now add the PWA <head> tags to app.py (see TASK 4b in the super prompt).")
