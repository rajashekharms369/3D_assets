# Stylised dental arch

This is a procedural Blender asset built from the reference shown in the conversation. The mesh and delivery checks pass. **The reference match remains partial:** the gingiva and crown silhouettes are more regular, and the white reflections less intricate, than the reference. The PNG is the actual Cycles render of the delivered scene, with no painted-over geometry or generated-image substitution.

## Deliverables

- `dental_arch.blend` — editable scene, packed textures, 85 mm camera and three area lights.
- `dental_arch.glb` — self-contained binary glTF, geometry and materials, with modifiers applied.
- `dental_arch.png` — 1920 × 1080 transparent RGBA render, up to 128 Cycles CPU samples (adaptive threshold 0.015, minimum 24), with denoising.
- `renders/iter_01.png` through `renders/iter_15.png` — fifteen inspected 960 × 540 previews at 24 samples each.
- `ITERATIONS.md` — comparisons, changes and remaining visual differences.
- `validation.json` — independent checks on the final Blender file and GLB.

## Structure

Exactly 28 individually named tooth objects: 14 upper and 14 lower. The naming pattern is `{U|L}_{R|L}_{1..7}_{type}`, where the ordered types from the midline are `central`, `lateral`, `canine`, `premolar1`, `premolar2`, `molar1`, `molar2`. There are no third molars.

Each crown has its own origin and `tooth`, `arch`, `quadrant`, `tooth_number` and `crown_type` properties. Four crowns additionally have a `specialty` string; GLB exports these as node extras, accessible through `userData` in common glTF loaders.

| Object | `specialty` |
| --- | --- |
| `U_R_1_central` | `coral` |
| `U_R_6_molar1` | `sky_blue` |
| `L_R_2_lateral` | `mint` |
| `L_L_1_central` | `amber` |

Each arch has one continuous, closed gum/base mesh, including 14 cervical sockets, interdental papillae and an integrated horseshoe base. Cervical ends are concealed in the tissue. Crown shapes use asymmetric superellipse sections, flattened facial surfaces, fine ridges, thin incisal edges, a single canine cusp, two premolar cusps and four molar cusps. Size, tilt and rotation vary slightly by tooth. Lower occlusal surfaces are fitted against the upper crowns with clearance, including triangle-level intersection correction.

The final scene contains **266,880 evaluated triangles** across 30 meshes. All 378 tooth pairs are checked for surface intersection and containment; gum/tooth overlap at the cervical sockets is intentional. The `.blend` has no unapplied mesh modifiers. Unit convention in Blender: one coordinate unit represents one centimetre (`scale_length = 0.01`); web viewers may choose their own presentation scale.

The camera is 85 mm, at approximately 32° yaw and 5.8° downward elevation. Lighting consists of an upper-left key, cool right rim and lavender fill. The material setup includes enamel subsurface scattering, coat, fine image normal maps, and transmission on accent crowns. Base roughness increases into the lavender region.

Blender subsurface scattering is retained in the `.blend`; standard glTF does not reproduce that shader exactly. The GLB retains enamel colour, normal maps, roughness, coat and transmission. Its appearance depends on the website's lighting, tone mapping and support for glTF material extensions. Scene lights and the render camera are retained in Blender and omitted from the geometry-only GLB.

## Reproduce in this cloud workspace

The tested interpreter is Python 3.11.17 with `bpy==4.3.0`, `numpy==1.26.4` and `pillow==12.3.0`. Blender runs headlessly through the Python API. No GPU or background service is required.

```bash
cd /workspace/3D_assets/dental_asset
bash setup.sh
/workspace/.dental-tools/run-python.sh build_dental.py --config config_final.json --iteration 16
/workspace/.dental-tools/run-python.sh build_dental.py --config config_final.json --final
/workspace/.dental-tools/run-python.sh validate_asset.py --blend dental_arch.blend --glb dental_arch.glb --output validation.json
```

The first render command writes a new preview; choose an unused iteration number. `--final` regenerates and replaces the three main deliverables. Preserve user edits before rerunning it. `config_final.json` contains the delivered camera, geometry, material and sampling settings. `build_dental.py` builds the crowns, materials, lights and exports; `gum_mesh.py` builds the tissue. Historical source snapshots accompany the preview images for inspection; use the current builder and final configuration for the supported reproduction workflow.

Each cloud task is already isolated. Use the existing checkout; do not create a Git worktree unless explicitly requested.
