"""Read-only deliverable QA for the dental arch blend and binary glTF.

Run with the project's bpy-enabled Python 3.11 interpreter:
    validate_asset.py --blend dental_arch.blend --glb dental_arch.glb --output validation.json
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import re
import struct
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree


TOOTH_NAME = re.compile(r"^([UL])_([RL])_([1-7])_(.+)$")
ORDER = ("central", "lateral", "canine", "premolar1", "premolar2", "molar1", "molar2")
TRIANGLE_LIMIT = 300_000


def is_tooth(name, extras=None):
    return bool((extras or {}).get("tooth", False) or TOOTH_NAME.match(name))


def check_names(names, errors, prefix):
    counts = {"upper": 0, "lower": 0}
    expected = {f"{arch}_{side}_{i}_{kind}" for arch in "UL" for side in "RL"
                for i, kind in enumerate(ORDER, 1)}
    actual = set(names)
    for name in names:
        match = TOOTH_NAME.match(name)
        if match:
            counts["upper" if match[1] == "U" else "lower"] += 1
    if len(names) != 28 or counts != {"upper": 14, "lower": 14}:
        errors.append(f"{prefix}: expected 28 teeth (14 upper/14 lower); found {len(names)} ({counts})")
    if actual != expected or len(actual) != len(names):
        errors.append(f"{prefix}: tooth naming/order differs; missing={sorted(expected - actual)}, unexpected={sorted(actual - expected)}")
    return counts


def check_specialties(items, errors, prefix):
    specialties = {name: props.get("specialty") for name, props in items
                   if "specialty" in props}
    values = list(specialties.values())
    valid = all(isinstance(value, str) and value.strip() for value in values)
    if len(values) != 4 or not valid or len({str(v) for v in values}) != 4:
        errors.append(f"{prefix}: expected four teeth with unique nonempty specialty strings; found {specialties}")
    return specialties


def bounds(vertices):
    return tuple(min(v[i] for v in vertices) for i in range(3)), tuple(max(v[i] for v in vertices) for i in range(3))


def bounds_overlap(a, b):
    return all(a[0][i] <= b[1][i] and b[0][i] <= a[1][i] for i in range(3))


def inside_closed_mesh(point, tree, extent):
    """Odd/even ray crossing test, used to catch complete containment.

    Surface intersections are checked separately. A non-axis ray avoids common
    crown grid alignments, and a scale-relative step skips the previous hit.
    """
    direction = Vector((0.734789, 0.421371, 0.532917)).normalized()
    epsilon = max(extent * 1e-7, 1e-9)
    origin = Vector(point)
    crossings = 0
    remaining = extent * 4.0 + epsilon
    for _ in range(4096):
        location, _, _, distance = tree.ray_cast(origin, direction, remaining)
        if location is None:
            return bool(crossings % 2)
        if distance <= epsilon:
            return False  # Boundary contact is handled by BVH overlap.
        crossings += 1
        advance = distance + epsilon
        origin += direction * advance
        remaining -= advance
        if remaining <= 0:
            return bool(crossings % 2)
    raise RuntimeError("Ray crossing did not converge")


def inspect_blend(path, errors):
    bpy.ops.wm.open_mainfile(filepath=str(path.resolve()))
    scene = bpy.context.scene
    meshes = [obj for obj in scene.objects if obj.type == "MESH"]
    teeth = [obj for obj in meshes if is_tooth(obj.name, obj)]
    names = [obj.name for obj in teeth]
    counts = check_names(names, errors, "blend")
    specialties = check_specialties([(obj.name, obj) for obj in teeth], errors, "blend")
    depsgraph = bpy.context.evaluated_depsgraph_get()
    total_triangles = 0
    mesh_reports = []
    tooth_geometry = []
    for obj in sorted(meshes, key=lambda o: o.name):
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        try:
            mesh.calc_loop_triangles()
            triangle_count = len(mesh.loop_triangles)
            total_triangles += triangle_count
            bm = bmesh.new()
            try:
                bm.from_mesh(mesh)
                boundary_edges = sum(edge.is_boundary for edge in bm.edges)
                nonmanifold_edges = sum(not edge.is_manifold for edge in bm.edges)
                loose_vertices = sum(not vertex.link_edges for vertex in bm.verts)
                zero_area_faces = sum(face.calc_area() <= 1e-14 for face in bm.faces)
            finally:
                bm.free()
            if nonmanifold_edges or loose_vertices or zero_area_faces:
                errors.append(f"blend: {obj.name} has {nonmanifold_edges} nonmanifold edges, {loose_vertices} loose vertices, {zero_area_faces} zero-area faces")
            mesh_reports.append({"name": obj.name, "vertices": len(mesh.vertices),
                                 "triangles": triangle_count, "boundary_edges": boundary_edges,
                                 "nonmanifold_edges": nonmanifold_edges,
                                 "loose_vertices": loose_vertices, "zero_area_faces": zero_area_faces,
                                 "unapplied_modifiers": [m.type for m in obj.modifiers]})
            if obj in teeth:
                vertices = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
                triangles = [tuple(tri.vertices) for tri in mesh.loop_triangles]
                if not vertices or not triangles:
                    errors.append(f"blend: {obj.name} has empty geometry")
                    continue
                box = bounds(vertices)
                tree = BVHTree.FromPolygons(vertices, triangles, all_triangles=True, epsilon=0.0)
                tooth_geometry.append({"name": obj.name, "vertices": vertices, "tree": tree, "bounds": box})
        finally:
            evaluated.to_mesh_clear()
    if total_triangles >= TRIANGLE_LIMIT:
        errors.append(f"blend: {total_triangles} evaluated triangles is not below {TRIANGLE_LIMIT}")
    collisions = []
    broadphase_pairs = 0
    for a, b in itertools.combinations(tooth_geometry, 2):
        if not bounds_overlap(a["bounds"], b["bounds"]):
            continue
        broadphase_pairs += 1
        overlap = a["tree"].overlap(b["tree"])
        containment = False
        if not overlap:
            extent = max(Vector(a["bounds"][1]).length, Vector(b["bounds"][1]).length,
                         (Vector(a["bounds"][1]) - Vector(a["bounds"][0])).length,
                         (Vector(b["bounds"][1]) - Vector(b["bounds"][0])).length, 1e-5)
            containment = (inside_closed_mesh(a["vertices"][0], b["tree"], extent) or
                           inside_closed_mesh(b["vertices"][0], a["tree"], extent))
        if overlap or containment:
            collisions.append({"a": a["name"], "b": b["name"],
                               "intersecting_triangle_pairs": len(overlap), "containment": containment})
    if collisions:
        errors.append(f"blend: {len(collisions)} tooth pairs intersect")
    camera = scene.camera
    cameras = [{"name": obj.name, "focal_length_mm": obj.data.lens} for obj in scene.objects if obj.type == "CAMERA"]
    if camera is None or not math.isclose(camera.data.lens, 85.0, abs_tol=1e-5):
        errors.append("blend: active render camera is missing or is not 85 mm")
    return {"path": str(path.resolve()), "teeth": sorted(names), "counts": counts,
            "specialties": specialties, "evaluated_triangles": total_triangles,
            "meshes": mesh_reports, "all_tooth_pairs_checked": len(tooth_geometry) * (len(tooth_geometry) - 1) // 2,
            "broadphase_pairs": broadphase_pairs, "collision_count": len(collisions), "collisions": collisions,
            "cameras": cameras, "active_camera": camera.name if camera else None,
            "render_dimensions": [round(scene.render.resolution_x * scene.render.resolution_percentage / 100),
                                  round(scene.render.resolution_y * scene.render.resolution_percentage / 100)]}


def read_glb(path):
    raw = path.read_bytes()
    if len(raw) < 20:
        raise ValueError("file is too short for GLB header")
    magic, version, length = struct.unpack_from("<4sII", raw)
    if magic != b"glTF" or version != 2 or length != len(raw):
        raise ValueError("invalid GLB 2 header or file length")
    offset, document, binary_size = 12, None, 0
    while offset < length:
        if offset + 8 > length:
            raise ValueError("truncated GLB chunk header")
        chunk_length, chunk_type = struct.unpack_from("<II", raw, offset)
        offset += 8
        if chunk_length % 4 or offset + chunk_length > length:
            raise ValueError("invalid GLB chunk length/alignment")
        chunk = raw[offset:offset + chunk_length]
        if chunk_type == 0x4E4F534A:
            if document is not None:
                raise ValueError("multiple GLB JSON chunks")
            document = json.loads(chunk.decode("utf-8").rstrip(" \t\r\n\x00"))
        elif chunk_type == 0x004E4942:
            binary_size += chunk_length
        offset += chunk_length
    if document is None:
        raise ValueError("missing GLB JSON chunk")
    return document, binary_size


def inspect_glb(path, blend_report, errors):
    document, binary_size = read_glb(path)
    nodes = document.get("nodes", [])
    meshes = document.get("meshes", [])
    accessors = document.get("accessors", [])
    tooth_nodes = [node for node in nodes if is_tooth(node.get("name", ""), node.get("extras", {}))]
    names = [node.get("name", "") for node in tooth_nodes]
    counts = check_names(names, errors, "glb")
    specialties = check_specialties([(node.get("name", ""), node.get("extras", {})) for node in tooth_nodes], errors, "glb")
    if blend_report and specialties != blend_report["specialties"]:
        errors.append("glb: specialty values do not match the blend")
    for node in tooth_nodes:
        if "mesh" not in node:
            errors.append(f"glb: tooth {node.get('name')} has no mesh")
    mesh_triangles = []
    for index, mesh in enumerate(meshes):
        total = 0
        for primitive in mesh.get("primitives", []):
            mode = primitive.get("mode", 4)
            accessor_index = primitive.get("indices", primitive.get("attributes", {}).get("POSITION"))
            if accessor_index is None:
                errors.append(f"glb: mesh {index} has a primitive with no POSITION or indices")
                continue
            count = accessors[accessor_index]["count"]
            if mode == 4:
                if count % 3:
                    errors.append(f"glb: mesh {index} triangle accessor count is not divisible by 3")
                total += count // 3
            elif mode in (5, 6):
                total += max(count - 2, 0)
            else:
                errors.append(f"glb: mesh {index} uses non-surface primitive mode {mode}")
        mesh_triangles.append(total)
    triangles = sum(mesh_triangles[node["mesh"]] for node in nodes if "mesh" in node)
    if triangles >= TRIANGLE_LIMIT:
        errors.append(f"glb: {triangles} instanced triangles is not below {TRIANGLE_LIMIT}")
    material_reports = []
    for material in document.get("materials", []):
        extensions = material.get("extensions", {})
        material_reports.append({"name": material.get("name"),
                                 "roughness": material.get("pbrMetallicRoughness", {}).get("roughnessFactor", 1),
                                 "extensions": extensions})
    used_extensions = document.get("extensionsUsed", [])
    for required in ("KHR_materials_transmission", "KHR_materials_clearcoat"):
        if required not in used_extensions:
            errors.append(f"glb: missing expected enamel material extension {required}")
    for node in tooth_nodes:
        if "specialty" not in node.get("extras", {}) or "mesh" not in node:
            continue
        for primitive in meshes[node["mesh"]].get("primitives", []):
            material_index = primitive.get("material")
            material = document.get("materials", [])[material_index] if material_index is not None else {}
            transmission = material.get("extensions", {}).get("KHR_materials_transmission", {}).get("transmissionFactor", 0)
            if transmission <= 0:
                errors.append(f"glb: accent tooth {node.get('name')} has a crown primitive without transmission")
    buffers = document.get("buffers", [])
    for buffer in buffers:
        if "uri" in buffer:
            errors.append("glb: external buffer prevents a self-contained deliverable")
        elif buffer.get("byteLength", 0) > binary_size:
            errors.append("glb: binary chunk is smaller than its declared buffer")
    for view in document.get("bufferViews", []):
        if view.get("byteOffset", 0) + view.get("byteLength", 0) > binary_size:
            errors.append("glb: bufferView exceeds binary payload")
    for image in document.get("images", []):
        if "uri" in image and not image["uri"].startswith("data:"):
            errors.append("glb: external image prevents a self-contained deliverable")
    return {"path": str(path.resolve()), "file_bytes": path.stat().st_size,
            "binary_chunk_bytes": binary_size, "counts": counts, "teeth": sorted(names),
            "specialties": specialties, "triangles": triangles, "mesh_count": len(meshes),
            "materials": material_reports, "extensions_used": used_extensions,
            "camera_count": len(document.get("cameras", [])),
            "punctual_light_count": len(document.get("extensions", {}).get("KHR_lights_punctual", {}).get("lights", []))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blend", required=True, type=Path)
    parser.add_argument("--glb", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    errors = []
    report = {"validator": "dental_asset", "blender_version": bpy.app.version_string,
              "triangle_limit_exclusive": TRIANGLE_LIMIT, "errors": errors}
    for label, operation in (("blend", lambda: inspect_blend(args.blend, errors)),
                             ("glb", lambda: inspect_glb(args.glb, report.get("blend"), errors))):
        try:
            report[label] = operation()
        except Exception as exc:
            errors.append(f"{label}: validation failed: {type(exc).__name__}: {exc}")
    report["passed"] = not errors
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"passed": report["passed"], "errors": errors, "report": str(args.output)}, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
