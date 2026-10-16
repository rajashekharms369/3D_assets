# Oral cavity — aesthetic refinement

Based directly on the uploaded `oral-cavity-main.glb`.

Changes: warm pearly enamel, softer rose gums, satin lavender bases, four restored pastel specialty teeth, less tall rootward tissue, smooth shading, and an 85 mm studio presentation. Removed the unrelated default Cube. All 28 named teeth are retained. The current version applies a shared 12% left-to-right stretch to the teeth, gums and bases; height and depth are unchanged. Tooth contacts remain aligned because every mesh receives the same transformation. Tissue beyond the cervical anchor is compressed vertically by 36% before the common lateral stretch. Upper/lower gums and bases remain separate named objects.

## Files

- `oral-cavity-aesthetic.glb`: portable PBR model, 32 meshes and 287,984 triangles. All seven materials have explicit exported colours. Four accent teeth carry specialty properties.
- `oral-cavity-aesthetic.blend`: editable scene with three lights and camera.
- `oral-cavity-aesthetic.png`: 1600 × 1200 transparent Cycles render, 64 samples.
- `width_before.png`: aesthetic preview before the 12% width adjustment.
- `before.png`: uploaded model under the initial studio lights, with the unrelated Cube removed for inspection.
- `iter_01.png`, `after.png`: first aesthetic preview and latest widened preview.
- `refine.py`: reproducible refinement script. Put the supplied original GLB beside it and run with Blender's Python interpreter, or Blender background mode: `blender --background --python refine.py -- after`. It writes output files to its own directory. It is an editing script for the attached GLB, not a standalone geometry generator.
- `validation.json`: mesh counts, specialty properties, and round-trip GLB checks confirming a width ratio of 1.12 with unchanged height/depth.

## Review notes

Pass 1 restored colour separation, reduced the tall gum bands and softened the materials. Remaining visual issues: excessively loose framing, broad highlights, and a high viewing angle. Pass 2 tightened framing, lowered the view and refined highlight roughness/softbox size. The original tooth shapes are still stylised, the gum bands remain relatively regular, and the base is simpler than the original reference.

This is an aesthetic edit, not a new anatomical or collision correction. Existing hidden socket intersections were not repaired or recertified. Blender uses subtle procedural bump and subsurface shading; the GLB exports explicit colour/roughness/coat/transmission, but does not reproduce Blender's procedural bump or subsurface shading exactly. Its appearance depends on viewer lighting and tone mapping. No claim of an exact reference match is made.

## Width adjustment

`CONFIG["horizontal_scale"] = 1.12` controls the shared lateral stretch. It is applied once from the original input, so rerunning does not accumulate widening. The mesh count remains 32 and the triangle count remains 287,984. Camera, lighting and materials are unchanged from the previous aesthetic version.
