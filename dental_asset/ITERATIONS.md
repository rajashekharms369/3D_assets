# Render review log

Every numbered PNG was rendered with headless Blender through Python 3.11, at 960 × 540 and 24 Cycles samples, then opened and visually compared with the reference in the conversation. Files were retained rather than overwritten. Camera focal length remained 85 mm.

| Pass | Three largest observed differences or defects | Changes for the next pass |
| --- | --- | --- |
| 01 | Matte enamel; slab-like gum walls; large dark bite spaces. | Stronger, smaller lights and coat; deeper papillae and tighter collars; flatter and closer posterior bite tables. |
| 02 | Tall rectangular silhouette; reflections limited to crown tips; stretched gum texture. | Broader/shorter model, shorter lower incisors, smooth tissue subdivision, rounder crown transitions and lower key light. |
| 03 | Straight upper border; uniform cream highlights; accent positions too far apart. | Bowed border, enamel colour gradient, refined light placement, mint and amber moved toward reference positions. |
| 04 | Incisal edges lean inward; highlights too restrained; sideways texture stretching. | Shifted thin incisal edges toward labial faces; tested a stronger display contrast; corrected normal-map scale. |
| 05 | White enamel clips; posterior bite edges look flat; lower base is too narrow. | PBR Neutral tone mapping, reduced lighting, rounded posterior corners, flared lower base; corrected incisal cap geometry. |
| 06 | Bite line too level; tissue too red; reflections too simple. | Increased camera elevation, softened pink/lavender colours, redistributed the three lights and strengthened microtexture. |
| 07 | Too much upper opening visible; yellow enamel; repetitive posterior silhouettes. | Lowered camera elevation, cooler pearl colour, softer posterior corners and individual root eminences. |
| 08 | Visible crown spaces; simple reflections; gum colour banding. | Tested tighter spacing/overjet, stronger enamel coat/IOR and nearly uniform gum colour with normal-only fine detail. |
| 09 | Tightening caused 15 intersecting tooth pairs; remaining regular crown shapes; far-side crowns too hidden. | Restored spacing/overjet and shifted camera slightly toward the front. Kept improved enamel material. |
| 10 | Three residual first/second molar intersections; gaps at some lower cervical collars; surface detail still simpler than reference. | Increased only the terminal molar spacing, tightened lower sockets, adjusted fine normal-map strength. |
| 11 | Geometry defects resolved. Remaining reference differences: regular crown/gum forms; simpler white highlights; simplified lavender support silhouette. | Rendered at full resolution; that inspection exposed excessive micro-normal grain and cervical gaps, prompting another pass. |
| 12 | High-resolution pass 11 showed grainy enamel, cervical gaps, and simple highlights. | Smoothed the coat normal, reduced substrate micro-normal strength, embedded cervical ends more deeply, and rerendered. Independent review still identified an overly open-looking bite. |
| 13 | Bite fit improved the visible gap, but seven opposing tooth pairs still intersected at triangle interiors; reference framing was loose; material/forms remained simpler than target. | Added triangle-level occlusal fitting and slightly tighter camera framing. Rejected this mesh as a deliverable. |
| 14 | Fitted bite and tighter framing; all tooth pairs clear. Remaining differences are regular gingival/crown forms, simpler pearly highlights and a simplified support silhouette. | Adjusted vertical framing slightly for the delivery view. Reference fidelity remains partial. |
| 15 | The upper margin in pass 14 was too tight; regular gum forms and simple enamel highlights still differ from reference. | Balanced the vertical framing while retaining the validated bite and surface geometry. Selected for delivery; visual reference match remains partial. |

## Validation during iteration

- Pass 01: 183,648 triangles; no tooth intersections or non-manifold edges.
- Pass 03: 266,880 triangles after smoother gum geometry; no tooth intersections.
- Pass 06: 266,880 triangles; no tooth intersections.
- Pass 09: 15 tooth-pair intersections — rejected as a deliverable.
- Pass 10: 3 tooth-pair intersections — rejected as a deliverable.
- Pass 11: 266,880 triangles; all 378 tooth pairs clear; no non-manifold edges, loose vertices or zero-area faces.
- Pass 12: 266,880 triangles; all 378 tooth pairs clear.
- Pass 13: 7 opposing tooth-pair intersections — rejected.
- Pass 14: 266,880 triangles; all 378 tooth pairs clear after occlusal fitting.
- Pass 15: Final Blender/GLB validation passed at 266,880 triangles with all 378 tooth pairs clear. GLB reimport preserved 30 meshes, 28 teeth, four specialty properties and five decoded textures.

The final high-resolution PNG uses the pass 15 scene and camera. The earlier high-resolution pass 11 and pass 12 images are also retained for comparison. The remaining visual limitations are recorded here rather than treating a successful geometric test as proof of reference fidelity.
