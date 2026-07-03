"""Design-system prompts for the mockup pipeline. Agnostic by construction — no identifier
or string here may name a proprietary layer (an agnosticism test greps this source file)."""

DESIGN_BRIEF = (
    "You are producing ONE self-contained HTML file (opens offline; no CDN/build; inline "
    "<style>/<script> only) — a hi-fi prototype the operator will judge as a real product, not "
    "a slide. Follow the design system exactly; take ONE aesthetic risk, no more. Do NOT use "
    "WebGL/3D or heavy canvas cinematics — premium static layout plus disciplined CSS micro-motion.\n"
    "TOKENS: all color/space/type as CSS custom properties in :root, with a full [data-theme] "
    "light+dark inversion and a pre-paint script to prevent flash. Never hardcode a color.\n"
    "PALETTE: muted, low-chroma; ONE restrained primary accent; reserve a 'signal' color for "
    "AI-proposed content, a 'verified' green, an 'alert' red; use var(--brand-primary) for the brand "
    "color. Reject saturated SaaS blue/green.\n"
    "TYPE: a grotesque for display+body; a monospace for ALL machinery (eyebrows, ids, timestamps, "
    "citations, stat labels), uppercase, wide tracking. Big ultralight tabular numbers.\n"
    "LAYOUT: ~1120-1180px column; a ~46px blueprint grid under a radial mask; ambient auras; sticky "
    "blurred header; numbered (NN) sections opened by a mono eyebrow over a hairline divider; 14-18px "
    "cards with a 3px left accent spine.\n"
    "MOTION: IntersectionObserver reveals (staggered; NEVER fade body text while it is being read); "
    "count-ups; hover lift. All gated behind prefers-reduced-motion and a .motion class; collapse to a "
    "static, legible final state. State is ALWAYS encoded by color + label + glyph.\n"
    "THREE REQUIRED BEHAVIORS: (1) RECONCILE — show a number only with its parts, computed 'sums to N'; "
    "(2) NO DEFAULT — AI-proposed content is declinable, no primary button, never auto-runs; "
    "(3) LABEL — every claim-bearing element carries a data-source=\"<claim id>\" attribute; tag any "
    "illustrative content SAMPLE. Never manufacture a fact, number, quote, or logo."
)

CREATIVE_DIRECTION_INSTR = (
    "Propose the creative direction (register, palette, type, ONE signature element, a metaphor). "
    "Each choice is an `inferred` claim whose `basis` lists the grounded pain ids it reasons from. "
    "If the GROUNDING carries brand colors (ids like `brand:0`), cite them as a `verified` claim with "
    "`sources`=[the brand id] — brand ids go in `sources`, NEVER in `basis`. Return {\"claims\": [...]}."
)

SOLUTION_INSTR = (
    "For each grounded pain, propose ONE solution approach. Each is an `inferred` claim whose `basis` "
    "lists the pain id(s) it addresses (from GROUNDING). Never invent facts about the customer. "
    "Return {\"solutions\": [{id, pain_id, approach, confidence, sources, basis}]}."
)

PURITY_SWEEP_INSTR = (
    'Return JSON {"uncited": ["<short quote>", ...]} listing every claim-bearing sentence in the HTML '
    "that has neither a data-source attribute nor a SAMPLE/PREVIEW tag. HTML follows."
)
