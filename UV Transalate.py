bl_info = {
    "name": "UV Vertex Step Translate",
    "author": "Venkatesh sanku",
    "version": (1, 0, 0),
    "blender": (3, 0, 0),
    "location": "UV Editor > Sidebar > UV Tools",
    "description": "Increment/Decrement selected UV vertices by 1 along U or V in the UV Editor.",
    "category": "UV",
}

import bpy
import bmesh

# Operators to increment/decrement UVs
class UV_OT_IncrementU(bpy.types.Operator):
    bl_idname = "uv.increment_u"
    bl_label = "Increment U (+1)"
    bl_options = {'REGISTER', 'UNDO'}

    amount: bpy.props.FloatProperty(default=1.0)

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            self.report({'WARNING'}, "No mesh object selected.")
            return {'CANCELLED'}
        bpy.ops.object.mode_set(mode='EDIT')
        mesh = bmesh.from_edit_mesh(obj.data)
        uv_layer = mesh.loops.layers.uv.verify()
        for face in mesh.faces:
            for loop in face.loops:
                if loop[uv_layer].select:
                    loop[uv_layer].uv.x += self.amount
        bmesh.update_edit_mesh(obj.data)
        return {'FINISHED'}

class UV_OT_DecrementU(bpy.types.Operator):
    bl_idname = "uv.decrement_u"
    bl_label = "Decrement U (-1)"
    bl_options = {'REGISTER', 'UNDO'}

    amount: bpy.props.FloatProperty(default=-1.0)

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            self.report({'WARNING'}, "No mesh object selected.")
            return {'CANCELLED'}
        bpy.ops.object.mode_set(mode='EDIT')
        mesh = bmesh.from_edit_mesh(obj.data)
        uv_layer = mesh.loops.layers.uv.verify()
        for face in mesh.faces:
            for loop in face.loops:
                if loop[uv_layer].select:
                    loop[uv_layer].uv.x += self.amount
        bmesh.update_edit_mesh(obj.data)
        return {'FINISHED'}

class UV_OT_IncrementV(bpy.types.Operator):
    bl_idname = "uv.increment_v"
    bl_label = "Increment V (+1)"
    bl_options = {'REGISTER', 'UNDO'}

    amount: bpy.props.FloatProperty(default=1.0)

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            self.report({'WARNING'}, "No mesh object selected.")
            return {'CANCELLED'}
        bpy.ops.object.mode_set(mode='EDIT')
        mesh = bmesh.from_edit_mesh(obj.data)
        uv_layer = mesh.loops.layers.uv.verify()
        for face in mesh.faces:
            for loop in face.loops:
                if loop[uv_layer].select:
                    loop[uv_layer].uv.y += self.amount
        bmesh.update_edit_mesh(obj.data)
        return {'FINISHED'}

class UV_OT_DecrementV(bpy.types.Operator):
    bl_idname = "uv.decrement_v"
    bl_label = "Decrement V (-1)"
    bl_options = {'REGISTER', 'UNDO'}

    amount: bpy.props.FloatProperty(default=-1.0)

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            self.report({'WARNING'}, "No mesh object selected.")
            return {'CANCELLED'}
        bpy.ops.object.mode_set(mode='EDIT')
        mesh = bmesh.from_edit_mesh(obj.data)
        uv_layer = mesh.loops.layers.uv.verify()
        for face in mesh.faces:
            for loop in face.loops:
                if loop[uv_layer].select:
                    loop[uv_layer].uv.y += self.amount
        bmesh.update_edit_mesh(obj.data)
        return {'FINISHED'}

# Panel in the UV Editor
class UV_PT_VertexStepPanel(bpy.types.Panel):
    bl_label = "UV Vertex Step Translate"
    bl_idname = "UV_PT_vertex_step_translate"
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "UV Tools"

    @classmethod
    def poll(cls, context):
        ob = context.active_object
        return context.area.type == 'IMAGE_EDITOR' and ob is not None and ob.type == 'MESH'

    def draw(self, context):
        layout = self.layout
        split = layout.split(factor=0.5)
        col = split.column()
        col.operator("uv.increment_u", text="U +1").amount = 1.0
        col.operator("uv.decrement_u", text="U -1").amount = -1.0
        col = split.column()
        col.operator("uv.increment_v", text="V +1").amount = 1.0
        col.operator("uv.decrement_v", text="V -1").amount = -1.0
        layout.label(text="Select UV verts then press buttons.")

# Registration
classes = (
    UV_OT_IncrementU,
    UV_OT_DecrementU,
    UV_OT_IncrementV,
    UV_OT_DecrementV,
    UV_PT_VertexStepPanel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
