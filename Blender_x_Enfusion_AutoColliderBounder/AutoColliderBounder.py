import bpy, bmesh, math
from mathutils import Vector

def get_bounding_box(obj):
    """Return world-space min and max corners, size and center of the object's bounding box."""
    world_matrix = obj.matrix_world
    bbox_corners = [world_matrix @ Vector(corner) for corner in obj.bound_box]
    min_corner = Vector((
        min(v.x for v in bbox_corners),
        min(v.y for v in bbox_corners),
        min(v.z for v in bbox_corners)
    ))
    max_corner = Vector((
        max(v.x for v in bbox_corners),
        max(v.y for v in bbox_corners),
        max(v.z for v in bbox_corners)
    ))
    size = max_corner - min_corner
    center = (min_corner + max_corner) * 0.5
    return min_corner, max_corner, size, center

def get_or_create_collider_material():
    """Return a material named 'col' (yellow, 10% opacity), creating it if necessary."""
    mat_name = "col"
    mat = bpy.data.materials.get(mat_name)
    if mat is None:
        mat = bpy.data.materials.new(name=mat_name)
        # Set diffuse color to yellow, with alpha 0.1 (10% opacity)
        mat.diffuse_color = (1.0, 1.0, 0.0, 0.1)
        # For Eevee or Cycles, set blend mode to allow transparency.
        if hasattr(mat, "blend_method"):
            mat.blend_method = 'BLEND'
    return mat

def assign_collider_material(obj):
    """Assign the 'col' material to the collider object."""
    mat = get_or_create_collider_material()
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)

def link_to_source_collection(new_obj, source_obj):
    """Link new_obj to every collection that the source_obj is in."""
    for coll in source_obj.users_collection:
        if new_obj.name not in coll.objects:
            coll.objects.link(new_obj)

def create_box_collider(size, center, src_name):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=center)
    new_obj = bpy.context.active_object
    new_obj.name = "UBX_" + src_name
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(new_obj.data)
    for v in bm.verts:
        # The default cube vertices are in [-0.5, 0.5]; scale to match size
        v.co.x *= size.x
        v.co.y *= size.y
        v.co.z *= size.z
    bmesh.update_edit_mesh(new_obj.data)
    bpy.ops.object.mode_set(mode='OBJECT')
    return new_obj

def create_sphere_collider(size, center, src_name):
    # Use half of the largest dimension as radius.
    r = max(size.x, size.y, size.z) / 2.0
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=center)
    new_obj = bpy.context.active_object
    new_obj.name = "USP_" + src_name
    return new_obj

def create_cylinder_collider(size, center, src_name):
    # Cylinder oriented along Z.
    radius = max(size.x, size.y) / 2.0
    height = size.z
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=height, location=center)
    new_obj = bpy.context.active_object
    new_obj.name = "UCL_" + src_name
    return new_obj

def create_capsule_collider(size, center, src_name):
    # Capsule along Z.
    # Use the minimum of X,Y extents for the radius.
    r = min(size.x, size.y) / 2.0
    # Determine cylinder height: if size.z is larger than 2*r, create a cylindrical mid-part.
    h = size.z - 2 * r
    if h < 0:
        # If no room for a cylinder, fallback to sphere.
        collider = create_sphere_collider(size, center, src_name)
        collider.name = "UCS_" + src_name
        return collider

    # Create cylinder part.
    cyl_center = center.copy()
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, location=cyl_center)
    cyl_obj = bpy.context.active_object
    cyl_obj.name = "temp_capsule_cylinder"
    
    # Create top hemisphere.
    top_center = center + Vector((0, 0, h/2))
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=top_center)
    sphere_top = bpy.context.active_object
    sphere_top.name = "temp_capsule_sphere_top"
    bpy.ops.object.mode_set(mode='EDIT')
    bm_top = bmesh.from_edit_mesh(sphere_top.data)
    verts_to_delete = [v for v in bm_top.verts if (sphere_top.matrix_world @ v.co).z < top_center.z]
    bmesh.ops.delete(bm_top, geom=verts_to_delete, context='VERTS')
    bmesh.update_edit_mesh(sphere_top.data)
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Create bottom hemisphere.
    bottom_center = center - Vector((0, 0, h/2))
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=bottom_center)
    sphere_bottom = bpy.context.active_object
    sphere_bottom.name = "temp_capsule_sphere_bottom"
    bpy.ops.object.mode_set(mode='EDIT')
    bm_bot = bmesh.from_edit_mesh(sphere_bottom.data)
    verts_to_delete = [v for v in bm_bot.verts if (sphere_bottom.matrix_world @ v.co).z > bottom_center.z]
    bmesh.ops.delete(bm_bot, geom=verts_to_delete, context='VERTS')
    bmesh.update_edit_mesh(sphere_bottom.data)
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Join the three parts.
    bpy.ops.object.select_all(action='DESELECT')
    cyl_obj.select_set(True)
    sphere_top.select_set(True)
    sphere_bottom.select_set(True)
    bpy.context.view_layer.objects.active = cyl_obj
    bpy.ops.object.join()
    new_obj = bpy.context.active_object
    new_obj.name = "UCS_" + src_name

    # Optional: Merge doubles along the joins.
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.remove_doubles(threshold=0.0001)
    bpy.ops.object.mode_set(mode='OBJECT')
    
    return new_obj

def create_convex_collider(src_obj, src_name):
    # Duplicate the object and compute its convex hull.
    new_obj = src_obj.copy()
    new_obj.data = src_obj.data.copy()
    new_obj.name = "UCX_" + src_name
    bpy.context.collection.objects.link(new_obj)
    bpy.context.view_layer.objects.active = new_obj
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(new_obj.data)
    bmesh.ops.convex_hull(bm, input=bm.verts)
    bmesh.update_edit_mesh(new_obj.data)
    bpy.ops.object.mode_set(mode='OBJECT')
    return new_obj

def create_triangle_collider(src_obj, src_name):
    # Duplicate the object and convert its faces to triangles.
    new_obj = src_obj.copy()
    new_obj.data = src_obj.data.copy()
    new_obj.name = "UTM_" + src_name
    bpy.context.collection.objects.link(new_obj)
    bpy.context.view_layer.objects.active = new_obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.quads_convert_to_tris()
    bpy.ops.object.mode_set(mode='OBJECT')
    return new_obj

class OBJECT_OT_create_collider(bpy.types.Operator):
    """Create a collider mesh around the selected object(s)."""
    bl_idname = "object.create_collider"
    bl_label = "Create Collider"
    bl_options = {'REGISTER', 'UNDO'}

    collider_type: bpy.props.EnumProperty(
        name="Collider Type",
        items=[
            ('UBX', "Box (UBX)", "Box collider based on bounding box"),
            ('UCS', "Capsule (UCS)", "Capsule collider based on bounding box"),
            ('USP', "Sphere (USP)", "Sphere collider based on bounding box"),
            ('UCL', "Cylinder (UCL)", "Cylinder collider based on bounding box"),
            ('UCX', "Convex (UCX)", "Convex collider using convex hull of the mesh"),
            ('UTM', "Triangle (UTM)", "Collider made of triangles (triangulated mesh)"),
        ]
    )

    def execute(self, context):
        selected_objects = context.selected_objects
        if not selected_objects:
            self.report({'WARNING'}, "No objects selected")
            return {'CANCELLED'}

        for obj in selected_objects:
            if obj.type != 'MESH':
                continue

            src_name = obj.name
            collider_obj = None
            
            if self.collider_type in {'UBX', 'USP', 'UCL', 'UCS'}:
                # Use bounding box data for these collider types.
                _, _, size, center = get_bounding_box(obj)

                if self.collider_type == 'UBX':
                    collider_obj = create_box_collider(size, center, src_name)
                elif self.collider_type == 'USP':
                    collider_obj = create_sphere_collider(size, center, src_name)
                elif self.collider_type == 'UCL':
                    collider_obj = create_cylinder_collider(size, center, src_name)
                elif self.collider_type == 'UCS':
                    collider_obj = create_capsule_collider(size, center, src_name)
            elif self.collider_type == 'UCX':
                collider_obj = create_convex_collider(obj, src_name)
            elif self.collider_type == 'UTM':
                collider_obj = create_triangle_collider(obj, src_name)

            # Link the collider to the same collections as the source object.
            if collider_obj:
                link_to_source_collection(collider_obj, obj)
                # Also assign the collider material.
                assign_collider_material(collider_obj)

        return {'FINISHED'}

class VIEW3D_PT_collider_panel(bpy.types.Panel):
    bl_label = "Collider Tools"
    bl_idname = "VIEW3D_PT_collider_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Collider Tools"

    def draw(self, context):
        layout = self.layout
        layout.label(text="Create Collider for Selected Objects:")
        layout.operator("object.create_collider")

classes = (OBJECT_OT_create_collider, VIEW3D_PT_collider_panel)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
