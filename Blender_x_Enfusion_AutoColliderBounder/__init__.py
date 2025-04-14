bl_info = {
    "name": "Enfusion Tools - [Addon] Auto Collider Bounder",
    "author": "'AntiPoney' Jérôme Noël",
    "version": (1, 1),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Colliders Tools",
    "description": "Automatically add a collider to the selected object and set it to the correct size.",
    "category": "Import-Export",
    "doc_url": "https://github.com/AntiPoney/Blender_x_Enfusion_AutoColliderBounder",
    "tracker_url": "https://github.com/AntiPoney/Blender_x_Enfusion_AutoColliderBounder/issues",
}

import bpy
import os

# Register and Unregister
def register():
    from . import AutoColliderBounder
    AutoColliderBounder.register()

def unregister():
    from . import AutoColliderBounder
    AutoColliderBounder.unregister()

if __name__ == "__main__":
    register()