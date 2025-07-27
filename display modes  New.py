bl_info = {
    "name": "Display Mode Picker",
    "author": "Venkatesh sanku",
    "version": (1, 0),
    "blender": (3, 4, 0),
    "location": "View3D > Sidebar > Quick Tools Tab",
    "description": "Panel to switch display mode of mesh objects and select all objects and collections",
    "category": "3D View",
}

import bpy

# -----------------------------
# Collection Picker + Panel UI
# -----------------------------

class VIEW3D_PT_display(bpy.types.Panel):
    bl_label = "Display Modes"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Quick Tools"

    def draw(self, context):
        layout = self.layout

        # Select All Objects & Collections button at the top, highlighted
        row = layout.row()
        row.scale_y = 1.2
        row.operator("object.select_all_objects_and_collections", text="Select All Objects & Collections", icon="RESTRICT_SELECT_OFF")

        layout.separator()

        # Box for Selected Objects Display Modes
        box = layout.box()
        box.label(text="Selected Objects Display Mode", icon='RESTRICT_SELECT_OFF')
        col = box.column(align=True)

        col.operator("mesh.display_solid_selected", text="Solid Selected", icon="SHADING_SOLID")
        col.operator("mesh.display_wire_selected", text="Wire Selected", icon="MOD_WIREFRAME")
        col.operator("mesh.display_bounds_selected", text="Bounds Selected", icon="PIVOT_BOUNDBOX")

        layout.separator()

        # Box for All Objects Display Modes
        box = layout.box()
        box.label(text="All Objects Display Mode", icon='OUTLINER_DATA_MESH')
        col = box.column(align=True)

        col.operator("mesh.display_solid_all", text="All Solid", icon="SHADING_SOLID")
        col.operator("mesh.display_wire_all", text="All Wire", icon="MOD_WIREFRAME")
        col.operator("mesh.display_bounds_all", text="All Bounds", icon="PIVOT_BOUNDBOX")

# -----------------------------
# Utility: Get selected or dropdown collection meshes
# -----------------------------

def get_outliner_selected_collections():
    """Get collections explicitly selected (blue highlight) in the Outliner"""
    selected_collections = []
    
    for window in bpy.context.window_manager.windows:
        screen = window.screen
        for area in screen.areas:
            if area.type == 'OUTLINER':
                with bpy.context.temp_override(window=window, screen=screen, area=area):
                    outliner_context = bpy.context
                    if hasattr(outliner_context, 'selected_ids'):
                        for item in outliner_context.selected_ids:
                            if isinstance(item, bpy.types.Collection):
                                selected_collections.append(item)
                                print(f"[OUTLINER] Found selected collection: {item.name}")
    
    if not selected_collections:
        print("[OUTLINER] No collections in selected_ids")
    
    return selected_collections

def get_selected_meshes_and_collections(context):
    """
    Returns a list of unique mesh objects:
    - From selected objects in the 3D viewport
    - From collections explicitly selected in the Outliner (blue highlight)
    - From active collection if no viewport objects are selected
    """
    processed = set()
    result = []

    print(f"\n=== VIEWPORT SELECTED OBJECTS ===")
    for obj in context.selected_objects:
        if obj.type == 'MESH' and obj.name not in processed:
            result.append(obj)
            processed.add(obj.name)
            print(f"[VIEWPORT] Added {obj.name}")

    print(f"\n=== OUTLINER SELECTED COLLECTIONS ===")
    selected_collections = get_outliner_selected_collections()
    
    if selected_collections:
        for collection in selected_collections:
            print(f"[COLLECTION] Processing {collection.name}")
            for obj in collection.objects:
                if obj.type == 'MESH' and obj.name not in processed:
                    result.append(obj)
                    processed.add(obj.name)
                    print(f"  - Added {obj.name} from collection")
    else:
        if not context.selected_objects:
            active_collection = bpy.context.view_layer.active_layer_collection
            if active_collection and active_collection.collection:
                collection = active_collection.collection
                print(f"[OUTLINER] No selected collections, using active collection: {collection.name}")
                print(f"[COLLECTION] Processing {collection.name}")
                for obj in collection.objects:
                    if obj.type == 'MESH' and obj.name not in processed:
                        result.append(obj)
                        processed.add(obj.name)
                        print(f"  - Added {obj.name} from collection")
        else:
            print("No collections selected in Outliner")

    print(f"Total objects to process: {len(result)}")
    return result

# -----------------------------
# Operators
# -----------------------------

# --- New operator: Select all objects and collections ---
class OBJECT_OT_select_all_objects_and_collections(bpy.types.Operator):
    bl_idname = "object.select_all_objects_and_collections"
    bl_label = "Select All Objects and Collections"
    bl_description = "Select all objects and activate all collections in the scene"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Select all objects
        bpy.ops.object.select_all(action='SELECT')
        obj_count = len(context.scene.objects)

        # Activate all collections in the current view layer
        for layer_collection in context.view_layer.layer_collection.children:
            # Recursively activate collections
            self.activate_collection_recursive(layer_collection)

        # Also activate the root collection
        context.view_layer.layer_collection.exclude = False
        context.view_layer.layer_collection.hide_viewport = False

        self.report({'INFO'}, f"Selected {obj_count} objects and activated collections")
        print(f"Selected {obj_count} objects and activated all collections in view layer")

        return {'FINISHED'}

    def activate_collection_recursive(self, layer_collection):
        """Recursively unhide and include collections in view layer"""
        layer_collection.exclude = False
        layer_collection.hide_viewport = False
        for child in layer_collection.children:
            self.activate_collection_recursive(child)

# === ALL OBJECTS OPERATORS ===

class MESH_OT_display_bounds_all(bpy.types.Operator):
    bl_idname = "mesh.display_bounds_all"
    bl_label = "All Bounds"
    bl_description = "Set the display type of all meshes in the scene to bounds"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        for obj in context.scene.objects:
            if obj.type == 'MESH':
                obj.display_type = 'BOUNDS'
        return {'FINISHED'}

class MESH_OT_display_wire_all(bpy.types.Operator):
    bl_idname = "mesh.display_wire_all"
    bl_label = "All Wire"
    bl_description = "Set the display type of all meshes in the scene to wire"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        for obj in context.scene.objects:
            if obj.type == 'MESH':
                obj.display_type = 'WIRE'
        return {'FINISHED'}

class MESH_OT_display_solid_all(bpy.types.Operator):
    bl_idname = "mesh.display_solid_all"
    bl_label = "All Solid"
    bl_description = "Set the display type of all meshes in the scene to solid"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        for obj in context.scene.objects:
            if obj.type == 'MESH':
                obj.display_type = 'SOLID'
        return {'FINISHED'}

# === SELECTED OBJECTS OPERATORS ===

class MESH_OT_display_bounds_selected(bpy.types.Operator):
    bl_idname = "mesh.display_bounds_selected"
    bl_label = "Selected Bounds"
    bl_description = "Set the display type of selected meshes and collection-picked meshes to bounds"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        count = 0
        meshes = get_selected_meshes_and_collections(context)
        for obj in meshes:
            obj.display_type = 'BOUNDS'
            print(f"-> {obj.name} now set to BOUNDS")
            count += 1
        print(f"Set {count} objects to BOUNDS display")
        return {'FINISHED'}

class MESH_OT_display_wire_selected(bpy.types.Operator):
    bl_idname = "mesh.display_wire_selected"
    bl_label = "Selected Wire"
    bl_description = "Set the display type of selected meshes and collection-picked meshes to wire"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        count = 0
        meshes = get_selected_meshes_and_collections(context)
        for obj in meshes:
            obj.display_type = 'WIRE'
            print(f"-> {obj.name} now set to WIRE")
            count += 1
        print(f"Set {count} objects to WIRE display")
        return {'FINISHED'}

class MESH_OT_display_solid_selected(bpy.types.Operator):
    bl_idname = "mesh.display_solid_selected"
    bl_label = "Selected Solid"
    bl_description = "Set the display type of selected meshes and collection-picked meshes to solid"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        count = 0
        meshes = get_selected_meshes_and_collections(context)
        for obj in meshes:
            print(f"-> {obj.name} (was: {obj.display_type}) -> setting to SOLID")
            obj.display_type = 'SOLID'
            print(f"? {obj.name} now: {obj.display_type}")
            count += 1
        print(f"Set {count} objects to SOLID display")
        return {'FINISHED'}

# -----------------------------
# Registration
# -----------------------------

classes = (
    VIEW3D_PT_display,
    OBJECT_OT_select_all_objects_and_collections,
    MESH_OT_display_bounds_all,
    MESH_OT_display_wire_all,
    MESH_OT_display_solid_all,
    MESH_OT_display_bounds_selected,
    MESH_OT_display_wire_selected,
    MESH_OT_display_solid_selected,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()