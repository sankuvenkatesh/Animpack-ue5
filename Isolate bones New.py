bl_info = {
    "name": "Bone Isolation Tools",
    "author": "Venkatesh sanku",
    "version": (1, 0),
    "blender": (4, 0, 0),
    "location": "3D View > Sidebar > Venky Anim Toolz Tab",
    "description": "Hides/shows bones based on selection.",
    "category": "Animation",
}

import bpy

# --- Operators ---

class VIEW3D_OT_IsolateBones(bpy.types.Operator):
    bl_idname = "armature.isolate_bones"
    bl_label = "Isolate Selected Bones"
    bl_description = "Hide unselected bones. Show all if none selected."
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != 'ARMATURE':
            self.report({'WARNING'}, "Please select an armature object to isolate bones.")
            return {'CANCELLED'}
        prev_mode = obj.mode
        if prev_mode != 'POSE':
            bpy.ops.object.mode_set(mode='POSE')
        selected_names = {pb.name for pb in context.selected_pose_bones}
        any_selected = bool(selected_names)
        for pb in obj.pose.bones:
            pb.bone.hide = any_selected and pb.name not in selected_names
        if not any_selected:
            for pb in obj.pose.bones:
                pb.bone.hide = False
        if prev_mode != 'POSE':
            bpy.ops.object.mode_set(mode=prev_mode)
        return {'FINISHED'}

class VIEW3D_OT_ShowAllBones(bpy.types.Operator):
    bl_idname = "armature.show_all_bones"
    bl_label = "Show All Bones"
    bl_description = "Unhide all bones in active armature."
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != 'ARMATURE':
            self.report({'WARNING'}, "Please select an armature object to show all bones.")
            return {'CANCELLED'}
        prev_mode = obj.mode
        if prev_mode != 'POSE':
            bpy.ops.object.mode_set(mode='POSE')
        for pb in obj.pose.bones:
            pb.bone.hide = False
        if prev_mode != 'POSE':
            bpy.ops.object.mode_set(mode=prev_mode)
        return {'FINISHED'}

class VIEW3D_OT_SelectAllBones(bpy.types.Operator):
    bl_idname = "armature.select_all_bones"
    bl_label = "Select All Bones"
    bl_description = "Select all bones in active armature."
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != 'ARMATURE':
            self.report({'WARNING'}, "Please select an armature object to select bones.")
            return {'CANCELLED'}
        prev_mode = obj.mode
        if prev_mode != 'POSE':
            bpy.ops.object.mode_set(mode='POSE')
        bpy.ops.pose.select_all(action='SELECT')
        for pb in obj.pose.bones:
            pb.bone.hide = False
        if prev_mode != 'POSE':
            bpy.ops.object.mode_set(mode=prev_mode)
        return {'FINISHED'}

# --- Panel ---

class VIEW3D_PT_BoneIsolationPanel(bpy.types.Panel):
    bl_label = "Bone Isolation Tools"
    bl_idname = "VIEW3D_PT_bone_isolation_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Venky Anim Toolz"

    def draw(self, context):
        layout = self.layout

        box = layout.box()
        box.label(text="Bone Tools", icon='ARMATURE_DATA')

        col = box.column(align=True)
        col.operator("armature.isolate_bones", text="Isolate Selected", icon='RESTRICT_SELECT_OFF')
        col.operator("armature.show_all_bones", text="Show All Bones", icon='HIDE_OFF')
        col.operator("armature.select_all_bones", text="Select All Bones", icon='BONE_DATA')
        
        layout.separator()

# --- Registration ---

classes = (
    VIEW3D_OT_IsolateBones,
    VIEW3D_OT_ShowAllBones,
    VIEW3D_OT_SelectAllBones,
    VIEW3D_PT_BoneIsolationPanel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()