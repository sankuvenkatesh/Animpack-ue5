# -*- coding: utf-8 -*-


bl_info = {
    "name": "Overlap Addon",
    "description": "Calculate an overlap/phase animation.",
    "author": "Venkatesh sanku",
    "version": (1, 1, 1),
    "blender": (2, 80, 0),
    "location": "View3D > Sidebar > Tool Tab",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "support": "COMMUNITY",
    "category": "Animation"
}


import bpy
import mathutils
import copy
import numpy as np
import math
import datetime as dt

# --- Logics previously in sj_phaser.py, now as OverlapModule ---

class OverlapModule(object):
    """phaser"""
    def __init__(self, *args, **kwargs):
        self.delay = 5.0
        self.recursion = 5.0
        self.strength = 1.0
        self.threshold = 0.001
        self.sf = 0
        self.ef = 10
        self.debug = False

    def check_limit(self):
        """limit check"""
        result = True
        return result

    def get_hierarchy_count(self, obj):
        """階層の深さを取得"""
        obj = obj.parent
        cnt = 0
        while obj is not None:
            obj = obj.parent
            cnt += 1
        return cnt

    def sort_by_hierarchy(self):
        """階層の深さ順にdictに回収"""
        obj_list = {}
        for pbn in bpy.context.selected_pose_bones:
            cnt = self.get_hierarchy_count(pbn)
            if cnt in obj_list:
                obj_list[cnt].append(pbn)
            else:
                obj_list[cnt] = []
                obj_list[cnt].append(pbn)
        return obj_list

    def get_default_data_table(self):
        return {
            "obj_list": [],
            "pre_mt": [],
            "obj_length": [],
            "old_vec": []
        }

    def get_tree_list(self):
        """オブジェクトの連続体を回収する"""
        tree_roots = []
        obj_trees = {}
        for pbn in bpy.context.selected_pose_bones:
            # 親なしはそのまま回収して終了
            if pbn.parent is None:
                continue
            # 親が選択されていないものはルートと判断する
            if pbn.parent in bpy.context.selected_pose_bones:
                # 選択されていた場合は分岐かどうかを判定する 0番で無ければルート
                if pbn.parent.children[0] == pbn:
                    continue
            tree_roots.append(pbn)
        t_cnt = 0
        for root_obj in tree_roots:
            depth_cnt = self.get_hierarchy_count(root_obj)
            tree = []
            t_name = "tree{}".format(t_cnt)
            # 既にキーがあるか確認 無いなら作る
            if (depth_cnt in obj_trees) is False:
                obj_trees[depth_cnt] = {}
            # 子供が無かったら終了
            if len(root_obj.children) == 0:
                tree.append(root_obj)
                obj_trees[depth_cnt][t_name] = self.get_default_data_table()
                obj_trees[depth_cnt][t_name]["obj_list"] = tree
                t_cnt += 1
                continue
            # ツリーは0番の子供を連続とする
            tree.append(root_obj)
            c_obj = root_obj.children[0]
            # 子供が選択に入っていれば連続構造とする、途切れたら終わり
            while c_obj in bpy.context.selected_pose_bones:
                tree.append(c_obj)
                if len(c_obj.children) == 0:
                    break
                c_obj = c_obj.children[0]
            # ツリー名
            obj_trees[depth_cnt][t_name] = self.get_default_data_table()
            obj_trees[depth_cnt][t_name]["obj_list"] = tree
            t_cnt += 1
        return obj_trees

    def get_bone_length_matrix(self, pbn):
        """方向を含む骨の長さmatrixを取得"""
        amt = bpy.context.active_object # まずワールドmatrixに置き換える
        wmt = amt.matrix_world @ pbn.matrix
        p_wmt = amt.matrix_world @ pbn.parent.matrix # 親 ワールド置換
        len_mt = wmt.transposed() @ p_wmt.transposed().inverted() # 転置行列
        return len_mt.transposed()

    def get_bone_pre_matrix(self, pbn):
        """pose boneの初期world_matrixを回収"""
        amt = bpy.context.active_object
        return amt.matrix_world @ pbn.matrix

    def get_end_pos_from_bonelength(self, pbn):
        """方向を含む骨の長さmatrixを取得"""
        amt = bpy.context.active_object # まずワールドmatrixに置き換える
        wmt = amt.matrix_world @ pbn.matrix
        # 長さの行列を作って親と掛け合わせて先端位置の行列を作る
        x = mathutils.Vector((1.0, 0.0, 0.0, 0.0))
        y = mathutils.Vector((0.0, 1.0, 0.0, pbn.length))
        z = mathutils.Vector((0.0, 0.0, 1.0, 0.0))
        w = mathutils.Vector((0.0, 0.0, 0.0, 1.0))
        len_mt = mathutils.Matrix([x, y, z, w])
        len_mt = len_mt.transposed() @ wmt.transposed()
        return len_mt.transposed()

    def normalize(self, vec):
        """ベクトルの正規化"""
        return vec / np.linalg.norm(vec)

    def set_pre_data(self, obj_trees):
        dct_k = sorted(obj_trees.keys()) # ソートしてツリー深度順にする
        cnt = 1 # 配列のカウント用、最後のオブジェクトは先端位置
        for k in dct_k:
            for t in obj_trees[k]:
                cnt = 1
                for pbn in obj_trees[k][t]["obj_list"]:
                    obj_trees[k][t]["pre_mt"].append(
                        self.get_bone_pre_matrix(pbn))
                    obj_trees[k][t]["obj_length"].append(
                        self.get_bone_length_matrix(pbn))
                    obj_trees[k][t]["old_vec"].append(
                        mathutils.Vector((0.0, 0.0, 0.0)))
                    # 最後のオブジェクトは
                    if cnt == len(obj_trees[k][t]["obj_list"]):
                        # まずはエンドポジションを取得する
                        amt = bpy.context.active_object
                        wmt = amt.matrix_world @ pbn.matrix
                        end_mt = self.get_end_pos_from_bonelength(pbn)
                        obj_trees[k][t]["pre_mt"].append(end_mt)
                        # 転置行列で計算する
                        len_mt = end_mt.transposed() @ wmt.transposed().inverted()
                        obj_trees[k][t]["obj_length"].append(len_mt.transposed())
                    cnt += 1
        return obj_trees

    def del_animkey(self, obj_trees):
        dct_k = sorted(obj_trees.keys())
        for k in dct_k:
            for t in obj_trees[k]:
                for pbn in obj_trees[k][t]["obj_list"]:
                    for f in range(self.sf-1, self.ef+1):
                        try:
                            pbn.keyframe_delete(data_path="location", frame=f)
                            pbn.keyframe_delete(data_path="rotation_euler", frame=f)
                            pbn.keyframe_delete(data_path="rotation_quaternion", frame=f)
                            pbn.keyframe_delete(data_path="scale", frame=f)
                        except:
                            break
        # これが無いとboneの状態がアップデートされない
        bpy.context.view_layer.update()
        for k in dct_k:
            for t in obj_trees[k]:
                for pbn in obj_trees[k][t]["obj_list"]:  # キーを作成しておく
                    pbn.keyframe_insert(data_path='location', frame=self.sf)
                    pbn.keyframe_insert(data_path='rotation_euler', frame=self.sf)
                    pbn.keyframe_insert(data_path='rotation_quaternion', frame=self.sf)
                    pbn.keyframe_insert(data_path='scale', frame=self.sf)
        return None

    def set_animkey(self, obj):
        f = bpy.context.scene.frame_current
        obj.keyframe_insert(data_path='location', frame=f)
        obj.keyframe_insert(data_path='rotation_euler', frame=f)
        obj.keyframe_insert(data_path='rotation_quaternion', frame=f)
        obj.keyframe_insert(data_path='scale', frame=f)
        return None

    def clamp(self, n, minn=0.0, maxn=1.0):
        return max(min(maxn, n), minn)

    def rotate_matrix(self, mtx, rot_mt):
        """matrixを指定の角度matrixで回転する"""
        # 成分ごとに分解
        loc, r_mt, s_mt = mtx.decompose()
        pos = mathutils.Matrix.Translation(loc)
        rot = r_mt.to_matrix().to_4x4()
        scl = (mathutils.Matrix.Scale(s_mt[0], 4, (1, 0, 0)) @
               mathutils.Matrix.Scale(s_mt[1], 4, (0, 1, 0)) @
               mathutils.Matrix.Scale(s_mt[2], 4, (0, 0, 1)))
        return pos @ rot_mt @ rot @ scl

    def create_test_empty(self, e_name, mtx):
        if self.debug is False:
            return None
        emp = bpy.data.objects.new(e_name, None)
        bpy.context.selected_objects[0].users_collection[0].objects.link(emp)
        emp.empty_display_size = 0.2
        emp.empty_display_type = 'ARROWS'
        emp.matrix_world = copy.copy(mtx)
        return None

    def calculate(self, obj_data):
        """phase"""
        amt = bpy.context.active_object
        # 初期の親のmatrix
        cur_p_mt = amt.matrix_world @ obj_data["obj_list"][0].parent.matrix
        strgh = self.strength # ベクトル長さ（強さ）長いと反復挙動が強くなる
        trshd = self.threshold # 閾値
        for i in range(len(obj_data["obj_list"])):
            obj = obj_data["obj_list"][i]
            # phase1
            tag_mt = obj_data["obj_length"][i].transposed() @ cur_p_mt.transposed()
            tag_mt = tag_mt.transposed()
            pre_mt = copy.copy(obj_data["pre_mt"][i])
            new_mt = copy.copy(obj_data["pre_mt"][i])
            tag_pos = tag_mt.translation
            pre_y_vec = pre_mt.transposed().to_3x3()[1].normalized()
            tag_y_vec = tag_mt.transposed().to_3x3()[1].normalized()
            y_diff = np.arccos(self.clamp(np.dot(pre_y_vec, tag_y_vec)))
            axis_vec = mathutils.Vector(np.cross(pre_y_vec, tag_y_vec))
            new_mt = self.rotate_matrix(new_mt,
                        mathutils.Matrix.Rotation(y_diff, 4, axis_vec.normalized()))
            new_mt.translation = copy.copy(tag_pos)
            # phase2
            new_x_vec = new_mt.transposed().to_3x3()[0].normalized()
            tag_x_vec = tag_mt.transposed().to_3x3()[0].normalized()
            dot_val = np.dot(new_x_vec, tag_x_vec)
            if dot_val > 1.0:
                roll = 0.0
            else:
                roll = np.arccos(dot_val)
            roll = roll / self.delay
            check_vec = np.cross(new_x_vec, tag_x_vec)
            if np.dot(check_vec, tag_y_vec) < 0.0:
                roll = -roll
            axis_vec = new_mt.transposed().to_3x3()[1].normalized()
            new_mt = self.rotate_matrix(new_mt,
                        mathutils.Matrix.Rotation(roll, 4, axis_vec))
            new_mt.translation = tag_pos
            # phase3 位相ベクトル
            c_pos = obj_data["pre_mt"][i+1].translation
            y_vec = self.normalize(c_pos - tag_pos)
            new_y_vec = new_mt.transposed().to_3x3()[1].normalized()
            rcs_vec = (obj_data["old_vec"][i] * self.recursion)
            phase_vec = ((new_y_vec - (y_vec * strgh)) / self.delay) + rcs_vec
            if phase_vec.length < trshd:
                phase_vec = mathutils.Vector((0.0, 0.0, 0.0))
            y_vec = y_vec + phase_vec
            obj_data["old_vec"][i] = phase_vec
            new_z_vec = new_mt.transposed().to_3x3()[2].normalized()
            y_vec = mathutils.Vector(self.normalize(y_vec))
            x_vec = mathutils.Vector(self.normalize(np.cross(y_vec, new_z_vec)))
            z_vec = mathutils.Vector(self.normalize(np.cross(x_vec, y_vec)))
            new_mt = mathutils.Matrix([x_vec, y_vec, z_vec])
            new_mt = new_mt.transposed().to_4x4()
            new_mt.translation = copy.copy(tag_pos)
            obj.matrix = amt.matrix_world.inverted() @ new_mt
            bpy.context.view_layer.update()
            self.set_animkey(obj)
            obj_data["pre_mt"][i] = copy.copy(new_mt)
            cur_p_mt = copy.copy(new_mt)
            len_mt = obj_data["obj_length"][i+1].transposed() @ new_mt.transposed()
            obj_data["pre_mt"][i+1].translation = len_mt.transposed().translation

    def message_box(self, message="", title="Message", icon='INFO'):
        def draw(self, context):
            self.layout.label(text=message)
        bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)

    def excute(self, obj_trees):
        dct_k = sorted(obj_trees.keys())
        # フレーム毎
        for f in range(self.sf+1, self.ef+1):
            bpy.context.scene.frame_set(f)
            # 階層ツリーごとに
            for k in dct_k:
                for t in obj_trees[k]:
                    self.calculate(obj_trees[k][t])
        return True

# ---- UI Properties, Operators, Panels ---

class OverlapProperties(bpy.types.PropertyGroup):
    """カスタムプロパティを定義する"""
    # frame
    start_frame: bpy.props.IntProperty(name="Start Frame", default=0, min=0)
    end_frame: bpy.props.IntProperty(name="End Frame", default=100, min=1)
    # Delay
    delay: bpy.props.FloatProperty(name="Delay", default=3, min=1.0, max=10.0)
    # Recursion
    recursion: bpy.props.FloatProperty(
        name="Recursion", default=5.0, min=0.0, max=10.0)
    # Power/Strength
    strength: bpy.props.FloatProperty(
        name="Strength", default=1.0, min=1.0, max=10.0)
    # Threshold
    threshold: bpy.props.FloatProperty(
        name="Threshold",
        default=0.001, min=0.00001, max=0.1, step=0.01, precision=4)
    debug: bpy.props.BoolProperty(name="Debug", default=False)

class OverlapResetDefaults(bpy.types.Operator):
    """Reset Overlap Properties to Defaults"""
    bl_idname = "overlap.reset_defaults"
    bl_label = "Reset Values"
    bl_description = "Reset all Overlap properties to their default values"

    @classmethod
    def poll(cls, context):
        return hasattr(context.scene, "overlap_props")

    def execute(self, context):
        props = context.scene.overlap_props
        props.start_frame = 0
        props.end_frame = 100
        props.delay = 3
        props.recursion = 5.0
        props.strength = 1.0
        props.threshold = 0.001
        props.debug = False
        self.report({'INFO'}, "Overlap: Values reset to default.")
        return {'FINISHED'}

class OverlapCalculate(bpy.types.Operator):
    """Gen overlap/phase animation"""
    bl_idname = "overlap.calculate"
    bl_label = "Calculate"
    bl_description = "Calculate an overlap phase animation."

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        ps = context.scene.overlap_props
        mod = OverlapModule()
        mod.sf = ps.start_frame
        mod.ef = ps.end_frame
        mod.debug = ps.debug
        mod.delay = ps.delay
        mod.recursion = ps.recursion / 10.0
        mod.strength = 1.0 + ((ps.strength - 1.0) / 10.0)
        mod.threshold = ps.threshold
        if ps.start_frame >= ps.end_frame:
            msg = "Make the start frame smaller than the end frame."
            def draw(self, context):
                self.layout.label(text=msg)
            bpy.context.window_manager.popup_menu(draw, title="Info", icon="INFO")
            self.report({'INFO'}, msg)
            return {'FINISHED'}
        bpy.context.scene.frame_set(ps.start_frame)
        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
        obj_trees = mod.get_tree_list()
        mod.del_animkey(obj_trees)
        obj_trees = mod.set_pre_data(obj_trees)
        mod.excute(obj_trees)
        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
        return {'FINISHED'}


class OverlapDelAnim(bpy.types.Operator):
    """Del Anim"""
    bl_idname = "overlap.del_anim"
    bl_label = "Delete Keyframe"
    bl_description = "Delete animation key."

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        ps = context.scene.overlap_props
        mod = OverlapModule()
        sf = ps.start_frame
        ef = ps.end_frame
        mod.sf = sf
        mod.ef = ef
        mod.debug = ps.debug
        if sf >= ef:
            msg = "Make the start frame smaller than the end frame."
            def draw(self, context):
                self.layout.label(text=msg)
            bpy.context.window_manager.popup_menu(draw, title="Info", icon="INFO")
            self.report({'INFO'}, msg)
            return {'FINISHED'}
        bpy.context.scene.frame_set(sf)
        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
        obj_trees = mod.get_tree_list()
        mod.del_animkey(obj_trees)
        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
        return {'FINISHED'}


class OverlapPanel(bpy.types.Panel):
    """UI"""
    bl_label = "Overlap Addon"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_context = "posemode"
    bl_category = "Venky Anim Toolz"
    bl_options = {'DEFAULT_CLOSED'}
    def draw(self, context):
        layout = self.layout
        ps = context.scene.overlap_props
        layout.label(text="Frame")
        row = layout.row()
        row.prop(ps, "start_frame")
        row.prop(ps, "end_frame")
        layout.label(text="Properties")
        row = layout.row(align=True)
        row.prop(ps, "delay")
        row.prop(ps, "recursion")
        row.prop(ps, "strength")
        row = layout.row()
        row.prop(ps, "threshold")
        layout.label(text="Main")
        row = layout.row()
        row.scale_y = 1.8
        row.operator("overlap.calculate", icon="KEYTYPE_KEYFRAME_VEC")
        row = layout.row()
        row.operator("overlap.del_anim", icon="KEYFRAME")
        row = layout.row()
        # After: row = layout.row()
#        row.operator("overlap.del_anim", icon="KEYFRAME")

        row = layout.row()
        row.operator("overlap.reset_defaults", icon="LOOP_BACK")

# --- Register ---

classes = (
    OverlapProperties,
    OverlapCalculate,
    OverlapDelAnim,
    OverlapResetDefaults,   # <-- Add this line!
    OverlapPanel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.overlap_props = bpy.props.PointerProperty(type=OverlapProperties)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.overlap_props

if __name__ == "__main__":
    register()
