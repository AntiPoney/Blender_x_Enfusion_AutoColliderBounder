import bpy, bmesh, math, importlib, sys, re
from mathutils import Vector

EnfusionCoreUtils = None

if "EnfusionBlenderTools" in sys.modules:
    EnfusionToolsKit = sys.modules["EnfusionBlenderTools"]
    EnfusionCoreUtils = importlib.import_module("EnfusionBlenderTools.core.utils")
    EnfusionCoreColCache = importlib.import_module("EnfusionBlenderTools.core.collider_cache")
    EnfusionColliderSetupCache = EnfusionCoreColCache.ColliderSetupCache


LOD_STRING_PATTERN = re.compile(r'.*_LOD\d$', re.IGNORECASE)

def get_bounding_box(obj):
    """Return world-space min and max corners, size and center of the object's bounding box."""
    world_matrix = obj.matrix_world
    bbox_corners = [world_matrix @ Vector(corner) for corner in obj.bound_box]
    min_corner = Vector((min(v.x for v in bbox_corners),
                         min(v.y for v in bbox_corners),
                         min(v.z for v in bbox_corners)))
    max_corner = Vector((max(v.x for v in bbox_corners),
                         max(v.y for v in bbox_corners),
                         max(v.z for v in bbox_corners)))
    size = max_corner - min_corner
    center = (min_corner + max_corner) * 0.5
    return min_corner, max_corner, size, center

def center_origin_to_geometry(obj):
    """Center the object's origin to its geometry."""
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    
# get the world pos of the reference Obj and set the origin of the obj to that position
def set_origin_from_other_object(referenceObj, obj):
    """Set the origin of obj to the world position of referenceObj."""
    reference_world_pos = referenceObj.matrix_world @ referenceObj.location
    obj.location = reference_world_pos
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

def get_or_create_collider_material():
    """Return a material named 'col' (yellow, 10% opacity)"""
    mat_name = "col"
    mat = bpy.data.materials.get(mat_name)
    if mat is None:
        mat = bpy.data.materials.new(name=mat_name)
        mat.diffuse_color = (1.0, 1.0, 0.0, 0.1)  # Yellow, 10% opacity
        if hasattr(mat, "blend_method"):
            mat.blend_method = 'BLEND'
    return mat

def assign_collider_material(obj):
    """Assign the 'col' material to the object."""
    mat = get_or_create_collider_material()
    if obj.data.materials:
        obj.data.materials.clear()
    obj.data.materials.append(mat)

def link_to_source_collections(new_obj, source_obj):
    """Link new_obj to each collection that source_obj is in."""
    for coll in source_obj.users_collection:
        if new_obj.name not in coll.objects:
            coll.objects.link(new_obj)

def parent_to_source(new_obj, source_obj):
    """Parent new_obj to source_obj and fix transform."""
    new_obj.parent = source_obj
    new_obj.matrix_parent_inverse = source_obj.matrix_world.inverted()

# Basic collider creation functions (box, sphere, cylinder, capsule, convex, and triangle)
def create_box_collider(size, center, src_name):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=center)
    new_obj = bpy.context.active_object
    new_obj.name = "UBX_" + src_name
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(new_obj.data)
    for v in bm.verts:
        v.co.x *= size.x
        v.co.y *= size.y
        v.co.z *= size.z
    bmesh.update_edit_mesh(new_obj.data)
    bpy.ops.object.mode_set(mode='OBJECT')
    return new_obj

def create_sphere_collider(size, center, src_name):
    r = max(size.x, size.y, size.z) / 2.0
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=center)
    new_obj = bpy.context.active_object
    new_obj.name = "USP_" + src_name
    return new_obj

def create_cylinder_collider(size, center, src_name):
    radius = max(size.x, size.y) / 2.0
    height = size.z
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=height, location=center)
    new_obj = bpy.context.active_object
    new_obj.name = "UCL_" + src_name
    return new_obj

def create_capsule_collider(size, center, src_name):
    r = min(size.x, size.y) / 2.0
    h = size.z - 2 * r
    if h < 0:
        collider = create_sphere_collider(size, center, src_name)
        collider.name = "UCS_" + src_name
        return collider
    cyl_center = center.copy()
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, location=cyl_center)
    cyl_obj = bpy.context.active_object
    cyl_obj.name = "temp_capsule_cylinder"
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
    bpy.ops.object.select_all(action='DESELECT')
    cyl_obj.select_set(True)
    sphere_top.select_set(True)
    sphere_bottom.select_set(True)
    bpy.context.view_layer.objects.active = cyl_obj
    bpy.ops.object.join()
    new_obj = bpy.context.active_object
    new_obj.name = "UCS_" + src_name
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.remove_doubles(threshold=0.0001)
    bpy.ops.object.mode_set(mode='OBJECT')
    return new_obj

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



# --- Operator that shows a popup dialog to choose collider type and collider usage ---
class OBJECT_OT_create_collider(bpy.types.Operator):


    """Create collider mesh with custom type and usage"""
    bl_idname = "object.create_collider"
    bl_label = "Create Collider"
    bl_options = {'REGISTER', 'UNDO'}

    # if the enfusion 
    if EnfusionCoreUtils is not None:
        
        collider_type : EnumProperty(
            name = "Collider Type",
            items=[
                ('UBX', "Box (UBX)", "Box collider"),
                ('USP', "Sphere (USP)", "Sphere collider"),
                ('UCL', "Cylinder (UCL)", "Cylinder collider"),
                ('UCS', "Capsule (UCS)", "Capsule collider"),
            ],
            default='UBX',
        )
        
        game_material_item : EnumProperty(
            name = "Game materials",
            items = EnfusionCoreColCache.get_game_mats_enum_callback
        ) #type: ignore

        layer_preset_item : EnumProperty(
            name = "Layer Presets",
            items = EnfusionCoreColCache.get_layer_presets_enum_callback
        ) 
        
        
    # if layer_presets is None, then we need to abort the operation
    if (game_material_item is None) or (layer_preset_item is None):
        raise RuntimeError("something went wrong while calling Enfusion Tools. Please report the issue.")
    
    def invoke(self, context, event):
        
        self.set_game_material_invoke(context)
        self.set_layer_preset_invoke(context)

        return context.window_manager.invoke_props_dialog(self)
    
    def set_layer_preset_invoke(self, context):
        active = context.active_object
        key = "None"

        if "usage" in active.keys():
            usage_attrib = active["usage"]
            key = usage_attrib

        self.layer_preset_item = key
    
    def set_game_material_invoke(self, context):
        active = context.active_object
        active_material = active.active_material
        
        material_name = active_material.name if active_material else "No change"
        
        material_name_to_enum_key = EnfusionColliderSetupCache.material_name_to_enum_key()
        key = material_name_to_enum_key.get(material_name, "No change")
        self.game_material_item = key

    def execute(self, context):
        
        selected_objects = context.selected_objects
        if not selected_objects:
            self.report({'WARNING'}, "No objects selected")
            return {'CANCELLED'}

        for obj in selected_objects:
            if obj.type != 'MESH':
                continue
            src_name = obj.name
            
            # if source name end with some sufixes, then we need to remove them (_LODx)
            if LOD_STRING_PATTERN.match(src_name):
                src_name = src_name[:-5]  # Remove the last 5 characters (_LODx)
                
            
            collider_obj = None
            _, _, size, center = get_bounding_box(obj)
            
            if self.collider_type == 'UBX':
                collider_obj = create_box_collider(size, center, src_name)
            elif self.collider_type == 'USP':
                collider_obj = create_sphere_collider(size, center, src_name)
            elif self.collider_type == 'UCL':
                collider_obj = create_cylinder_collider(size, center, src_name)
            elif self.collider_type == 'UCS':
                collider_obj = create_capsule_collider(size, center, src_name)

            if collider_obj:
                link_to_source_collections(collider_obj, obj)
                parent_to_source(collider_obj, obj)
                
                self.set_game_materials_exec(collider_obj)
                self.set_layer_presets_exec(collider_obj)
                
                self.report({'INFO'},
                    f"Created collider '{collider_obj.name}' with usage '{self.layer_preset_item}'")
                
        return {'FINISHED'}
    
    def set_game_materials_exec(self, obj):
        key = self.game_material_item

        if key == 'No change':
            return 

        chosen_material_name = EnfusionColliderSetupCache._gamemat_enum_key_to_material_name[key]
        material = bpy.data.materials.get(chosen_material_name)

        if material is None:
            material = get_random_colored_material(chosen_material_name)

        
        obj.data.materials.clear()
        obj.data.materials.append(material)

    def set_layer_presets_exec(self, obj):
        obj["usage"] = self.layer_preset_item


class OBJECT_OT_convert_to_collider(bpy.types.Operator):


    """Convert the current object to a collider"""
    bl_idname = "object.convert_to_collider"
    bl_label = "Convert to Collider"
    bl_options = {'REGISTER', 'UNDO'}
    
    collider_type : EnumProperty(
            name = "Collider Type",
            items=[
                ('UBX', "Box (UBX)", "Box collider"),
                ('USP', "Sphere (USP)", "Sphere collider"),
                ('UCL', "Cylinder (UCL)", "Cylinder collider"),
                ('UCS', "Capsule (UCS)", "Capsule collider"),
                ('UCX', "Convex (UCX)", "Convex collider"),
                ('UTM', "Triangle (UTM)", "Triangle collider"),
            ],
            default='UBX',
        )
    
    def invoke(self, context, event):
        # Pop up a dialog to let the user set the properties.
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        selected_objects = context.selected_objects
        if not selected_objects:
            self.report({'WARNING'}, "No objects selected")
            return {'CANCELLED'}

        for obj in selected_objects:
            if obj.type != 'MESH':
                continue
            
            ''' if the collider type to convert is UTM, then we need to triangulate the mesh first '''
            if self.collider_type == 'UTM':
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
                bpy.ops.mesh.quads_convert_to_tris()
                bpy.ops.object.mode_set(mode='OBJECT')
                
                
            ''' modify the name of the object to the new collider type + the original name ''' 
            oldObjName = obj.name
            
            # if source name end with _LOD sufixes, then we need to remove them (_LODx, )
            if LOD_STRING_PATTERN.match(oldObjName):
                oldObjName = oldObjName[:-5]  # Remove the last 5 characters (_LODx)
            
            obj.name = self.collider_type + "_" + oldObjName
            
            ''' set the usage of the collider to the new usage '''
            obj["usage"] = self.collider_usage
            
            ''' finally we need to assign the collider material to the object '''
            assign_collider_material(obj)
            
        return {'FINISHED'}

class OBJECT_OT_modify_to_type(bpy.types.Operator):
    
    
class OBJECT_OT_modify_to_layer(bpy.types.Operator):
class OBJECT_OT_modify_to_material(bpy.types.Operator):

# --- UI Panel to run the operator ---
class VIEW3D_PT_collider_panel(bpy.types.Panel):
    bl_label = "Colliders Tools"
    bl_idname = "VIEW3D_PT_collider_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Enfusion Tools"

    def draw(self, context):
        layout = self.layout
        layout.operator("object.create_collider", text="Create Collider")
        layout.operator("object.convert_to_collider", text="Convert to Collider")
        layout.operator("object.modify_to_type", text="Modify Type")
        layout.operator("object.modify_to_layer", text="Modify Layer")
        layout.operator("object.modify_to_material", text="Modify Material")
    

classes = (
    OBJECT_OT_create_collider,
    OBJECT_OT_convert_to_collider,
    VIEW3D_PT_collider_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)