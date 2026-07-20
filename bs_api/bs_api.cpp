#include <Eigen/Dense>
#include <omp.h>

using namespace Eigen;

extern "C" {
    __declspec(dllexport) void invert_blendshape_m33(
        const double* offset_x,
        const double* offset_y,
        const double* offset_z,
        const double* base,
        double* m33,
        int point_count);
    __declspec(dllexport) void invert_points(
        const double* base,
        const double* target,
        const double* m33,
        double* points,
        int point_count);
    __declspec(dllexport) int zip_points(
        double* points,
        int* ids,
        int point_count);
    __declspec(dllexport) void unzip_points(
        const double* points,  // 压缩的点数组 (每个点4个double，但只用前3个)
        const int* ids,
        double* full_points,
        int use_count,
        int point_count);
    __declspec(dllexport) void remove_points(
        double* points,
        const int* ids,
        int point_count,
        int remove_count);
}


// 函数1: 计算并反转blendshape的3x3矩阵
void invert_blendshape_m33(
    const double* offset_x,
    const double* offset_y,
    const double* offset_z,
    const double* base,
    double* m33,
    int point_count)
{
    #pragma omp parallel for
    for (int i = 0; i < point_count; i++) {
        int base_idx = i * 3;
        int m33_idx = i * 9;

        // 构建3x3矩阵，每一行是一个offset减去base
        Matrix3d mat;
        mat(0, 0) = offset_x[base_idx + 0] - base[base_idx + 0];
        mat(0, 1) = offset_x[base_idx + 1] - base[base_idx + 1];
        mat(0, 2) = offset_x[base_idx + 2] - base[base_idx + 2];

        mat(1, 0) = offset_y[base_idx + 0] - base[base_idx + 0];
        mat(1, 1) = offset_y[base_idx + 1] - base[base_idx + 1];
        mat(1, 2) = offset_y[base_idx + 2] - base[base_idx + 2];

        mat(2, 0) = offset_z[base_idx + 0] - base[base_idx + 0];
        mat(2, 1) = offset_z[base_idx + 1] - base[base_idx + 1];
        mat(2, 2) = offset_z[base_idx + 2] - base[base_idx + 2];

        // 求逆矩阵
        Matrix3d inv_mat = mat.inverse();

        // 存储结果 (按行优先存储)
        for (int r = 0; r < 3; r++) {
            for (int c = 0; c < 3; c++) {
                m33[m33_idx + r * 3 + c] = inv_mat(r, c);
            }
        }
    }
}

// 函数2: 通过反转矩阵变换点
void invert_points(
    const double* base,
    const double* target,
    const double* m33,
    double* points,
    int point_count)
{
    #pragma omp parallel for
    for (int i = 0; i < point_count; i++) {
        int base_idx = i * 3;
        int m33_idx = i * 9;

        // 计算世界空间的偏移向量
        Vector3d world_v;
        world_v(0) = target[base_idx + 0] - base[base_idx + 0];
        world_v(1) = target[base_idx + 1] - base[base_idx + 1];
        world_v(2) = target[base_idx + 2] - base[base_idx + 2];

        // 加载3x3矩阵
        Matrix3d mat;
        for (int r = 0; r < 3; r++) {
            for (int c = 0; c < 3; c++) {
                mat(r, c) = m33[m33_idx + r * 3 + c];
            }
        }

        // 矩阵乘法: world_v * mat
        Vector3d result = world_v.transpose() * mat;

        // 存储结果
        points[base_idx + 0] = result(0);
        points[base_idx + 1] = result(1);
        points[base_idx + 2] = result(2);
    }
}

// 函数3: 压缩点数据，移除接近零的点
int zip_points(
    double* points,
    int* ids,
    int point_count)
{
    const double threshold = 1e-5;

    // 第一遍：计算非零点的数量
    int use_count = 0;
    for (int i = 0; i < point_count; i++) {
        int idx = i * 3;
        double norm = sqrt(
            points[idx + 0] * points[idx + 0] +
            points[idx + 1] * points[idx + 1] +
            points[idx + 2] * points[idx + 2]
        );
        if (norm > threshold) {
            use_count++;
        }
    }

    // 第二遍：收集非零点
    int write_idx = 0;
    for (int i = 0; i < point_count; i++) {
        int idx = i * 3;
        double norm = sqrt(
            points[idx + 0] * points[idx + 0] +
            points[idx + 1] * points[idx + 1] +
            points[idx + 2] * points[idx + 2]
        );
        if (norm > threshold) {
            ids[write_idx] = i;
            if (write_idx != i) {
                points[write_idx * 3 + 0] = points[idx + 0];
                points[write_idx * 3 + 1] = points[idx + 1];
                points[write_idx * 3 + 2] = points[idx + 2];
            }
            write_idx++;
        }
    }

    return use_count;
}

// 函数4: 解压缩点数据，恢复完整数组
void unzip_points(
    const double* points,  // 压缩的点数组 (每个点4个double，但只用前3个)
    const int* ids,
    double* full_points,
    int use_count,
    int point_count)
{
    // 首先将所有点清零
    #pragma omp parallel for
    for (int i = 0; i < point_count * 3; i++) {
        full_points[i] = 0.0;
    }

    // 根据ids恢复点
    #pragma omp parallel for
    for (int i = 0; i < use_count; i++) {
        int target_idx = ids[i];
        int source_idx = i * 4;  // 输入是4元素数组

        full_points[target_idx * 3 + 0] = points[source_idx + 0];
        full_points[target_idx * 3 + 1] = points[source_idx + 1];
        full_points[target_idx * 3 + 2] = points[source_idx + 2];
    }
}

// 函数5: 移除指定的点（设为0）
void remove_points(
    double* points,
    const int* ids,
    int point_count,
    int remove_count)
{
    #pragma omp parallel for
    for (int i = 0; i < remove_count; i++) {
        int idx = ids[i] * 3;
        points[idx + 0] = 0.0;
        points[idx + 1] = 0.0;
        points[idx + 2] = 0.0;
    }
}
