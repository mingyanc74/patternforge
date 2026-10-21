# Rulecraft interface direction

Rulecraft is the user-facing name of the existing PatternForge data preparation application. Repository identity, HTTPS hostname, API contracts, session ownership, credentials, snapshots and processing behavior stay unchanged. Historical Clearflow evidence remains dated evidence, not renamed retrospectively.

## Visual system

- Audience/task: people preparing private CSV/Excel data with readable natural-language rules; the main job is to move safely from cloud source to reviewed result.
- Palette: ink `#273340`, light slate navigation `#f0f3f7`, canvas `#f7f8fa`, white surface `#ffffff`, blue action `#2867a5`, pale selection `#eaf2fb`. This merges the original light/blue workbench with the refined first-pass typography and components. Semantic warning/failure colors stay distinct.
- Type: self-hosted Manrope variable for interface/headings, system CJK fallbacks; data has tabular numerals, no remote font requests. Manrope is supplied under its included SIL OFL.
- Layout: a narrow light navigation rail, compact context header, left-aligned page heading, one clear work surface. The file table remains the main object, not decorative metrics. Narrow layouts cap the source preview's height so the transformation controls are not buried below a full table.
- Components: 7–8px controls, 10px work surfaces, low-contrast borders, minimal surface shadows; selected columns and selected operations use the same action tone. Buttons retain plain action names. Column headers can select targets through exactly the same state handler as the existing checkbox/radio list; extraction still permits one source column and replacement/normalization retain the existing limits.
- Memorable element: the gate's rule-workbench composition uses explicitly illustrative input → instruction → output, connecting the brand to the product rather than an unrelated hero image.

```text
Brand / context header                 workspace controls
Navigation rail | page title                       primary action
                | actual workflow steps (when applicable)
                | files / data table     | configuration
                | pagination / retention / source safety
```

## Scope and critique

This is an application, not a marketing landing page: avoid fake metrics, full-page promotional banners, decorative charts and stock imagery. Keep the source preview readable and preserve all error, busy, empty, expired and sample-source labels. The sample adapter remains explicitly simulated. A live service claim must come from actual service state, not decoration.

Do not replace the established APIs, add account registration, change the public hostname, or migrate the Spark stack to another host. Mobile layout must not rely on a fixed sidebar, and data tables may scroll inside their own container without making the entire viewport overflow. Respect reduced motion and keyboard focus.

Reference reviewed: [Anthropic frontend-design skill](https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md). Principles adapted to this existing product; no third-party runtime or skill installer executed. Review the actual browser at desktop and narrow widths, then verify a genuine retained AWS dataset still processes on the unchanged backend.

Additional primary design references: [Linear's UI redesign](https://linear.app/now/how-we-redesigned-the-linear-ui) for consistent navigation/header hierarchy and density, and [Supabase table patterns](https://supabase.com/design-system/docs/ui-patterns/tables) for readable data surfaces with filtering/pagination and clear row actions. These are design references, not imported dashboard code or new dependencies. No branding, screenshots or product data from those sites are bundled.
