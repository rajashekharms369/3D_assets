# Oral cavity — aesthetic refinement

Based directly on the uploaded `oral-cavity-main.glb`.

Changes: warm pearly enamel, softer rose gums, satin lavender bases, four restored pastel specialty teeth, less tall rootward tissue, smooth shading, and an 85 mm studio presentation. Removed the unrelated default Cube. All 28 tooth meshes and their positions are preserved. Tissue beyond the cervical anchor is compressed vertically by 36%; collars are left in place. Upper/lower gums and bases remain separate named objects.

## Files

- `oral-cavity-aesthetic.glb`: portable PBR model, 32 meshes and 287,984 triangles. All seven materials have explicit exported colours. Four accent teeth carry specialty properties.
- `oral-cavity-aesthetic.blend`: editable scene with three lights and camera.
- `oral-cavity-aesthetic.png`: 1600 × 1200 transparent Cycles render, 64 samples.
- `before.png`: uploaded model under the initial studio lights, with the unrelated Cube removed for inspection.
- `iter_01.png`, `after.png`: inspected aesthetic previews; the second preview has closer framing and a lower viewing angle.
- `refine.py`: reproducible refinement script. Put the supplied original GLB beside it and run with Blender's Python interpreter, or Blender background mode: `blender --background --python refine.py -- after`. It writes output files to its own directory. It is an editing script for the attached GLB, not a standalone geometry generator.
- `validation.json`: tooth preservation, mesh counts, exported colours and specialty checks.

## Review notes

Pass 1 restored colour separation, reduced the tall gum bands and softened the materials. Remaining visual issues: excessively loose framing, broad highlights, and a high viewing angle. Pass 2 tightened framing, lowered the view and refined highlight roughness/softbox size. The original tooth shapes are still stylised, the gum bands remain relatively regular, and the base is simpler than the original reference.

This is an aesthetic edit, not a new anatomical or collision correction. Existing hidden socket intersections were not repaired or recertified. Blender uses subtle procedural bump and subsurface shading; the GLB exports explicit colour/roughness/coat/transmission, but does not reproduce Blender's procedural bump or subsurface shading exactly. Its appearance depends on viewer lighting and tone mapping. No claim of an exact reference match is made.
