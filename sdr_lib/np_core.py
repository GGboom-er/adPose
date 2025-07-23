# coding:utf-8
import json
import os.path
import shutil
import subprocess
import sys
try:
    import numpy as np
except ImportError:
    np = None


ITER_COUNT = 15


def solve_anis_points(orig_points, joints_bind_matrix, weights, anis_joints_matrix):
    u"""
    已知蒙皮权重，骨骼动画，计算顶点动画
    @param orig_points: 模型初始形状
    @param joints_bind_matrix: 骨骼初始位置
    @param weights: 蒙皮权重
    @param anis_joints_matrix: 骨骼动画
    @return: anis_points 模型顶点动画
    """
    # 骨骼初始矩阵的逆矩阵 乘以 骨骼动画矩阵 等于 骨骼的变化矩阵
    anis_joints_transform = np.matmul(np.linalg.inv(joints_bind_matrix), anis_joints_matrix)
    # 模型初始点坐标 乘以 骨骼变化矩阵 等于 模型点跟完全随骨骼变化后的模型刚性点坐标
    rigid_points = np.matmul(orig_points, anis_joints_transform)
    # 刚性点坐标 乘以 骨骼权重, 得到模型加权坐标
    weight_points = rigid_points * weights.T[None, :, :, None]
    # 模型加权坐标求和 得到 模型经过蒙皮计算后的坐标
    anis_points = np.sum(weight_points, axis=1)
    return anis_points


def re_center_joint_matrix(orig_points, weights, anis_points, scale=False):
    u"""
    以按骨骼权重加权平均，重置骨骼中心点，预估骨骼动画
    @param orig_points: 模型初始形状
    @param weights: 蒙皮权重
    @param anis_points: 顶点动画
    @param scale: 是否匹配缩放
    @return:
    """
    # 模型初始点按骨骼权重加权平均，求中心点，即骨骼初始位置
    weights_t1 = weights.T[:, :, None]
    orig_center = np.sum(orig_points[None, :] * weights_t1, axis=1) / np.sum(weights_t1, axis=1)
    # 模型初始点减去中心的点,并按骨骼权重加权，得到点云
    orig_point_cloud = ((orig_points[None, :] - orig_center[:, None]) * weights_t1)[:, :, :3]

    # 计算动画点云
    weights_t2 = weights_t1[None, :]
    anis_center = np.sum(anis_points[:, None] * weights_t2, axis=2) / np.sum(weights_t2, axis=2)
    anis_point_cloud = ((anis_points[:, None] - anis_center[:, :, None]) * weights_t2)[:, :, :, :3]

    # 声明点云骨骼动画
    joint_count = weights.shape[1]
    ani_count = anis_points.shape[0]
    re_anis_joints_matrix = np.full([ani_count, joint_count, 4, 4], np.eye(4))
    re_joints_bind_matrix = np.full([joint_count, 4, 4], np.eye(4))
    # 设置点云中心为骨骼动画位置
    re_anis_joints_matrix[:, :, 3] = anis_center
    re_joints_bind_matrix[:, 3] = orig_center

    # 奇异值分解，得到orig_point_cloud变换到anim_point_cloud的旋转矩阵
    orig_point_cloud_t = orig_point_cloud.transpose(0, 2, 1)
    U, S, V = np.linalg.svd(np.matmul(orig_point_cloud_t, anis_point_cloud))
    # 正交化，防止负缩放的情况出现
    U[:, :, 2] = np.cross(U[:, :, 0], U[:, :, 1], axis=2)
    V[:, :, 2] = np.cross(V[:, :, 0], V[:, :, 1], axis=2)
    if scale:
        # S是一个缩放矩阵，S[0][0]是最大特征值，选取特征值最大的帧数
        max_scale_frame = np.argmax(S[:, :, 0], axis=0)
        for joint in range(joint_count):
            # U为缩放方向， 将骨骼的初始轴向与缩放方向对齐
            max_scale_u = U[max_scale_frame[joint]][joint]
            re_joints_bind_matrix[joint, :3, :3] = max_scale_u.T
        rotate = np.matmul(np.matmul(re_joints_bind_matrix[:, :3, :3], U), V)
        re_anis_joints_matrix[:, :, :3, :3] = rotate
    else:
        rotate = np.matmul(U, V)
        re_anis_joints_matrix[:, :, :3, :3] = rotate
    return re_joints_bind_matrix, re_anis_joints_matrix


def update_anis_joints_point(orig_points, joints_bind_matrix, weights, anis_points, anis_joints_matrix, joints):
    u"""
    根据顶点动画与蒙皮结构的差异，移动骨骼
    @param orig_points: 模型初始形状
    @param joints_bind_matrix: 骨骼初始位置
    @param weights: 蒙皮权重
    @param anis_points 模型顶点动画
    @param anis_joints_matrix: 骨骼动画
    @param joints: 修改位置的骨骼
    @return:
    """
    # 求蒙皮结果
    skin_anis_points = solve_anis_points(orig_points, joints_bind_matrix, weights, anis_joints_matrix)
    # 求顶点动画与蒙皮结果的差异
    anis_offsets = (anis_points - skin_anis_points)[:, :, :3]
    # 骨骼偏移量 = （顶点偏移 叉乘 权重）除以 (权重叉乘权重)
    # joint_translation = dot(joint_anis_offsets, joint_weights)/dot(joint_weights, joint_weights)
    # anis_offsets时所有骨骼的偏移量，按权重加权，为对应骨骼应造成的偏移量
    # joint_anis_offsets = anis_offsets * joint_weights
    # 将joint_weights代入上式
    # joint_translation = dot(anis_offsets * joint_weights, joint_weights)/dot(joint_weights, joint_weights)
    # joint_translation = sum(anis_offsets * joint_weights * joint_weights)/sum(joint_weights * joint_weights)
    # joint_translation = sum(anis_offsets * joint_weights_square)/sum(joint_weights_square)
    weights_square = np.square(weights[None, :, :, None])
    anis_joints_translation = np.sum(anis_offsets[:, :, None, :]*weights_square, axis=1)/np.sum(weights_square, axis=1)
    anis_joints_matrix[:, joints, 3, :3] += anis_joints_translation[:, joints]


def update_anis_joints_rotation(orig_points, joints_bind_matrix, weights, anis_points, anis_joints_matrix, joints=None):
    u"""
    根据顶点动画与蒙皮结构的差异，旋转骨骼
    @param orig_points: 模型初始形状
    @param joints_bind_matrix: 骨骼初始位置
    @param weights: 蒙皮权重
    @param anis_points 模型顶点动画
    @param anis_joints_matrix: 骨骼动画
    @param joints: 修改位置的骨骼
    @return:
    """
    if joints is None:
        joints = slice(None, None, None)
    # 求模型动画坐标与模型蒙皮坐标的差
    skin_anis_points = solve_anis_points(orig_points, joints_bind_matrix, weights, anis_joints_matrix)
    anis_offsets = anis_points - skin_anis_points
    # 求模型点在joints_bind_matrix下的点云
    orig_point_cloud = np.matmul(orig_points, np.linalg.inv(joints_bind_matrix))
    # 求模型点在anis_joints_matrix下的点云
    anis_point_cloud = orig_point_cloud[None, ] + np.matmul(anis_offsets[:, None], np.linalg.inv(anis_joints_matrix))
    # 将点云并按骨骼权重加权
    orig_point_cloud = (orig_point_cloud * weights.T[:, :, None])[:, :, :3]
    anis_point_cloud = (anis_point_cloud * weights.T[None, :, :, None])[:, :, :, :3]
    # 奇异值分解，得到orig_point_cloud变换到anim_point_cloud的旋转矩阵
    orig_point_cloud_t = orig_point_cloud.transpose(0, 2, 1)
    U, S, V = np.linalg.svd(np.matmul(orig_point_cloud_t, anis_point_cloud))
    rotate = np.matmul(U, V)
    rotate[:, :, 2] = np.cross(rotate[:, :, 0], rotate[:, :, 1], axis=2)
    # 修改旋转矩阵
    anis_joints_matrix[:, joints, :3, :3] = np.matmul(rotate, anis_joints_matrix[:, :, :3, :3])[:, joints]


def update_anis_joints_scale(orig_points, joints_bind_matrix, weights, anis_points, anis_joints_matrix, joints=None):
    u"""
    根据顶点动画与蒙皮结构的差异，旋转骨骼
    @param orig_points: 模型初始形状
    @param joints_bind_matrix: 骨骼初始位置
    @param weights: 蒙皮权重
    @param anis_points 模型顶点动画
    @param anis_joints_matrix: 骨骼动画
    @param joints: 修改位置的骨骼
    @return:
    """
    if joints is None:
        joints = slice(None, None, None)
    # 求模型动画坐标与模型蒙皮坐标的差
    skin_anis_points = solve_anis_points(orig_points, joints_bind_matrix, weights, anis_joints_matrix)
    anis_offsets = anis_points - skin_anis_points
    # 求模型点在joints_bind_matrix下的点云
    orig_point_cloud = np.matmul(orig_points, np.linalg.inv(joints_bind_matrix))
    # 求模型点在anis_joints_matrix下的点云
    anis_point_cloud = orig_point_cloud[None, ] + np.matmul(anis_offsets[:, None], np.linalg.inv(anis_joints_matrix))
    # 将点云并按骨骼权重加权
    orig_point_cloud = (orig_point_cloud * weights.T[:, :, None])[:, :, :3]
    anis_point_cloud = (anis_point_cloud * weights.T[None, :, :, None])[:, :, :, :3]
    orig_point_cloud = orig_point_cloud[None]
    scale = np.sum(orig_point_cloud * anis_point_cloud, axis=2)/np.sum(orig_point_cloud * orig_point_cloud, axis=2)
    anis_joints_matrix[:, joints, :3, :3] *= scale[:, joints, :, None]


def update_anis_joints_matrix(orig_points, joints_bind_matrix, weights, anis_joints_matrix, anis_points, joints, scale):
    u"""
    已知顶点动画，蒙皮权重，旧骨骼，计算新增骨骼动画
    @param orig_points: 模型初始形状
    @param joints_bind_matrix: 骨骼初始位置
    @param weights: 蒙皮权重
    @param anis_joints_matrix: 骨骼动画
    @param anis_points: 顶点动画
    @param joints: 旧骨骼
    @param scale: 是否匹配缩放
    @return:
    """
    joints_bind_matrix[joints], anis_joints_matrix[:, joints] = re_center_joint_matrix(
        orig_points, weights[:, joints], anis_points, scale)
    for i in range(ITER_COUNT):
        update_anis_joints_point(orig_points, joints_bind_matrix, weights, anis_points, anis_joints_matrix, joints)
        update_anis_joints_rotation(orig_points, joints_bind_matrix, weights, anis_points, anis_joints_matrix, joints)
    if scale:
        for _ in range(ITER_COUNT):
            update_anis_joints_point(orig_points, joints_bind_matrix, weights, anis_points, anis_joints_matrix, joints)
            update_anis_joints_scale(orig_points, joints_bind_matrix, weights, anis_points, anis_joints_matrix, joints)
    return joints_bind_matrix, anis_joints_matrix


def weight_regression(rigid_points, anis_points, max_weights):
    u"""
    anis_points = dot(rigid_points, weights)
    @param rigid_points: 模型点跟完全随骨骼变化后的模型刚性点坐标
    @param anis_points: 模型顶点动画
    @param max_weights: 最大权重
    @return: 骨骼权重
    """
    joint_count = rigid_points.shape[1]
    vtx_count = anis_points.shape[0]
    weights = np.full([vtx_count, joint_count], 1.0/joint_count)
    weights *= max_weights[:, None]
    joints = np.arange(joint_count)
    for _ in range(ITER_COUNT):
        for joint_id in range(joint_count):
            # edit_weights, 当前骨骼权重增加1时，其它骨骼权重按原权重比例减少，共计减少1
            other_joints = np.delete(joints, joint_id)
            edit_weights = weights.copy()
            rest_weights = np.sum(edit_weights[:, other_joints], axis=1)
            edit_weights[rest_weights < 0.001] = 1.0/(joint_count-1)
            rest_weights = np.sum(edit_weights[:, other_joints], axis=1)
            edit_weights /= -rest_weights[:, None]
            edit_weights[:, joint_id] = 1.0
            # 当权重增加1时，模型点变化量
            edit_points = np.sum(rigid_points * edit_weights[:, :, None], axis=1)
            rest_points = anis_points - np.sum(rigid_points * weights[:, :, None], axis=1)
            # edit_weight = dot(edit_points, rest_points)/ dot(edit_points, edit_points)
            edit_weight = np.sum(edit_points*rest_points, axis=1)/np.sum(edit_points*edit_points, axis=1)
            # 限制权重修改范围在0-1之间
            edit_weight = np.clip(edit_weight, 0-weights[:, joint_id], max_weights-weights[:, joint_id])
            # 修改权重
            weights += edit_weights * edit_weight[:, None]
    return weights


def limit_max_influence(weights, rigid_points, anis_points, max_influence, max_weights):
    max_influence_joint_ids = np.argsort(weights, axis=1)[:, -max_influence:]
    max_influence_rigid_points = np.zeros([weights.shape[0], max_influence, rigid_points.shape[2]])
    for i in range(weights.shape[0]):
        max_influence_rigid_points[i] = rigid_points[i, max_influence_joint_ids[i]]
    max_influence_weights = weight_regression(max_influence_rigid_points, anis_points, max_weights)
    weights[:, :] = 0
    for i in range(weights.shape[0]):
        weights[i, max_influence_joint_ids[i]] = max_influence_weights[i]


def solve_weights(orig_points, joints_bind_matrix, anis_joints_matrix, anis_points, max_influence, max_weights):
    u"""
    已知顶点动画， 蒙皮权重，计算骨骼动画
    @param orig_points: 模型初始形状
    @param joints_bind_matrix: 骨骼初始位置
    @param anis_joints_matrix: 骨骼动画
    @param anis_points: 顶点动画
    @param max_influence: 最大影响数
    @param max_weights: 最大权重
    @return:
    """
    vtx_count = orig_points.shape[0]
    joint_count = joints_bind_matrix.shape[0]
    ani_count = anis_points.shape[0]
    # 骨骼初始矩阵的逆矩阵 乘以 骨骼动画矩阵 等于 骨骼的变化矩阵
    anis_joints_transform = np.matmul(np.linalg.inv(joints_bind_matrix), anis_joints_matrix)
    # 模型初始点坐标 乘以 骨骼变化矩阵 等于 模型点跟完全随骨骼变化后的模型刚性点坐标
    rigid_points = np.matmul(orig_points, anis_joints_transform)
    # 重构数据结构
    rigid_points = rigid_points.transpose([2, 1, 0, 3])[:, :, :, :3].reshape(vtx_count, joint_count, ani_count*3)
    anis_points = anis_points.transpose([1, 0, 2])[:, :, :3].reshape(vtx_count, ani_count*3)
    # 计算权重
    weights = weight_regression(rigid_points, anis_points, max_weights)
    if max_influence and max_influence < joint_count:
        limit_max_influence(weights, rigid_points, anis_points, max_influence, max_weights)
    return weights


def update_weights(orig_points, joints_bind_matrix, anis_joints_matrix, anis_points, max_influence, weights, joints):
    skin_points = solve_anis_points(
        orig_points,
        np.delete(joints_bind_matrix, joints, axis=0),
        np.delete(weights, joints, axis=1),
        np.delete(anis_joints_matrix, joints, axis=1),
    )
    rest_points = anis_points - skin_points
    max_weights = np.sum(weights[:, joints], axis=1)
    weights[:, joints] = solve_weights(
        orig_points,
        joints_bind_matrix[joints],
        anis_joints_matrix[:, joints],
        rest_points,
        max_influence,
        max_weights
    )


def joint_transform_group(joints_bind_matrix, anis_joints_matrix):
    u"""
    如果骨骼所有帧的变化都相同，将归类为同一组
    @param joints_bind_matrix: 骨骼蒙皮时的初始矩阵
    @param anis_joints_matrix: 每帧动画所有骨骼的矩阵
    @return:
    """
    joint_count = anis_joints_matrix.shape[1]
    frame_count = anis_joints_matrix.shape[0]
    # 求每个骨骼变换变换矩阵
    anis_joins_transform = np.matmul(np.linalg.inv(joints_bind_matrix), anis_joints_matrix)
    # 将骨骼多帧变换矩阵合并到同一维度
    joins_transform = anis_joins_transform.transpose([1, 0, 2, 3]).reshape(joint_count, 4*4*frame_count)
    # 声明未分组的骨骼id
    rest_joints = np.arange(0, joint_count, 1)
    # 声明已分组的骨骼
    groups = []
    for i in range(1000):  # while True 防无限循环
        if rest_joints.shape[0] == 0:
            break
        # 去除已分组的骨骼变换矩阵
        rest_joins_transform = joins_transform[rest_joints]
        # 求骨骼变换矩阵的差异
        transform_diff = np.sum(np.square(rest_joins_transform - rest_joins_transform[0]), axis=1)
        # 将进行相同变换的骨骼归为一组
        same_filter = transform_diff < 0.00001
        # 记录同组的骨骼id
        groups.append(rest_joints[same_filter].tolist())
        # 移除已分组的骨骼id
        rest_joints = np.delete(rest_joints, np.arange(0, rest_joints.shape[0], 1)[same_filter])
    return groups


def merge_joint_weights(weights, groups, unlock_joints):
    u"""
    合并具有相同动画的骨骼数据，减少计算量
    @param weights: 权重
    @param groups:  骨骼蒙皮时的初始矩阵
    @param unlock_joints: 未锁定骨骼，需要计算权重
    @return:
    """
    # 按锁定权重分类
    lock_groups = list(filter(bool, [[i for i in ids if i not in unlock_joints] for ids in groups]))
    # 按未锁定骨骼分类
    unlock_groups = list(filter(bool, [[i for i in ids if i in unlock_joints] for ids in groups]))
    # 同组骨骼当作一个骨骼来计算，权重取同组骨骼权重之和
    groups = lock_groups + unlock_groups
    joint_count = len(groups)
    vtx_count = weights.shape[0]
    new_weights = np.zeros([vtx_count, joint_count])
    for i, group in enumerate(groups):
        new_weights[:, i] = np.sum(weights[:, group], axis=1)
    # 未锁定的同组骨骼，当作一个骨骼来计算出权重，需要按照原本的权重比例，再将权重拆分
    split_weights = []
    for unlock_joints in unlock_groups:
        group_weights = weights[:, unlock_joints]
        group_weights[np.sum(group_weights, axis=1) < 0.001] = 1
        group_weights /= np.sum(group_weights, axis=1)[:, None]
        split_weights.append(group_weights)
    return new_weights, split_weights, groups


def new_joint_weights(anis_points, skin_points, new_joint_count, split_count, weights):
    # 选取融合变形修形量较大的部分顶点进行聚类
    ani_count = anis_points.shape[0]
    vtx_count = anis_points.shape[1]
    # 顶点动画与蒙皮结果的差，为修形向量
    vectors = anis_points - skin_points
    vectors = vectors[:, :, :3].transpose(1, 0, 2).reshape(vtx_count, ani_count*3)
    lengths = np.sum(np.square(vectors), axis=1)
    lengths /= np.max(lengths)
    anis_points = anis_points[:, :, :3].transpose(1, 0, 2).reshape(vtx_count, ani_count*3)
    # 选取修型最大的点作为簇点
    cluster_ids = [np.argmax(lengths)]
    for _ in range(new_joint_count-1):
        # 选取一个与簇点差异度最大点的做为新簇点
        distances = np.sum(np.square(vectors[:, None] - vectors[cluster_ids][None]), axis=2)
        distances *= (lengths[:, None] * lengths[cluster_ids][None])
        cluster_ids.append(np.argmax(np.min(distances, axis=1)))
    # 聚类时，同时考虑点坐标位置和bs修形态方向
    # 将位置相近，修形变化相同的点，聚类到一起
    points = np.concatenate([vectors, anis_points], axis=1)
    clusters = points[cluster_ids]
    # 聚类
    for _ in range(ITER_COUNT):
        distances = np.sum(np.square(points[:, None] - clusters[None]), axis=2)
        groups = (np.eye(new_joint_count) > 0)[np.argmin(distances, axis=1)].T
        for i in range(new_joint_count):
            k_lengths = lengths[groups[i]]
            k_lengths /= np.sum(k_lengths)
            # 求新簇点时，按修形向量大小加权平均
            cluster = np.sum(points[groups[i]] * k_lengths[:, None], axis=0)
            clusters[i] = cluster

    # 将顶点权重按长度比例赋予最近的簇点
    distances = np.sum(np.square(points[:, None] - clusters[None]), axis=2)
    new_weights = np.eye(new_joint_count)[np.argmin(distances, axis=1)]
    max_weights = np.sum(weights[:, -split_count:], axis=1)
    new_weights *= (max_weights * lengths)[:, None]
    weights[:, -split_count:] *= (1-lengths)[:, None]
    weights = np.concatenate([weights, new_weights], axis=1)
    return weights


def part_deform_to_skin(orig_points, joints_bind_matrix, weights, anis_joints_matrix, anis_points,
                        unlock_joints, max_influence, new_joint_count, iter_count, scale=False):
    u"""
    局部的修形变形转骨骼蒙皮动画
    @param orig_points: 模型初始形状
    @param joints_bind_matrix: 骨骼初始位置
    @param weights: 蒙皮权重
    @param anis_joints_matrix: 骨骼动画
    @param anis_points: 顶点动画
    @param unlock_joints: 未锁定的骨骼
    @param max_influence: 最大影响数
    @param new_joint_count: 新增的骨骼数
    @param iter_count: 迭代次数
    @param scale: 是否缩放骨骼
    @return:
    """
    global ITER_COUNT
    ITER_COUNT = iter_count
    vtx_count = orig_points.shape[0]
    vertices = np.arange(vtx_count)
    cache_weights = weights
    # 移除未锁定骨骼没有权重的点数据
    cut = np.sum(weights[:, unlock_joints], axis=1) > 0.001
    orig_points, weights, anis_points, vertices = orig_points[cut], weights[cut], anis_points[:, cut], vertices[cut]
    print("remove unlock joint has not weight vtx")

    # 如果骨骼所有帧的变化都相同，将归类为同一组
    groups = joint_transform_group(joints_bind_matrix, anis_joints_matrix)
    # 合并具有相同动画的骨骼数据，减少计算量
    weights, split_weights, groups = merge_joint_weights(weights, groups, unlock_joints)
    joints = [group[0] for group in groups]
    joints_bind_matrix = joints_bind_matrix[joints]
    anis_joints_matrix = anis_joints_matrix[:, joints]
    print("merge same ani joint")

    # 移除顶点动画与蒙皮结果相同的点数据
    skin_points = solve_anis_points(orig_points, joints_bind_matrix, weights, anis_joints_matrix)
    cut = np.sum(np.sum(np.square(anis_points - skin_points), axis=0), axis=1) > 0.00001
    orig_points, weights, anis_points, vertices = orig_points[cut], weights[cut], anis_points[:, cut], vertices[cut]
    split_weights = [split[cut] for split in split_weights]
    print("remove no deform vtx")

    # 生成新的骨骼数据
    skin_points = solve_anis_points(orig_points, joints_bind_matrix, weights, anis_joints_matrix)
    split_count = len(split_weights)
    ani_count = anis_joints_matrix.shape[0]
    weights = new_joint_weights(anis_points, skin_points, new_joint_count, split_count, weights)
    joints_bind_matrix = np.concatenate([joints_bind_matrix, np.zeros([new_joint_count, 4, 4])])
    anis_joints_matrix = np.concatenate([anis_joints_matrix, np.zeros([ani_count, new_joint_count, 4, 4])], axis=1)
    print("create new joints")

    # 更新骨骼动画与权重
    joint_count = joints_bind_matrix.shape[0]
    joints = np.arange(joint_count)
    new_joints = joints[-new_joint_count:]
    update_weight_joints = joints[-new_joint_count-split_count:]
    for _ in range(ITER_COUNT):
        update_anis_joints_matrix(
            orig_points, joints_bind_matrix, weights, anis_joints_matrix, anis_points, new_joints, scale)
        update_weights(
            orig_points,
            joints_bind_matrix,
            anis_joints_matrix,
            anis_points,
            max_influence,
            weights,
            update_weight_joints
        )

        skin_points = solve_anis_points(orig_points, joints_bind_matrix, weights, anis_joints_matrix)
        err = np.sum(np.square(anis_points-skin_points))
        print("update joint weight animation %i err: %.6f" % (_, err))


    # 将未锁定骨骼权重，按原权重比例分给同组的骨骼
    vtx_count = weights.shape[0]
    unlock_weights = np.zeros([vtx_count, len(unlock_joints)])
    for split, group, joint in zip(split_weights, groups[-split_count:], joints[-new_joint_count-split_count:]):
        unlock_indexes = [unlock_joints.tolist().index(i) for i in group]
        unlock_weights[:, unlock_indexes] = weights[:, joint, None] * split
    weights = np.concatenate([unlock_weights, weights[:, new_joints]], axis=1)
    # 计算跟随权重
    follow_weights = cache_weights[vertices][:, None, unlock_joints]
    follow_weights = follow_weights * weights[:, -new_joint_count:, None]
    follow_weights = np.sum(follow_weights, axis=0)
    sum_weights = np.sum(follow_weights, axis=1)
    follow_weights[follow_weights < 0.1] = 0
    follow_weights /= sum_weights[:, None]
    follow_weights[sum_weights < 0.0001] = 1.0/unlock_joints.shape[0]
    return joints_bind_matrix[new_joints], anis_joints_matrix[:, new_joints], vertices, weights, follow_weights


def run_in_numpy_maya(fun, *args, **kwargs):
    # 将参数从list转array并将返回值从array转为list
    args = [np.array(arg) if isinstance(arg, list) else arg for arg in args]
    kwargs = {key: np.array(arg) if isinstance(arg, list) else arg for key, arg in kwargs.items()}
    result = fun(*args, **kwargs)
    print("np run over")
    if isinstance(result, np.ndarray):
        return result.tolist()
    elif isinstance(result, tuple):
        return [r.tolist() for r in result]
    else:
        return result


def run_in_no_numpy_maya(fun, *args, **kwargs):
    data = dict(
        fun=fun.__name__,
        args=args,
        kwargs=kwargs
    )
    path = os.path.abspath(__file__+"/../data.json")
    with open(path, "w") as fp:
        json.dump(data, fp, indent=4)

    cmd = os.path.abspath(__file__+"/../np_core.exe").replace("\\", "/")
    sub = subprocess.Popen(cmd)
    sub.wait()
    with open(path, "r") as fp:
        result = json.load(fp)
    return result


def run(fun, *args, **kwargs):
    if np is None:
        return run_in_no_numpy_maya(fun, *args, **kwargs)
    else:
        return run_in_numpy_maya(fun, *args, **kwargs)


def run_in_exe():
    path = os.path.abspath(sys.argv[0]+"/../data.json")
    # path = "D:/dev/tools/x3_P4/scripts/adPose2_FKSdk/adPose2/sdr_lib/data.json"
    with open(path, "r") as fp:
        data = json.load(fp)
    result = run_in_numpy_maya(globals()[data["fun"]], *data["args"], **data["kwargs"])
    with open(path, "w") as fp:
        json.dump(result, fp, indent=4)


def run_in_python():
    # 打包python文件成exe
    pyinstaller_path = "C:/Users/mengya/AppData/Local/Programs/Python/Python310/Scripts/pyinstaller.exe"
    py_path = __file__
    name = os.path.splitext(os.path.split(__file__)[-1])[0]
    cmd = '"{0}" -F "{1}"'.format(pyinstaller_path, py_path)
    cwd = os.path.abspath(__file__+"/../temp/").replace("\\", "/")
    if not os.path.isdir(cwd):
        os.makedirs(cwd)
    popen = subprocess.Popen(cmd, cwd=cwd)
    popen.wait()
    src_exe = os.path.abspath(py_path+"/../temp/dist/{0}.exe".format(name)).replace("\\", "/")
    dst_exe = os.path.abspath(py_path+"/../{0}.exe".format(name)).replace("\\", "/")
    if os.path.isfile(dst_exe):
        os.remove(dst_exe)
    shutil.copyfile(src_exe, dst_exe)
    shutil.rmtree(cwd)


def main():
    _, ext = os.path.splitext(sys.argv[0])
    if ext in [".py"]:
        run_in_python()
    else:
        run_in_exe()


if __name__ == '__main__':
    main()
