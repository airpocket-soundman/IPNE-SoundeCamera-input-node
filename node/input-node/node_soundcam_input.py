#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import numpy as np
import dearpygui.dearpygui as dpg
import json
import cv2

from node_editor.util import dpg_get_value, dpg_set_value
from node.node_abc import DpgNodeABC
from node_editor.util import convert_cv_to_dpg

def image_process(image):
    image = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    image = image[3:12,0:16]
    image = cv2.resize(image,dsize=(1280,720))
    ret, mask_image = cv2.threshold(image,1,255 ,cv2.THRESH_BINARY)
    image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    color_image = cv2.applyColorMap(image, cv2.COLORMAP_JET)
    output_image = cv2.bitwise_and(color_image,color_image,mask = mask_image)
    return output_image

class Node(DpgNodeABC):
    _ver = '0.0.1'

    node_label = 'SoundCam'
    node_tag = 'SoundCamera'

    _opencv_setting_dict = None

    def __init__(self):
        pass

    def add_node(
        self,
        parent,
        node_id,
        pos=[0, 0],
        opencv_setting_dict=None,
        callback=None,
    ):
        # タグ名
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_node_input01_name = tag_node_name + ':' + self.TYPE_INT + ':Input01'
        tag_node_input01_value_name = tag_node_name + ':' + self.TYPE_INT + ':Input01Value'
        tag_node_output01_name = tag_node_name + ':' + self.TYPE_IMAGE + ':Output01'
        tag_node_output01_value_name = tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'
        tag_node_output02_name = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02'
        tag_node_output02_value_name = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'

        # OpenCV向け設定
        self._opencv_setting_dict = opencv_setting_dict
        small_window_w = self._opencv_setting_dict['input_window_width']
        small_window_h = self._opencv_setting_dict['input_window_height']
        serial_device_no_list = self._opencv_setting_dict['serial_device_no_list']
        use_pref_counter = self._opencv_setting_dict['use_pref_counter']

        # 初期化用黒画像
        black_image = np.zeros((small_window_w, small_window_h, 3))
        black_texture = convert_cv_to_dpg(
            black_image,
            small_window_w,
            small_window_h,
        )

        # テクスチャ登録
        with dpg.texture_registry(show=False):
            dpg.add_raw_texture(
                small_window_w,
                small_window_h,
                black_texture,
                tag=tag_node_output01_value_name,
                format=dpg.mvFormat_Float_rgb,
            )

        # ノード
        with dpg.node(
                tag=tag_node_name,
                parent=parent,
                label=self.node_label,
                pos=pos,
        ):
            # COM No選択 コンボボックス
            with dpg.node_attribute(
                    tag=tag_node_input01_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    serial_device_no_list,
                    width=small_window_w - 80,
                    label="COM No",
                    tag=tag_node_input01_value_name,
                )
            # カメラ画像
            with dpg.node_attribute(
                    tag=tag_node_output01_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_image(tag_node_output01_value_name)
            # 処理時間
            if use_pref_counter:
                with dpg.node_attribute(
                        tag=tag_node_output02_name,
                        attribute_type=dpg.mvNode_Attr_Output,
                ):
                    dpg.add_text(
                        tag=tag_node_output02_value_name,
                        default_value='elapsed time(ms)',
                    )

        return tag_node_name

    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
    ):
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_value01_tag = tag_node_name + ':' + self.TYPE_INT + ':Input01Value'
        output_value01_tag = tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'
        output_value02_tag = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'

        serial_device_no_list = self._opencv_setting_dict['serial_device_no_list']
        serial_connection_list = self._opencv_setting_dict['serial_connection_list']
        small_window_w = self._opencv_setting_dict['input_window_width']
        small_window_h = self._opencv_setting_dict['input_window_height']
        use_pref_counter = self._opencv_setting_dict['use_pref_counter']

        # COM Name取得
        com_name = dpg_get_value(input_value01_tag)

        # Serial接続のインスタンス取得
        serial_connection = None

        # 計測開始
        if com_name != '' and use_pref_counter:
            start_time = time.perf_counter()

        # soundmap取得
        frame = None
        if com_name != "":
            com_no = serial_device_no_list.index(com_name)
            serial_connection = serial_connection_list[com_no]
            if serial_connection.in_waiting:
                try:
                    frame = serial_connection.readline().decode()
                    frame = json.loads(frame)
                    frame = np.array(frame,dtype=np.uint8)
                    if frame.shape != (16, 16):
                        frame = None
                    #print(frame)
                except:
                    frame = None

        # グレースケール化
        if frame is not None:
            frame = image_process(frame)

        # 計測終了
        if com_name != '' and use_pref_counter:
            elapsed_time = time.perf_counter() - start_time
            elapsed_time = int(elapsed_time * 1000)
            dpg_set_value(output_value02_tag,
                          str(elapsed_time).zfill(4) + 'ms')

        # 描画
        if frame is not None:
            texture = convert_cv_to_dpg(
                frame,
                small_window_w,
                small_window_h,
            )
            dpg_set_value(output_value01_tag, texture)

        return frame, None

    def close(self, node_id):
        pass

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag

        pos = dpg.get_item_pos(tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        pass

