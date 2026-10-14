"""Continuous socketed gum and broad horseshoe base for the dental asset.

The scene uses roughly one unit per centimetre.  ``gum_height`` and
``base_height`` are absolute *unsigned* distances from the bite plane:
upper defaults 2.0/2.5, lower 1.7/2.3.  Signed values are accepted too.
``gum_outer_width`` overrides the outward radial half-width; by default
each section follows crown depth / 2 + .14.  The inner side similarly
uses depth / 2 + .10 (or ``gum_inner_width``).

Every tooth has a genuine socket opening and an internal closed pocket.
Shared cell edges are welded; the surface is one connected manifold.
The UV V coordinate is zero on the gingival collar, .60 where the gum
meets the base, and one at the underside, for a pink-to-lavender shader.
"""

import bisect
import math

import bpy
import bmesh


def _get(config, key, default):
    if config is None:
        return default
    if isinstance(config, dict):
        return config.get(key, default)
    return getattr(config, key, default)


def build_gum(arch_name, teeth, arch, material, config=None):
    """Return one socketed Blender mesh, with no unapplied modifiers.

    ``arch.frame(s)`` returns center, tangent, outward-normal XY pairs.
    Teeth are dictionaries containing s, w, d, h, cerv, sign_z, center,
    tangent and normal.  Either order of the tooth dictionaries is valid.
    The default resolution is approximately 22k triangles per arch.
    """
    teeth = sorted(teeth, key=lambda t: t["s"])
    if not teeth:
        raise ValueError("A gum arch requires at least one tooth")
    sign = float(teeth[0]["sign_z"])
    upper = sign > 0
    gum_z = sign * abs(float(_get(config, "gum_height", 2.0 if upper else 1.7)))
    base_z = sign * abs(float(_get(config, "base_height", 2.5 if upper else 2.3)))
    if sign * (base_z - gum_z) <= .10:
        raise ValueError("base_height must lie beyond gum_height, away from the bite")
    sides = max(6, int(_get(config, "gum_cell_resolution", 12)))
    radial_steps = max(2, int(_get(config, "gum_radial_resolution", 4)))
    papilla = float(_get(config, "gum_papilla_height", .22))
    collar_ratio = float(_get(config, "gum_collar_ratio", .70))
    socket_depth = float(_get(config, "gum_socket_depth", .48))
    outer_override = _get(config, "gum_outer_width", None)
    inner_override = _get(config, "gum_inner_width", None)
    s_values = [float(t["s"]) for t in teeth]
    # Use a little more than half a molar width beyond the terminal centre.
    # Do not clip to max_s: some arch implementations use it for centres.
    bounds = [s_values[0] - .57 * teeth[0]["w"]]
    bounds.extend((a + b) * .5 for a, b in zip(s_values[:-1], s_values[1:]))
    bounds.append(s_values[-1] + .57 * teeth[-1]["w"])
    span = bounds[-1] - bounds[0]

    def interp(s, key):
        i = bisect.bisect_right(s_values, s)
        if i == 0:
            return float(teeth[0][key])
        if i == len(teeth):
            return float(teeth[-1][key])
        f = (s - s_values[i - 1]) / (s_values[i] - s_values[i - 1])
        f = f * f * (3.0 - 2.0 * f)
        return float(teeth[i - 1][key]) * (1.0 - f) + float(teeth[i][key]) * f

    def widths(s):
        d = interp(s, "d")
        return (float(inner_override) if inner_override is not None else d * .5 + .10,
                float(outer_override) if outer_override is not None else d * .5 + .14)

    def margin(s, v):
        i = bisect.bisect_right(s_values, s)
        if i == 0:
            f = (s_values[0] - s) / (s_values[0] - bounds[0])
            dip = papilla * .8 * math.sin(.5 * math.pi * min(1.0, f)) ** 2
        elif i == len(teeth):
            f = (s - s_values[-1]) / (bounds[-1] - s_values[-1])
            dip = papilla * .8 * math.sin(.5 * math.pi * min(1.0, f)) ** 2
        else:
            f = (s - s_values[i - 1]) / (s_values[i] - s_values[i - 1])
            dip = papilla * math.sin(math.pi * f) ** 2
        inner, outer = widths(s)
        radius = outer if v >= 0 else inner
        return interp(s, "cerv") - sign * dip + sign * .055 * (abs(v) / radius) ** 1.7

    def world(s, v, z):
        center, _tangent, normal = arch.frame(s)
        return (center[0] + normal[0] * v, center[1] + normal[1] * v, z)

    vertices, faces, face_uv = [], [], []
    vertex_lookup = {}
    parameters = {}
    collar_vertices = set()

    def vertex(co, parameter=None):
        key = tuple(round(float(c), 7) for c in co)
        index = vertex_lookup.get(key)
        if index is None:
            index = len(vertices)
            vertices.append(tuple(float(c) for c in co))
            vertex_lookup[key] = index
            if parameter is not None:
                parameters[index] = parameter
        elif parameter is not None and index not in parameters:
            parameters[index] = parameter
        return index

    def uv(s, v):
        return ((s - bounds[0]) / span, v)

    def face(indices, texcoords):
        if len(set(indices)) >= 3:
            faces.append(tuple(indices))
            face_uv.append(tuple(texcoords))

    def boundary_point(left, right, side, f):
        if side == 0:
            s = right
            inner, outer = widths(s)
            v = -inner + (inner + outer) * f
        elif side == 1:
            s = right + (left - right) * f
            v = widths(s)[1]
        elif side == 2:
            s = left
            inner, outer = widths(s)
            v = outer - (inner + outer) * f
        else:
            s = left + (right - left) * f
            v = -widths(s)[0]
        return s, v

    for tooth_index, tooth in enumerate(teeth):
        left, right = bounds[tooth_index:tooth_index + 2]
        samples = [boundary_point(left, right, side, k / sides)
                   for side in range(4) for k in range(sides)]
        collar = []
        for s, v in samples:
            angle = math.atan2(v, s - tooth["s"])
            ca, sa = math.cos(angle), math.sin(angle)
            # A softly squared socket matches a crown neck, unlike circles.
            local_u = collar_ratio * tooth["w"] * .5 * math.copysign(abs(ca) ** .70, ca)
            local_v = collar_ratio * tooth["d"] * .5 * math.copysign(abs(sa) ** .70, sa)
            z = tooth["cerv"] - sign * papilla * abs(ca) ** 2.4
            center, tangent, normal = tooth["center"], tooth["tangent"], tooth["normal"]
            x = center[0] + tangent[0] * local_u + normal[0] * local_v
            y = center[1] + tangent[1] * local_u + normal[1] * local_v
            collar.append(((x, y, z), tooth["s"] + local_u, local_u, local_v))

        previous_ring = None
        first_ring = None
        for ring_number in range(radial_steps + 1):
            f = ring_number / radial_steps
            ring, ring_s = [], []
            for (s, v), (collar_co, collar_s, _u, _v) in zip(samples, collar):
                target = world(s, v, margin(s, v))
                co = tuple(a * (1.0 - f) + b * f for a, b in zip(collar_co, target))
                # Gentle convex interstitial tissue, without spherical lobes.
                co = (co[0], co[1], co[2] + sign * .035 * math.sin(math.pi * f))
                parameter = (s, v) if ring_number == radial_steps else None
                index = vertex(co, parameter)
                ring.append(index)
                ring_s.append(collar_s * (1.0 - f) + s * f)
            if previous_ring is not None:
                for k in range(len(ring)):
                    q = (k + 1) % len(ring)
                    face((previous_ring[k], previous_ring[q], ring[q], ring[k]),
                         (uv(previous_s[k], 0), uv(previous_s[q], 0), uv(ring_s[q], 0), uv(ring_s[k], 0)))
            else:
                first_ring = ring
                collar_vertices.update(ring)
            previous_ring, previous_s = ring, ring_s

        # The mouth of a socket remains open, while its internal wall and
        # rounded bottom make the whole gingival solid closed/manifold.
        previous_ring = first_ring
        for depth_f, radius_f in ((.20, .98), (.52, .84), (.82, .58), (1.0, .22)):
            ring = []
            for (co, collar_s, local_u, local_v) in collar:
                center, tangent, normal = tooth["center"], tooth["tangent"], tooth["normal"]
                x = center[0] + radius_f * (tangent[0] * local_u + normal[0] * local_v)
                y = center[1] + radius_f * (tangent[1] * local_u + normal[1] * local_v)
                z = co[2] + sign * socket_depth * depth_f
                ring.append(vertex((x, y, z)))
            for k in range(len(ring)):
                q = (k + 1) % len(ring)
                face((previous_ring[q], previous_ring[k], ring[k], ring[q]),
                     (uv(collar[q][1], 0), uv(collar[k][1], 0), uv(collar[k][1], 0), uv(collar[q][1], 0)))
            previous_ring = ring
        center_index = vertex((tooth["center"][0], tooth["center"][1],
                               tooth["cerv"] + sign * (socket_depth + .025)))
        for k in range(len(previous_ring)):
            q = (k + 1) % len(previous_ring)
            face((previous_ring[q], previous_ring[k], center_index),
                 (uv(collar[q][1], 0), uv(collar[k][1], 0), uv(tooth["s"], 0)))

    # Find only the outside perimeter: socket edges already have two faces.
    edge_count = {}
    edge_direction = {}
    for polygon in faces:
        for a, b in zip(polygon, polygon[1:] + polygon[:1]):
            key = (min(a, b), max(a, b))
            edge_count[key] = edge_count.get(key, 0) + 1
            edge_direction[key] = (a, b)
    perimeter = [edge_direction[key] for key, count in edge_count.items() if count == 1]
    perimeter_vertices = {i for edge in perimeter for i in edge}
    if not all(i in parameters for i in perimeter_vertices):
        raise RuntimeError("Socket patch contains an unexpected unwelded boundary")

    # Broad, mostly flat sidewalls with a rounded shoulder and foot.  The
    # final V=.60..1 section is the integrated lavender base material.
    wall_rows = ((.07, .025, .055), (.22, .060, .16), (.52, .080, .35),
                 (.82, .075, .51), (1.0, .065, .60),
                 (1.12, .070, .68), (1.72, .065, .87),
                 (1.94, .035, .97), (2.0, .0, 1.0))

    def wall_coordinate(index, level, flare):
        s, v = parameters[index]
        inner, outer = widths(s)
        v_new = v * (1.0 + flare / max(inner, outer))
        original_z = vertices[index][2]
        if level <= 1.0:
            z = original_z * (1.0 - level) + gum_z * level
        else:
            f = level - 1.0
            z = gum_z * (1.0 - f) + base_z * f
        return world(s, v_new, z)

    previous = {i: i for i in perimeter_vertices}
    previous_v = 0.0
    for level, flare, material_v in wall_rows:
        row = {i: vertex(wall_coordinate(i, level, flare)) for i in perimeter_vertices}
        for a, b in perimeter:
            sa, _ = parameters[a]
            sb, _ = parameters[b]
            face((previous[b], previous[a], row[a], row[b]),
                 (uv(sb, previous_v), uv(sa, previous_v), uv(sa, material_v), uv(sb, material_v)))
        previous, previous_v = row, material_v

    # Flat horseshoe underside.  Cell boundaries coincide with the wall
    # perimeter and one another, with no internal duplicate surfaces.
    for cell in range(len(teeth)):
        left, right = bounds[cell:cell + 2]
        grid = []
        grid_s = []
        for i in range(sides + 1):
            s = left + (right - left) * i / sides
            inner, outer = widths(s)
            grid.append([vertex(world(s, -inner + (inner + outer) * j / sides, base_z))
                         for j in range(sides + 1)])
            grid_s.append(s)
        for i in range(sides):
            for j in range(sides):
                face((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]),
                     (uv(grid_s[i], 1), uv(grid_s[i + 1], 1), uv(grid_s[i + 1], 1), uv(grid_s[i], 1)))

    mesh = bpy.data.meshes.new(f"{arch_name}_continuous_socketed_gum_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    layer = mesh.uv_layers.new(name="Gum_Base_Gradient")
    for polygon, coords in zip(mesh.polygons, face_uv):
        for loop_index, coord in zip(polygon.loop_indices, coords):
            layer.data[loop_index].uv = coord
    # Recalculate after assembling the manifold; this also handles upper
    # and lower surfaces without maintaining two separate winding rules.
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    non_manifold = sum(not e.is_manifold for e in bm.edges)
    bm.to_mesh(mesh)
    bm.free()
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    mesh.update()
    obj = bpy.data.objects.new(f"{arch_name}_Gum_and_Lavender_Base", mesh)
    bpy.context.collection.objects.link(obj)
    if material is not None:
        mesh.materials.append(material)
    obj["construction"] = "Continuous socketed horseshoe with integrated base"
    obj["socket_count"] = len(teeth)
    obj["non_manifold_edges"] = non_manifold
    mesh.calc_loop_triangles()
    obj["triangle_count"] = len(mesh.loop_triangles)
    return obj
