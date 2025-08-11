bl_info = {
    "name": "Smart Curve Tools",
    "author": "Venkatesh Sanku (merged by AI assistant)",
    "version": (1, 0),
    "blender": (2, 80, 0),
    "location": "Graph Editor > Sidebar > Smart Curve Tools Tab",
    "description": (
        "Combined toolset: Smart Euler Filter for unwrap/smooth Euler or Quaternion rotations preserving handles "
        "and advanced smoothing of selected F-Curve keyframes. "
        "Works for objects and pose bones, with preserved keyframe handles."
    ),
    "category": "Animation",
}

import bpy
import math
from mathutils import Euler, Quaternion

# ----- Smart Euler Filter Functions -----

def nearest_equivalent_euler(a1, a2):
    twopi = 2 * math.pi
    while a2 - a1 > math.pi:
        a2 -= twopi
    while a2 - a1 < -math.pi:
        a2 += twopi
    return a2

def get_selection_info(context):
    obj = context.active_object
    bone = getattr(context, "active_pose_bone", None)
    if bone:
        return bone, bone.rotation_mode, f'pose.bones["{bone.name}"]'
    elif obj:
        return obj, obj.rotation_mode, ""
    else:
        return None, None, None

def get_rotation_fcurves(mode_code, all_fcurves, rna_path_prefix):
    if mode_code == "EULER":
        channel = "rotation_euler"
        num_channels = 3
    else:
        channel = "rotation_quaternion"
        num_channels = 4

    if rna_path_prefix:
        prefix = rna_path_prefix
        found = [
            fc for fc in all_fcurves
            if fc.data_path.startswith(f'{prefix}.') and fc.data_path.endswith(channel)
        ]
    else:
        found = [
            fc for fc in all_fcurves
            if fc.data_path == channel
        ]

    found = sorted(found, key=lambda fc: fc.array_index)
    found = found[:num_channels]
    if not found or (mode_code == "EULER" and len(found) < 3) or (mode_code == "QUATERNION" and len(found) < 4):
        return None, f"No {channel} f-curves found for {'bone' if rna_path_prefix else 'object'}."
    return found, None

def get_fcurve_keyframe_map(fcurve):
    return {int(round(kp.co[0])): kp for kp in fcurve.keyframe_points}

def collect_keyframes_with_handles_any(curves):
    axis_keyframes = [get_fcurve_keyframe_map(fc) for fc in curves]
    frames = sorted({f for mapping in axis_keyframes for f in mapping})
    keyframe_info = []
    for f in frames:
        kps = [mapping.get(f) for mapping in axis_keyframes]
        value = [kp.co[1] if kp else None for kp in kps]
        handles = [{
            'handle_left_type': kp.handle_left_type if kp else None,
            'handle_right_type': kp.handle_right_type if kp else None,
            'handle_left': kp.handle_left.copy() if kp else None,
            'handle_right': kp.handle_right.copy() if kp else None,
        } for kp in kps]
        keyframe_info.append({
            'frame': f,
            'value': value,
            'handles': handles,
        })
    return keyframe_info

def unwrap_keyframe_values_euler_any(keyframes):
    out = []
    prev = None
    for info in keyframes:
        e = info['value']
        if prev is None:
            fixed = list(e)
        else:
            fixed = [nearest_equivalent_euler(prev[i], e[i]) if e[i] is not None and prev[i] is not None else e[i]
                     for i in range(len(e))]
        out.append({
            'frame': info['frame'],
            'value': fixed,
            'handles': info['handles'],
        })
        prev = [fixed[i] if fixed[i] is not None else (prev[i] if prev else None) for i in range(len(fixed))]
    return out

def unwrap_keyframe_values_quaternion_any(keyframes):
    out = []
    prev = None
    for info in keyframes:
        v = info['value']
        if len(v) == 4:
            q = Quaternion([x if x is not None else (prev[i] if prev is not None else 0.0) for i, x in enumerate(v)])
            if prev is not None and prev.dot(q) < 0.0:
                q = -q
            values = [q.w, q.x, q.y, q.z]
            prev = Quaternion(q)
        else:
            values = v if prev is None else [
                -v[i] if v[i] is not None and prev[i] is not None and abs(v[i] + prev[i]) < abs(v[i] - prev[i]) else v[i]
                for i in range(len(v))
            ]
            prev = [values[i] if values[i] is not None else (prev[i] if prev else None) for i in range(len(values))]
        out.append({
            'frame': info['frame'],
            'value': values,
            'handles': info['handles'],
        })
    return out

def preserve_and_update_fcurve_points_any(curves, keyframe_infos):
    for axis, fc in enumerate(curves):
        frame_map = get_fcurve_keyframe_map(fc)
        for info in keyframe_infos:
            f = info['frame']
            v = info['value'][axis]
            kph = info['handles'][axis]
            kp = frame_map.get(f)
            if kp and v is not None:
                kp.co[1] = v
                if kph['handle_left_type'] is not None:
                    kp.handle_left_type = kph['handle_left_type']
                if kph['handle_right_type'] is not None:
                    kp.handle_right_type = kph['handle_right_type']
                if kph['handle_left'] is not None:
                    kp.handle_left = kph['handle_left']
                if kph['handle_right'] is not None:
                    kp.handle_right = kph['handle_right']
        fc.update()

def ensure_rotation_keyframes(context, entity, mode_code, rna_path_prefix):
    frame = context.scene.frame_current
    if rna_path_prefix:  # It's a bone
        data_path = 'rotation_quaternion' if mode_code == "QUATERNION" else 'rotation_euler'
        entity.keyframe_insert(data_path=data_path, frame=frame)
    else:
        obj = entity
        data_path = 'rotation_quaternion' if mode_code == "QUATERNION" else 'rotation_euler'
        obj.keyframe_insert(data_path=data_path, frame=frame)

# ----- Smooth-filter Functions -----

def clamp(value, minv, maxv):
    return min(max(value, minv), maxv)

def auto_fix_bad_keyframes(fcurve):
    keyframes = fcurve.keyframe_points
    n = len(keyframes)
    for i in range(n):
        y = keyframes[i].co[1]
        if not math.isfinite(y):
            left = next((keyframes[j].co[1] for j in range(i - 1, -1, -1) if math.isfinite(keyframes[j].co[1])), None)
            right = next((keyframes[j].co[1] for j in range(i + 1, n) if math.isfinite(keyframes[j].co[1])), None)
            if left is not None and right is not None:
                keyframes[i].co[1] = (left + right) / 2
            elif left is not None:
                keyframes[i].co[1] = left
            elif right is not None:
                keyframes[i].co[1] = right
            else:
                keyframes[i].co[1] = 0.0

def smooth_selected_keyframes(fcurve, iterations, strength, sensitivity, preserve_ends=True):
    keyframes = fcurve.keyframe_points
    n = len(keyframes)
    if n < 3:
        return {'moved': 0, 'max_delta': 0}
    selected_indices = [i for i, kp in enumerate(keyframes) if kp.select_control_point]
    if len(selected_indices) < 3:
        return {'moved': 0, 'max_delta': 0}
    values = [kp.co[1] for kp in keyframes]
    stats = {'moved': 0, 'max_delta': 0}
    strength_factor = strength ** 3
    smooth_factor = 1.0 - sensitivity
    for _ in range(iterations):
        new_values = values[:]
        for idx_pos in range(1, len(selected_indices) - 1):
            i = selected_indices[idx_pos]
            if preserve_ends and (idx_pos == 0 or idx_pos == len(selected_indices) - 1):
                continue
            left_i = selected_indices[idx_pos - 1]
            right_i = selected_indices[idx_pos + 1]
            left = values[left_i]
            center = values[i]
            right = values[right_i]
            average = (left + center + right) / 3
            diff = abs(center - average)
            base = abs(center) if center != 0 else 1.0
            weight_unclamped = strength_factor * (1 - smooth_factor + smooth_factor * (diff / base))
            weight = clamp(weight_unclamped, 0.0, 1.0)
            new_val = center * (1 - weight) + average * weight
            if not math.isfinite(new_val):
                new_val = center
            delta = new_val - center
            new_values[i] = new_val
            if abs(delta) > 0:
                stats['moved'] += 1
                stats['max_delta'] = max(stats['max_delta'], abs(delta))
        values = new_values
    for i in selected_indices:
        keyframes[i].co[1] = values[i]
    auto_fix_bad_keyframes(fcurve)
    fcurve.update()
    return stats

def set_bezier_and_auto_clamp_handles(fcurve):
    for kp in fcurve.keyframe_points:
        kp.interpolation = 'BEZIER'
        kp.handle_left_type = 'AUTO_CLAMPED'
        kp.handle_right_type = 'AUTO_CLAMPED'
    fcurve.update()

# ----- Blender UI and Operator Classes -----

class ROTATION_OT_smart_euler_filter(bpy.types.Operator):
    """Smart Euler Filter: unwrap/smooth Euler or Quaternion rotation for objects/pose bones.
    Handles preserved. Works with all curves (selected or not), all keyframes."""
    bl_idname = "graph.smart_euler_filter"
    bl_label = "Smart Euler Filter"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        entity, rot_mode, rna_path_prefix = get_selection_info(context)
        obj = context.active_object

        if not entity or not obj or not obj.animation_data or not obj.animation_data.action:
            self.report({'ERROR'}, "No active object or pose bone with animation/action found.")
            return {'CANCELLED'}

        all_fcurves = obj.animation_data.action.fcurves

        if rot_mode == "QUATERNION":
            mode_code = "QUATERNION"
        elif rot_mode in {"XYZ", "XZY", "YXZ", "YZX", "ZXY", "ZYX"}:
            mode_code = "EULER"
        else:
            self.report({'ERROR'}, f"Unsupported rotation mode: {rot_mode}")
            return {'CANCELLED'}

        rotation_fcurves_all, err = get_rotation_fcurves(mode_code, all_fcurves, rna_path_prefix)

        if rotation_fcurves_all is None:
            ensure_rotation_keyframes(context, entity, mode_code, rna_path_prefix)
            all_fcurves = obj.animation_data.action.fcurves
            rotation_fcurves_all, err = get_rotation_fcurves(mode_code, all_fcurves, rna_path_prefix)
            if rotation_fcurves_all is None:
                self.report({'ERROR'}, err)
                return {'CANCELLED'}

        # Use selected fcurves if any selected
        selected_fcurves = [fc for fc in rotation_fcurves_all if fc.select]
        rotation_fcurves = selected_fcurves if selected_fcurves else rotation_fcurves_all

        keyframes = collect_keyframes_with_handles_any(rotation_fcurves)
        if not keyframes:
            self.report({'ERROR'}, "No matching keyframes found in any channel.")
            return {'CANCELLED'}

        if mode_code == "EULER":
            unwrapped = unwrap_keyframe_values_euler_any(keyframes)
        else:
            unwrapped = unwrap_keyframe_values_quaternion_any(keyframes)

        preserve_and_update_fcurve_points_any(rotation_fcurves, unwrapped)

        if context.area:
            context.area.tag_redraw()

        self.report({'INFO'}, f"{mode_code} continuity applied to {len(rotation_fcurves)} channel(s) of {'bone' if rna_path_prefix else 'object'} "
                              f"({ 'selected only' if selected_fcurves else 'all channels'}), over all keyframes.")
        return {'FINISHED'}

class CurveSmoothProperties(bpy.types.PropertyGroup):
    iterations: bpy.props.IntProperty(
        name="Iterations",
        description="Number of smoothing iterations",
        default=5, min=1, max=50
    )
    strength: bpy.props.FloatProperty(
        name="Strength",
        description="Smoothing intensity (0-1)",
        default=0.5, min=0.0, max=1.0
    )
    sensitivity: bpy.props.FloatProperty(
        name="Sensitivity",
        description="Smoothing sensitivity falloff (Reversed effect, 0-1)",
        default=0.5, min=0.0, max=1.0
    )
    preserve_ends: bpy.props.BoolProperty(
        name="Preserve Ends",
        description="Do not smooth the first and last selected keyframes",
        default=True
    )

class CurveSmoothOperator(bpy.types.Operator):
    """Smooth Selected Keyframes of Selected F-Curves (Advanced)"""
    bl_idname = "graph.smooth_selected_keyframes"
    bl_label = "Smooth Selected Keyframes (Advanced)"
    bl_options = {'REGISTER', 'UNDO', 'PRESET'}

    def execute(self, context):
        settings = context.scene.curve_smooth_settings
        smoothed_count = 0
        total_keys = 0
        biggest_move = 0
        curves = getattr(context, "selected_editable_fcurves", [])

        if not curves:
            self.report({'WARNING'}, "No editable F-Curves selected")
            return {'CANCELLED'}

        for fcurve in curves:
            selected_keys = [kp for kp in fcurve.keyframe_points if kp.select_control_point]
            if len(selected_keys) >= 3:
                stats = smooth_selected_keyframes(
                    fcurve,
                    settings.iterations,
                    settings.strength,
                    settings.sensitivity,
                    settings.preserve_ends
                )
                set_bezier_and_auto_clamp_handles(fcurve)  # Set handles after smoothing
                smoothed_count += 1
                total_keys += stats['moved']
                biggest_move = max(biggest_move, stats['max_delta'])

        if smoothed_count == 0:
            self.report({'WARNING'}, "Not enough selected keyframes to smooth")
            return {'CANCELLED'}

        self.report({'INFO'},
                    f"Smoothed {total_keys} keyframes in {smoothed_count} F-Curve(s). Largest change: {biggest_move:.2f}")
        return {'FINISHED'}

class CurveSmoothAllOperator(bpy.types.Operator):
    """Batch Smooth All F-Curves (Advanced)"""
    bl_idname = "graph.smooth_all_keyframes"
    bl_label = "Batch Smooth All F-Curves"
    bl_options = {'REGISTER', 'UNDO', 'PRESET'}

    def execute(self, context):
        settings = context.scene.curve_smooth_settings
        smoothed_count = 0
        total_keys = 0
        biggest_move = 0

        for obj in context.selected_objects:
            if obj.animation_data and obj.animation_data.action:
                for fcurve in obj.animation_data.action.fcurves:
                    selected_keys = [kp for kp in fcurve.keyframe_points if kp.select_control_point]
                    if len(selected_keys) >= 3:
                        stats = smooth_selected_keyframes(
                            fcurve,
                            settings.iterations,
                            settings.strength,
                            settings.sensitivity,
                            settings.preserve_ends
                        )
                        set_bezier_and_auto_clamp_handles(fcurve)  # Set handles after smoothing
                        smoothed_count += 1
                        total_keys += stats['moved']
                        biggest_move = max(biggest_move, stats['max_delta'])

        if smoothed_count == 0:
            self.report({'WARNING'}, "No F-Curves to smooth")
            return {'CANCELLED'}

        self.report({'INFO'},
                    f"Batch smoothed {total_keys} keyframes in {smoothed_count} F-Curve(s). Largest change: {biggest_move:.2f}")
        return {'FINISHED'}

class ResetCurveSmoothValuesOperator(bpy.types.Operator):
    """Reset Curve Smooth Values to Defaults"""
    bl_idname = "graph.reset_curve_smooth_values"
    bl_label = "Reset Curve Smooth Values"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.scene.curve_smooth_settings
        settings.iterations = 5
        settings.strength = 0.5
        settings.sensitivity = 0.5
        settings.preserve_ends = True
        self.report({'INFO'}, "Reset smoothing parameters to default values")
        return {'FINISHED'}

class SMARTCURVETOOLS_PT_panel(bpy.types.Panel):
    bl_label = "Smart Curve Tools"
    bl_space_type = 'GRAPH_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Smart Curve Tools"

    def draw(self, context):
        layout = self.layout

        # Smart Euler Filter section
        layout.label(text="Smart Euler Filter:")
        layout.operator("graph.smart_euler_filter", icon='CON_ROTLIKE')

        layout.separator()

        # Curve smoothing section
        settings = context.scene.curve_smooth_settings
        layout.label(text="Curve Smoothing Parameters:")
        layout.prop(settings, "iterations")
        layout.prop(settings, "strength")
        layout.prop(settings, "sensitivity")
        layout.prop(settings, "preserve_ends")

        layout.operator("graph.smooth_selected_keyframes", text="Smooth Selected Keyframes")
        layout.operator("graph.smooth_all_keyframes", text="Batch Smooth All F-Curves")
        layout.separator()
        layout.operator("graph.reset_curve_smooth_values", text="Reset Smooth Values")

# ----- Register and Unregister -----

classes = [
    ROTATION_OT_smart_euler_filter,
    CurveSmoothProperties,
    CurveSmoothOperator,
    CurveSmoothAllOperator,
    ResetCurveSmoothValuesOperator,
    SMARTCURVETOOLS_PT_panel,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.curve_smooth_settings = bpy.props.PointerProperty(type=CurveSmoothProperties)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.curve_smooth_settings

if __name__ == "__main__":
    register()
