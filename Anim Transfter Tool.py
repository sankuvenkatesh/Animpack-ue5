# -*- coding: utf-8 -*-
bl_info = {
    "name": "Anim Tool Transfer",
    "author": "Venkatesh sanku",
    "version": (1, 0, 0),
    "blender": (4, 3, 2),
    "location": "View3D > Sidebar > Anim Tool Transfer",
    "description": (
        "This addon allows you to adjust the root controller position based on each action or set it in origin world space. "
        "Supports batch processing for multiple actions, making it easier to calculate character positions in game engines."
    ),
    "category": "Anim Tool Transfer",
    "license": "SPDX:GPL-3.0-or-later"
}

import bpy

# --- properties.py portion ---
class RMT_ControllerItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty()

class RMT_ActionItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Action Name")
    action: bpy.props.PointerProperty(type=bpy.types.Action)
    is_selected: bpy.props.BoolProperty(name="Select", default=False)

def get_torso_items(self, context):
    scene = context.scene
    ctrls = getattr(scene, "controllers", [])
    return [(ctrl.name, ctrl.name, "") for ctrl in ctrls]

def register_properties():
    bpy.types.Scene.rmt_selected_rig = bpy.props.PointerProperty(
        name="Rig", type=bpy.types.Object,
        update=lambda self, ctx: ctx.area.tag_redraw()
    )
    bpy.types.Scene.controllers = bpy.props.CollectionProperty(type=RMT_ControllerItem)
    bpy.types.Scene.controllers_index = bpy.props.IntProperty()
    bpy.types.Scene.axis_x = bpy.props.BoolProperty(name="X", default=True)
    bpy.types.Scene.axis_y = bpy.props.BoolProperty(name="Y", default=True)
    bpy.types.Scene.axis_z = bpy.props.BoolProperty(name="Z", default=False)
    bpy.types.Scene.rmt_torso_controller_enum = bpy.props.EnumProperty(
        name="Torso Controller",
        description="Select Target from added controllers",
        items=get_torso_items
    )
    bpy.types.Scene.rmt_root_controller_name = bpy.props.StringProperty(
        name="Root Controller",
        description="Search for root controller bone"
    )
    bpy.types.Scene.keep_in_world_origin = bpy.props.BoolProperty(
        name="Keep in World Origin",
        description="Keep root controller at world origin",
        default=False
    )
    bpy.types.Scene.rmt_action_items = bpy.props.CollectionProperty(type=RMT_ActionItem)
    bpy.types.Scene.rmt_batch_actions = bpy.props.CollectionProperty(type=RMT_ActionItem)
    # Optionally: bpy.types.Scene.empty_size = bpy.props.FloatProperty(name="Empty Size", default=0.2, min=0.01, max=10.0)

def unregister_properties():
    del bpy.types.Scene.rmt_selected_rig
    del bpy.types.Scene.controllers
    del bpy.types.Scene.controllers_index
    del bpy.types.Scene.axis_x
    del bpy.types.Scene.axis_y
    del bpy.types.Scene.axis_z
    del bpy.types.Scene.rmt_torso_controller_enum
    del bpy.types.Scene.rmt_root_controller_name
    del bpy.types.Scene.keep_in_world_origin
    del bpy.types.Scene.rmt_action_items
    del bpy.types.Scene.rmt_batch_actions
    # Optionally: del bpy.types.Scene.empty_size

# --- operators.py portion ---
class RMT_OT_AddController(bpy.types.Operator):
    bl_idname = "rmt.add_controller"
    bl_label = "Add Controllers"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        rig = scene.rmt_selected_rig
        if not rig or rig.type != 'ARMATURE':
            self.report({'WARNING'}, "Please select a valid rig (Armature).")
            return {'CANCELLED'}
        if context.mode != 'POSE':
            self.report({'WARNING'}, "Please switch to Pose Mode and select bones.")
            return {'CANCELLED'}
        selected_bones = context.selected_pose_bones
        if not selected_bones:
            self.report({'WARNING'}, "No bones selected.")
            return {'CANCELLED'}
        count = 0
        for bone in selected_bones:
            if not any(item.name == bone.name for item in scene.controllers):
                new_ctrl = scene.controllers.add()
                new_ctrl.name = bone.name
                count += 1
        scene.controllers_index = max(0, len(scene.controllers) - 1)
        self.report({'INFO'}, f"Added {count} controllers.")
        return {'FINISHED'}

class RMT_OT_ClearControllers(bpy.types.Operator):
    bl_idname = "rmt.clear_controllers"
    bl_label = "Clear All Controllers"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        scene.controllers.clear()
        collection = bpy.data.collections.get("RootMotionRefs")
        if collection:
            for obj in list(collection.objects):
                bpy.data.objects.remove(obj, do_unlink=True)
            bpy.data.collections.remove(collection)
        return {'FINISHED'}

class RMT_OT_RemoveController(bpy.types.Operator):
    bl_idname = "rmt.remove_controller"
    bl_label = "Remove Controller"
    bl_options = {'REGISTER', 'UNDO'}

    index: bpy.props.IntProperty()

    def execute(self, context):
        scene = context.scene
        scene.controllers.remove(self.index)
        return {'FINISHED'}

class RMT_OT_SelectAllControllers(bpy.types.Operator):
    bl_idname = "rmt.select_all_controllers"
    bl_label = "Select All Controllers"

    def execute(self, context):
        scene = context.scene
        rig = scene.rmt_selected_rig
        if not rig or rig.type != 'ARMATURE':
            self.report({'WARNING'}, "Please select a valid rig (Armature).")
            return {'CANCELLED'}
        controller_names = [ctrl.name for ctrl in scene.controllers]
        if not controller_names:
            self.report({'WARNING'}, "No controllers to select.")
            return {'CANCELLED'}
        bpy.context.view_layer.objects.active = rig
        if rig.mode != 'POSE':
            bpy.ops.object.mode_set(mode='POSE')
        bpy.ops.pose.select_all(action='DESELECT')
        for name in controller_names:
            if name in rig.pose.bones:
                rig.pose.bones[name].bone.select = True
        self.report({'INFO'}, "Selected all controllers.")
        return {'FINISHED'}

class RMT_OT_TransferRootMotion(bpy.types.Operator):
    bl_idname = "rmt.transfer_root_motion"
    bl_label = "Transfer Root Motion"
    bl_description = "Transfer selected axis motion from COG Controller to Root Controller, bake motion, and clean up."
    bl_options = {'REGISTER', 'UNDO'}

    action_name: bpy.props.StringProperty(name="Action Name", default="")

    def execute(self, context):
        scene = context.scene
        rig = scene.rmt_selected_rig
        if not rig:
            self.report({'WARNING'}, "No rig selected.")
            return {'CANCELLED'}

        # If running from batch then change action to active
        if self.action_name:
            action = bpy.data.actions.get(self.action_name)
            if action:
                if not rig.animation_data:
                    rig.animation_data_create()
                rig.animation_data.action = action
            else:
                self.report({'ERROR'}, f"Action '{self.action_name}' not found.")
                return {'CANCELLED'}

        controller_names = [ctrl.name for ctrl in scene.controllers]
        if not controller_names:
            self.report({'WARNING'}, "No controllers added.")
            return {'CANCELLED'}

        root_controller = scene.rmt_root_controller_name
        if not root_controller:
            self.report({'WARNING'}, "No Root Controller selected.")
            return {'CANCELLED'}

        self.create_reference(context, rig, controller_names)
        self.bake_reference(context)
        self.constraint_to_reference(context, rig)
        self.transfer_motion(context, rig)
        self.final_bake(context, rig)
        self.cleanup_reference_objects(context)
        self.report({'INFO'}, "Transfer Root Motion completed.")
        return {'FINISHED'}

    def create_reference(self, context, rig, controller_names):
        scene = context.scene
        collection = bpy.data.collections.get("RootMotionRefs")
        if not collection:
            collection = bpy.data.collections.new("RootMotionRefs")
            bpy.context.scene.collection.children.link(collection)
        for obj in list(collection.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        for bone_name in controller_names:
            ref_obj_name = f"{bone_name}-ref"
            if ref_obj_name in bpy.data.objects:
                continue
            empty_ref = bpy.data.objects.new(ref_obj_name, None)
            collection.objects.link(empty_ref)
            empty_ref.parent = rig
            empty_ref.matrix_world = rig.matrix_world @ rig.pose.bones[bone_name].matrix
            empty_ref.empty_display_size = 0.2  # set as you wish
            empty_ref.empty_display_type = 'SPHERE'
            constraint = empty_ref.constraints.new('COPY_TRANSFORMS')
            constraint.target = rig
            constraint.subtarget = bone_name

    def bake_reference(self, context):
        scene = context.scene
        collection = bpy.data.collections.get("RootMotionRefs")
        if not collection or not collection.objects:
            self.report({'ERROR'}, "No reference objects found!")
            return
        frame_start = scene.frame_start
        frame_end = scene.frame_end
        if bpy.context.object and bpy.context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        for obj in collection.objects:
            obj.select_set(True)
        context.view_layer.objects.active = collection.objects[0]
        bpy.ops.nla.bake(
            frame_start=frame_start,
            frame_end=frame_end,
            only_selected=True,
            visual_keying=True,
            clear_constraints=True,
            clear_parents=False,
            use_current_action=True,
            bake_types={'OBJECT'}
        )
        bpy.ops.object.select_all(action='DESELECT')
        for obj in collection.objects:
            if obj.animation_data and obj.animation_data.action:
                act = obj.animation_data.action
                if not act.name.endswith("_refAction"):
                    act.name += "_refAction"

    def constraint_to_reference(self, context, rig):
        scene = context.scene
        controller_names = [ctrl.name for ctrl in scene.controllers]
        collection = bpy.data.collections.get("RootMotionRefs")
        if not collection:
            self.report({'ERROR'}, "No reference objects found!")
            return
        ref_objs = {obj.name: obj for obj in collection.objects}
        bpy.context.view_layer.objects.active = rig
        if rig.mode != 'POSE':
            bpy.ops.object.mode_set(mode='POSE')
        for bone_name in controller_names:
            ref_obj_name = f"{bone_name}-ref"
            ref_obj = ref_objs.get(ref_obj_name)
            if not ref_obj: continue
            pbone = rig.pose.bones.get(bone_name)
            if not pbone: continue
            for con in list(pbone.constraints):
                if con.name.startswith("RMT_Constraint"):
                    pbone.constraints.remove(con)
            constraint = pbone.constraints.new(type='COPY_TRANSFORMS')
            constraint.name = "RMT_Constraint_CopyTransforms"
            constraint.target = ref_obj

    def transfer_motion(self, context, rig):
        scene = context.scene
        keep_in_world_origin = scene.keep_in_world_origin
        collection = bpy.data.collections.get("RootMotionRefs")
        if not collection:
            collection = bpy.data.collections.new("RootMotionRefs")
            scene.collection.children.link(collection)
        empty_root = bpy.data.objects.new("Empty-Root", None)
        collection.objects.link(empty_root)
        empty_root.location = (0, 0, 0)
        empty_root.empty_display_size = 0.2
        empty_root.empty_display_type = 'SPHERE'
        root_controller_name = scene.rmt_root_controller_name
        pb_root = rig.pose.bones.get(root_controller_name)
        if pb_root is None:
            self.report({'ERROR'}, f"Root controller '{root_controller_name}' not exist!")
            return {'CANCELLED'}
        pb_root.location = (0, 0, 0)
        for c in list(pb_root.constraints):
            if c.type == 'COPY_LOCATION':
                pb_root.constraints.remove(c)
        constraint = pb_root.constraints.new('COPY_LOCATION')
        if keep_in_world_origin:
            constraint.use_x = True
            constraint.use_y = True
            constraint.use_z = False
            constraint.target = empty_root
        else:
            constraint.use_x = scene.axis_x
            constraint.use_y = scene.axis_y
            constraint.use_z = scene.axis_z
            torso_controller_name = scene.rmt_torso_controller_enum
            torso_pbone = rig.pose.bones.get(torso_controller_name)
            if torso_pbone is None:
                self.report({'ERROR'}, f"Torso controller '{torso_controller_name}' not exists!")
                return {'CANCELLED'}
            constraint.target = rig
            constraint.subtarget = torso_controller_name
        constraint.use_offset = False
        constraint.target_space = 'WORLD'
        constraint.owner_space = 'WORLD'
        return {'FINISHED'}

    def cleanup_reference_objects(self, context):
        ref_action_suffix = "_refAction"
        collection = bpy.data.collections.get("RootMotionRefs")
        if collection:
            for obj in list(collection.objects):
                if obj.animation_data and obj.animation_data.action:
                    action = obj.animation_data.action
                    if action.name.endswith(ref_action_suffix):
                        obj.animation_data.action = None
                        bpy.data.actions.remove(action, do_unlink=True)
                bpy.data.objects.remove(obj, do_unlink=True)
            bpy.data.collections.remove(collection)
        actions_to_remove = [a for a in bpy.data.actions if a.name.endswith(ref_action_suffix)]
        for action in actions_to_remove:
            for obj in bpy.data.objects:
                if obj.animation_data and obj.animation_data.action == action:
                    obj.animation_data.action = None
            bpy.data.actions.remove(action, do_unlink=True)

    def final_bake(self, context, rig):
        scene = context.scene
        frame_start = scene.frame_start
        frame_end = scene.frame_end
        root_controller_name = scene.rmt_root_controller_name
        controller_names = [ctrl.name for ctrl in scene.controllers]
        if not root_controller_name:
            self.report({'ERROR'}, "No Root Controller selected for baking!")
            return {'CANCELLED'}
        if rig.mode != 'POSE':
            bpy.ops.object.mode_set(mode='POSE')
        bpy.ops.pose.select_all(action='DESELECT')
        pb_root = rig.pose.bones.get(root_controller_name)
        if pb_root:
            pb_root.bone.select = True
            rig.data.bones.active = pb_root.bone
            bpy.ops.nla.bake(
                frame_start=frame_start,
                frame_end=frame_end,
                only_selected=True,
                visual_keying=True,
                clear_constraints=True,
                clear_parents=True,
                use_current_action=True,
                bake_types={'POSE'}
            )
        bpy.ops.pose.select_all(action='DESELECT')
        other_controllers = [name for name in controller_names if name != root_controller_name]
        for bone_name in other_controllers:
            pbone = rig.pose.bones.get(bone_name)
            if not pbone:
                continue
            pbone.bone.select = True
        if other_controllers:
            rig.data.bones.active = rig.data.bones[other_controllers[0]]
            bpy.ops.nla.bake(
                frame_start=frame_start,
                frame_end=frame_end,
                only_selected=True,
                visual_keying=True,
                clear_constraints=True,
                clear_parents=False,
                use_current_action=True,
                bake_types={'POSE'}
            )
        return {'FINISHED'}

class RMT_OT_BatchTransferRootMotionContinue(bpy.types.Operator):
    bl_idname = "rmt.batch_transfer_root_motion_continue"
    bl_label = "Batch Transfer Root Motion"
    bl_description = "Apply Transfer Root Motion for all selected Actions"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        selected_actions = scene.rmt_batch_actions
        if not selected_actions:
            self.report({'WARNING'}, "No actions selected for batch processing.")
            return {'CANCELLED'}
        rig = scene.rmt_selected_rig
        current_action = rig.animation_data.action if rig.animation_data else None
        for item in selected_actions:
            action_name = item.name
            result = bpy.ops.rmt.transfer_root_motion('INVOKE_DEFAULT', action_name=action_name)
            if result != {'FINISHED'}:
                self.report({'ERROR'}, f"Failed to process action: {action_name}")
        if current_action:
            rig.animation_data.action = current_action
        self.report({'INFO'}, "Batch Transfer Root Motion completed.")
        return {'FINISHED'}

# --- UI Panel and helper ---
def action_contains_rig_animation(action, rig):
    if not rig or rig.type != 'ARMATURE' or not action:
        return False
    for fcurve in action.fcurves:
        if fcurve.data_path.startswith('pose.bones["') and fcurve.data_path.split('["')[1].split('"]')[0] in rig.data.bones:
            return True
    return False

class RMT_PT_RootMotionPanel(bpy.types.Panel):
    bl_label = "Anim Tool Transfer"
    bl_idname = "RMT_PT_root_motion_transfer"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Venky Anim Toolz"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        col = layout.column(align=True)
        col.prop(scene, "rmt_selected_rig", text="Target Object")
        row = layout.row(align=True)
        row.operator("rmt.add_controller", text="Add Controllers", icon='PLUS')
        row = layout.row(align=True)
        row.operator("rmt.clear_controllers", text="Clear All", icon='TRASH')
        row.operator("rmt.select_all_controllers", text="Select All", icon='RESTRICT_SELECT_OFF')
        box = layout.box()
        for index, item in enumerate(scene.controllers):
            row = box.row(align=True)
            row.label(text=item.name, icon='BONE_DATA')
            op = row.operator("rmt.remove_controller", text="", icon='X')
            op.index = index
        col = layout.column(align=True)
        col.label(text="Target Controller (usually torso - COG):")
        col.prop(scene, "rmt_torso_controller_enum", text="")
        col.separator()
        col.label(text="Master Controller (root):")
        if scene.rmt_selected_rig:
            col.prop_search(scene, "rmt_root_controller_name", scene.rmt_selected_rig.pose, "bones", text="", icon="OUTLINER_OB_EMPTY")
        else:
            col.label(text="No rig selected!", icon='ERROR')
        row = layout.row(align=True)
        row.label(text="Keep in World Origin")
        row.prop(scene, "keep_in_world_origin", text="")
        if not scene.keep_in_world_origin:
            row = layout.row(align=True)
            row.label(text="Transfer Axes:")
            subrow = row.row(align=True)
            subrow.scale_x = 0.5
            subrow.prop(scene, "axis_x", text="X")
            subrow.prop(scene, "axis_y", text="Y")
            subrow.prop(scene, "axis_z", text="Z")
        col = layout.column(align=True)
        col.scale_y = 1
        col.operator("rmt.transfer_root_motion", text="Apply Root Motion", icon='PLAY')
        layout.operator("rmt.batch_transfer_root_motion", icon="ACTION")

class RMT_OT_SelectActionsPopup(bpy.types.Operator):
    bl_idname = "rmt.batch_transfer_root_motion"
    bl_label = "Batch Transfer"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Batch execute the following actions (list of actions with keys belonging to Rig)"

    def invoke(self, context, event):
        rig = context.scene.rmt_selected_rig
        scene = context.scene
        scene.rmt_action_items.clear()
        if not rig or rig.type != 'ARMATURE':
            self.report({'WARNING'}, "No rig selected.")
            return {'CANCELLED'}
        for act in bpy.data.actions:
            if act.users > 0 and action_contains_rig_animation(act, rig):
                item = scene.rmt_action_items.add()
                item.name = act.name
                item.action = act
                item.is_selected = False
        return context.window_manager.invoke_props_dialog(self, width=400)

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.label(text="Select actions to process:", icon='ACTION')
        for item in scene.rmt_action_items:
            layout.prop(item, "is_selected", text=item.name)

    def execute(self, context):
        selected = [item.action for item in context.scene.rmt_action_items if item.is_selected]
        if not selected:
            self.report({'WARNING'}, "No actions selected for batch processing.")
            return {'CANCELLED'}
        context.scene.rmt_batch_actions.clear()
        for action in selected:
            item = context.scene.rmt_batch_actions.add()
            item.name = action.name
            item.action = action
        bpy.ops.rmt.batch_transfer_root_motion_continue()
        self.report({'INFO'}, f"Transferred {len(selected)} actions: {', '.join([act.name for act in selected])}")
        return {'FINISHED'}

# ------------ Addon registration ------------
classes = [
    RMT_ControllerItem,
    RMT_ActionItem,
    RMT_OT_AddController,
    RMT_OT_ClearControllers,
    RMT_OT_RemoveController,
    RMT_OT_SelectAllControllers,
    RMT_OT_TransferRootMotion,
    RMT_OT_BatchTransferRootMotionContinue,
    RMT_OT_SelectActionsPopup,
    RMT_PT_RootMotionPanel,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    register_properties()

def unregister():
    unregister_properties()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()