# Face kit (vendored, OFL)

Inlinable base64 woff2 faces for offline mockups. Curated kit (all OFL/self-hostable):
Geist (display+body) · Geist Mono (machinery) · Bricolage Grotesque (expressive display).

Build (run once, needs `fonttools`+`brotli` at build time only):
  pyftsubset <Face>.ttf --unicodes=U+0000-00FF,U+2018-201F,U+2022,U+2192 --flavor=woff2 --output-file=<face>.woff2
  base64 -i <face>.woff2 -o <face>-<weight>.b64
Then add each to MANIFEST.json: {"geist":{"family":"Geist","weights":{"400":"geist-400.b64"}}, ...}
and copy each OFL.txt into LICENSES/.

An empty MANIFEST.json degrades gracefully: fonts.font_faces() returns "" and mockups use
system font stacks (below the hi-fi bar but functional).
