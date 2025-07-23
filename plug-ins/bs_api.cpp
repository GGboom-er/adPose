#include "FunCToPy.h"
#include "maya/MGlobal.h"
#include <maya/MFnMesh.h>
#include <maya/MMatrix.h>
#include <maya/MMatrixArray.h>
#include <maya/MSelectionList.h>
#include <maya/MDagPath.h>
#include <maya/MPlug.h>
#include <maya/MFnComponentListData.h>
#include <maya/MFnSingleIndexedComponent.h>
#include <maya/MFnPointArrayData.h>
#include <maya/MFnBlendShapeDeformer.h>
#include <tuple>
#include <map>
#include <set>
#include <vector>
#include <fstream>

#include "tbb/tbb.h"
#include "json/json.h"
using namespace std;

void str_to_dag_path(MString name, MDagPath& dag_path) {
    MSelectionList selection_list;
    selection_list.add(name);
    selection_list.getDagPath(0, dag_path);
}

void str_to_depend_node(MString name, MObject& depend_node) {
    MSelectionList selection_list;
    selection_list.add(name);
    selection_list.getDependNode(0, depend_node);
}

void get_mesh_points(MString polygon_name, MPointArray& points) {
    MDagPath dag_path;
    str_to_dag_path(polygon_name, dag_path);
    MFnMesh fn_mesh(dag_path);
    fn_mesh.getPoints(points);
}

void set_mesh_points(MString polygon_name, MPointArray& points) {
    MDagPath dag_path;
    str_to_dag_path(polygon_name, dag_path);
    MFnMesh fn_mesh(dag_path);
    fn_mesh.setPoints(points);
}



void set_plug_ids(MPlug& plug, MIntArray& ids) {
    MFnSingleIndexedComponent fn_ids;
    MObject ids_obj = fn_ids.create(MFn::kMeshVertComponent);
    fn_ids.addElements(ids);
    MFnComponentListData fn_components;
    MObject obj = fn_components.create();
    fn_components.add(ids_obj);
    plug.setMObject(obj);
}


void set_plug_points(MPlug& plug, MPointArray& points) {
    MFnPointArrayData fn_points;
    MObject obj = fn_points.create(points);
    plug.setMObject(obj);
}

auto get_ipt_ict(MString bs_name, int index) {
    MPlug ipt, ict;
    MObject depend_node;
    str_to_depend_node(bs_name, depend_node);
    MFnDependencyNode fn_depend_node(depend_node);
    MPlug iti = fn_depend_node.findPlug("it", false).elementByLogicalIndex(0).child(0).elementByLogicalIndex(index).child(0).elementByLogicalIndex(6000);
    ipt = iti.child(iti.numChildren() - 2);
    ict = iti.child(iti.numChildren() - 1);
    return std::make_tuple(ipt, ict);
}

MPlug get_iti(MString bs_name, int index) {
    MObject depend_node;
    str_to_depend_node(bs_name, depend_node);
    MFnDependencyNode fn_depend_node(depend_node);
    MPlug iti = fn_depend_node.findPlug("it", false).elementByLogicalIndex(0).child(0).elementByLogicalIndex(index).child(0).elementByLogicalIndex(6000);
    return iti;
}

void set_bs_id_points(MString bs_name, int index, MIntArray& ids, MPointArray& points) {
    MPlug ipt, ict;
    MObject depend_node;
    str_to_depend_node(bs_name, depend_node);
    MFnDependencyNode fn_depend_node(depend_node);
    MPlug iti = fn_depend_node.findPlug("it", false).elementByLogicalIndex(0).child(0).elementByLogicalIndex(index).child(0).elementByLogicalIndex(6000);
    ipt = iti.child(iti.numChildren() - 2);
    ict = iti.child(iti.numChildren() - 1);
    set_plug_points(ipt, points);
    set_plug_ids(ict, ids);
}

void init_target(MString bs_name, int index) {
    MIntArray ids;
    MPointArray points;
    set_bs_id_points(bs_name, index, ids, points);
}
    

void set_bs_points(MString bs_name, int index, MPointArray& all_points) {
    MIntArray ids;
    MPointArray points;
    int vtx_length = all_points.length();
    for (int vtx_id = 0; vtx_id < vtx_length; vtx_id++) {
        if (all_points[vtx_id].distanceTo(MPoint()) < 0.00001){
            continue;
        }
        ids.append(vtx_id);
        points.append(all_points[vtx_id]);
    }
    set_bs_id_points(bs_name, index, ids, points);
}

MString find_history(MString polygon_name, MString typ_name) {
    MStringArray result;
    MGlobal::executeCommand("listHistory " + polygon_name, result);
    int length = result.length();
    for (int i = 0; i < length; i++) {
        MObject obj;
        str_to_depend_node(result[i], obj);
        MString api_type = obj.apiTypeStr();
        if (api_type == typ_name) {
            return result[i];
        }
    }
    return "";
}


MMatrixArray invert_shape_matrix_cache;

void save_invert_shape_matrix(MString polygon_name, MString orig_name) {
    MPointArray polygon_points;
    MPointArray orig_points;
    MString bs = find_history(polygon_name, "kBlendShape");
    MGlobal::executeCommand("setAttr \"" +bs + ".envelope\" 0;");
    get_mesh_points(polygon_name, polygon_points);
    get_mesh_points(orig_name, orig_points);
    int vtx_length = orig_points.length();
    invert_shape_matrix_cache.setLength(vtx_length);
    auto offset_orig = [&](int xyz_id) {
        MPointArray offset_points(orig_points);
        tbb::parallel_for(0, vtx_length, [&](int vtx_id) {
            offset_points[vtx_id][xyz_id] += 1;
        });
        set_mesh_points(orig_name, offset_points);
        get_mesh_points(polygon_name, offset_points);
        tbb::parallel_for(0, vtx_length, [&](int vtx_id) {
            MVector offset = offset_points[vtx_id] - polygon_points[vtx_id];
            invert_shape_matrix_cache[vtx_id][xyz_id][0] = offset.x;
            invert_shape_matrix_cache[vtx_id][xyz_id][1] = offset.y;
            invert_shape_matrix_cache[vtx_id][xyz_id][2] = offset.z;
            invert_shape_matrix_cache[vtx_id][xyz_id][3] = 0.0;
        });
    };
    offset_orig(0);
    offset_orig(1);
    offset_orig(2);
    set_mesh_points(orig_name, orig_points);
    MGlobal::executeCommand("setAttr \"" + bs + ".envelope\" 1;");
    get_mesh_points(polygon_name, polygon_points);
    tbb::parallel_for(0, vtx_length, [&](int vtx_id) {
        invert_shape_matrix_cache[vtx_id][3][0] = polygon_points[vtx_id].x;
        invert_shape_matrix_cache[vtx_id][3][1] = polygon_points[vtx_id].y;
        invert_shape_matrix_cache[vtx_id][3][2] = polygon_points[vtx_id].z;
        invert_shape_matrix_cache[vtx_id][3][3] = 1.0;
        invert_shape_matrix_cache[vtx_id] = invert_shape_matrix_cache[vtx_id].inverse();
    });
}


void cache_target(MString bs_name, int index, MString polygon_name, MString orig_name) {
    init_target(bs_name, index);
    save_invert_shape_matrix(polygon_name, orig_name);
}


void set_target(MString bs_name, int index, MString target_name) {
    MPointArray points;
    get_mesh_points(target_name, points);
    int vtx_length = points.length();
    tbb::parallel_for(0, vtx_length, [&](int vtx_id) {
        points[vtx_id] = points[vtx_id] * invert_shape_matrix_cache[vtx_id];
    });
    set_bs_points(bs_name, index, points);
}

void edit_target(MString bs_name, int index, MString target_name, MString polygon_name, MString orig_name) {
    cache_target(bs_name, index, polygon_name, orig_name);
    set_target(bs_name, index, target_name);
}


void edit_target(MString bs_name, int index, MString target_name, MString polygon_name) {
    init_target(bs_name, index);
    MPointArray polygon_points;
    MPointArray target_points;
    get_mesh_points(polygon_name, polygon_points);
    get_mesh_points(target_name, target_points);
    int vtx_length = target_points.length();
    MPointArray points(vtx_length);
    tbb::parallel_for(0, vtx_length, [&](int vtx_id) {
        MVector vector = target_points[vtx_id] - polygon_points[vtx_id];
        points.set(MPoint(vector), vtx_id);
    });
    set_bs_points(bs_name, index, points);
}

void get_plug_ids(MPlug& plug, MIntArray& ids) {
    MFnComponentListData fn_components(plug.asMObject());
    int component_length = fn_components.length();
    for (int component_id = 0; component_id < component_length; component_id++) {
        MFnSingleIndexedComponent fn_ids(fn_components[component_id]);
        MIntArray append_ids;
        fn_ids.getElements(append_ids);
        int ids_length = append_ids.length();
        for (int i = 0; i < ids_length; i++) {
            ids.append(append_ids[i]);
        }
    }
}


void get_plug_points(MPlug& plug, MPointArray& points) {
    MFnPointArrayData fn_points(plug.asMObject());
    points.copy(fn_points.array());
}


void get_bs_id_points(MString bs_name, int index, MIntArray& ids, MPointArray& points) {
    MPlug ipt, ict;
    std::tie(ipt, ict) = get_ipt_ict(bs_name, index);
    get_plug_points(ipt, points);
    get_plug_ids(ict, ids);
}

void get_mirror_id_point_map(MString bs_name, int index, std::map<int, MVector>& id_point_map) {
    MIntArray ids;
    MPointArray points;
    get_bs_id_points(bs_name, index, ids, points);
    int length = ids.length();
    int length2 = points.length();
    for (int i = 0; i < length; i++) {
        id_point_map[ids[i]] = MVector(-points[i].x, points[i].y, points[i].z);

    }
}

double dot(double* list1, double* list2, int length) {
    double result = 0;
    for (int i = 0; i < length; i++) {
        result += list1[i] * list2[i];
    }
    return result;
}

double* matrix_dot_list(double** matrix, double* list2, int matrix_length, int list_length) {
    double* result = new double[matrix_length];
    for (int i = 0; i < matrix_length; i++) {
        result[i] = dot(matrix[i], list2, list_length);
    }
    return result;
}

double* sub_list(double* list1, double* list2, int length) {
    double* result = new double[length];
    for (int i = 0; i < length; i++) {
        result[i] = list1[i] - list2[i];
    }
    return result;
}

double* liner_regression(double** data_x, double* data_y, int x_length, int y_length) {
    double* slopes = new double[x_length];
    for (int i = 0; i < x_length; i++) {
        slopes[i] = 1.0 / x_length;
    }
    for (int i = 0; i < 10; i++) {
        for (int slope_index = 0; slope_index < x_length; slope_index++) {
            double other_slope_sum = 1.0 - slopes[slope_index];
            double* edit_scale_list = new double[x_length];;
            if (other_slope_sum < 0.00001) {
                for (int j = 0; j < x_length; j++) {
                    edit_scale_list[j] = -1.0 / (x_length - 1.0);
                }
            }
            else {
                for (int j = 0; j < x_length; j++) {
                    edit_scale_list[j] = -1.0 * slopes[j] / other_slope_sum;
                }
            }
            edit_scale_list[slope_index] = 1.0;
            double* xs = matrix_dot_list(data_x, edit_scale_list, y_length, x_length);
            double* ys = sub_list(data_y, matrix_dot_list(data_x, slopes, y_length, x_length), y_length);
            double dot_xs = dot(xs, xs, y_length);
            if (dot_xs < 0.00001) {
                continue;
            }
            double edit_weight = dot(xs, ys, y_length) / dot_xs;
            for (int j = 0; j < x_length; j++) {
                slopes[j] = slopes[j] + edit_weight * edit_scale_list[j];
                if (slopes[j] > 1) {
                    slopes[j] = 1;
                }
                if (slopes[j] < 0) {
                    slopes[j] = 0;
                }
            }
            double sum_slopes = 0;
            for (int j = 0; j < x_length; j++) {
                sum_slopes += slopes[j];
            }
            for (int j = 0; j < x_length; j++) {
                slopes[j] = slopes[j] / sum_slopes;
            }
            delete[] xs;
            delete[] ys;
            delete[] edit_scale_list;
        }
    }
    return slopes;
}

struct IW
{
    int i;
    double w;
};

void mirror_targets(MString bs_name, MString orig_name, MIntArray src_indexes, MIntArray dst_indexes) {
    MDagPath dag_path;
    str_to_dag_path(orig_name, dag_path);
    MFnMesh fn_mesh(dag_path);
    MPointArray points;
    fn_mesh.getPoints(points);
    int vtx_length = points.length();
    std::vector<std::vector<IW>> iw_data(vtx_length);
    for (int vtx_id = 0; vtx_id < vtx_length; vtx_id++) {
        //tbb::parallel_for(0, vtx_length, [&](int vtx_id) {

        MPoint mirror_point(-points[vtx_id].x, points[vtx_id].y, points[vtx_id].z);
        MPoint closest_point;
        int face_id = 0;
        fn_mesh.getClosestPoint(mirror_point, closest_point, MSpace::kTransform, &face_id);
        MIntArray face_vtx_ids;
        fn_mesh.getPolygonVertices(face_id, face_vtx_ids);
        int face_vtx_length = face_vtx_ids.length();
        double min_distance = 0.001;
        int closest_vtx_id = -1;
        for (int vtx_arr_id = 0; vtx_arr_id < face_vtx_length; vtx_arr_id++) {
            int face_vtx_id = face_vtx_ids[vtx_arr_id];
            double next_distance = points[face_vtx_id].distanceTo(mirror_point);
            if (next_distance < min_distance) {
                min_distance = next_distance;
                closest_vtx_id = face_vtx_id;
            }
        }
        if (closest_vtx_id == -1) {
            // printf("\r\n");
            double** data_x = new double* [3];
            data_x[0] = new double[face_vtx_length];
            data_x[1] = new double[face_vtx_length];
            data_x[2] = new double[face_vtx_length];
            for (int vtx_arr_id = 0; vtx_arr_id < face_vtx_length; vtx_arr_id++) {
                int face_vtx_id = face_vtx_ids[vtx_arr_id];
                data_x[0][vtx_arr_id] = points[face_vtx_id].x;
                data_x[1][vtx_arr_id] = points[face_vtx_id].y;
                data_x[2][vtx_arr_id] = points[face_vtx_id].z;
            }
            double data_y[3] = { mirror_point.x, mirror_point.y, mirror_point.z };
            double* ws = liner_regression(data_x, data_y, face_vtx_length, 3);
            for (int vtx_arr_id = 0; vtx_arr_id < face_vtx_length; vtx_arr_id++) {
                int face_vtx_id = face_vtx_ids[vtx_arr_id];
                // printf("%.6f; ", ws[vtx_arr_id]);
                IW iw = { face_vtx_id, ws[vtx_arr_id] };
                iw_data[vtx_id].push_back(iw);
            }

        }
        else {
            IW iw = { closest_vtx_id, 1.0 };
            iw_data[vtx_id].push_back(iw);
        }
    }

    int target_length = src_indexes.length();
    for (int target_id = 0; target_id < target_length; target_id++) {
        int src_target_i = src_indexes[target_id];
        int dst_target_i = dst_indexes[target_id];
        std::map<int, MVector> id_point_map;
        get_mirror_id_point_map(bs_name, src_target_i, id_point_map);
        MPointArray dst_points(vtx_length);
        tbb::parallel_for(0, vtx_length, [&](int vtx_id) {
            MPoint dst_point;
            for (IW iw : iw_data[vtx_id]) {
                if (id_point_map.count(iw.i)) {
                    dst_points[vtx_id] += iw.w * id_point_map[iw.i];
                }
            }
        });
        set_bs_points(bs_name, dst_target_i, dst_points);
    }
}


void edit_static_target(MString bs_name, int index, MString target_name, MString polygon_name) {
    init_target(bs_name, index);
    MPointArray polygon_points;
    get_mesh_points(polygon_name, polygon_points);
    MPointArray target_points;
    get_mesh_points(target_name, target_points);
    int vtx_length = target_points.length();
    MPointArray points(vtx_length);
    for (int vtx_id = 0; vtx_id < vtx_length; vtx_id++) {
        MVector vector = target_points[vtx_id] - polygon_points[vtx_id];
        MPoint point(vector);
        points.set(point, vtx_id);
    }
    set_bs_points(bs_name, index, points);
}

//  bs json export load

template<typename T>
void m_to_json(T& m_value, Json::Value& json_value) {
    json_value = m_value;
}


void m_to_json(MPoint& m_value, Json::Value& json_value) {
    json_value[0] = m_value.x;
    json_value[1] = m_value.y;
    json_value[2] = m_value.z;
}

void m_to_json(MString& m_value, Json::Value& json_value) {
    json_value = m_value.asChar();
}

template<typename T>
void m_to_json_arry(T& m_value, Json::Value& json_value, int length) {
    for (int i = 0; i < length; i++) {
        m_to_json(m_value[i], json_value[i]);
    }
}


void json_to_m(double& m_value, Json::Value& json_value) {
    m_value = json_value.asDouble();
}

void json_to_m(int& m_value, Json::Value& json_value) {
    m_value = json_value.asInt();
}

void json_to_m(MPoint& m_value, Json::Value& json_value) {
    m_value.x = json_value[0].asDouble();
    m_value.y = json_value[1].asDouble();
    m_value.z = json_value[2].asDouble();
}

template<typename T>
void json_to_m_arr(T& m_value, Json::Value& json_value) {
    int length = json_value.size();
    if (!json_value.isArray()) {
        return;
    }
    m_value.setLength(length);
    for (int i = 0; i < length; i++) {
        json_to_m(m_value[i], json_value[i]);
    }
}

#define JsonToMArray(T) void json_to_m(T& m_value, Json::Value& json_value) { json_to_m_arr(m_value, json_value);}
JsonToMArray(MDoubleArray)
JsonToMArray(MIntArray)
JsonToMArray(MPointArray)

void save_json(Json::Value& data, const char* path) {
    Json::StyledWriter writer;
    ofstream fp;
    fp.open(path);
    fp << writer.write(data);
    fp.close();
}

bool load_json(Json::Value& data, const char* path) {
    Json::Reader reader;
    ifstream fp(path, ios::binary);
    if (!fp.is_open()) {
        return false;
    }
    bool successful = reader.parse(fp, data);
    fp.close();
    return successful;
}

void get_polygon_points(MString polygon_name, MPointArray& points) {
    MDagPath dag_path;
    str_to_dag_path(polygon_name, dag_path);
    MFnMesh fn_mesh(dag_path);
    fn_mesh.getPoints(points);
}




MPlug find_plug(MString node_name, MString attr_name) {
    MObject depend_node;
    str_to_depend_node(node_name, depend_node);
    MFnDependencyNode fn_depend_node(depend_node);
    return fn_depend_node.findPlug(attr_name, false);
}

bool has_name(vector<MString>& names, MString name) {
    return find(names.begin(), names.end(), name) != names.end();
}


void get_bs_targets(MString polygon_name, vector<MString>& target_names, Json::Value& targets) {
    MString bs = find_history(polygon_name, "kBlendShape");
    if (bs.length() == 0) {
        return;
    }
    MPlug weight_plug = find_plug(bs, "weight");
    int target_length = weight_plug.numElements();
    int index = -1;
    for (int target_id = 0; target_id < target_length; target_id++) {
        MPlug plug = weight_plug.elementByPhysicalIndex(target_id);
        MString target_name = plug.partialName(false, false, false, true);
        if (!has_name(target_names, target_name)) {
            continue;
        }
        index += 1;
        MIntArray ids;
        MPointArray points;
        get_bs_id_points(bs, plug.logicalIndex(), ids, points);
        m_to_json(target_name, targets[index]["name"]);
        m_to_json_arry(ids, targets[index]["ids"], ids.length());
        m_to_json_arry(points, targets[index]["points"], points.length());
    }
}

void export_targets(MStringArray polygon_names, MStringArray& target_name_array, MString path) {
    Json::Value data;
    int target_length = target_name_array.length();
    vector<MString> target_name_vector;
    for (int i = 0; i < target_length; i++) {
        target_name_vector.push_back(target_name_array[i]);
    }
    int polygon_length = polygon_names.length();
    for (int i = 0; i < polygon_length; i++) {
        MString polygon_name = polygon_names[i];
        m_to_json(polygon_name, data[i]["name"]);
        get_bs_targets(polygon_name, target_name_vector,  data[i]["targets"]);
    }
    save_json(data, path.asChar());
}



void get_target_names(MString node_name, vector<MString>& target_names) {
    MPlug weight = find_plug(node_name, "weight");
    int target_length = weight.numElements();
    for (int target_id = 0; target_id < target_length; target_id++) {
        MPlug target_plug = weight.elementByPhysicalIndex(target_id);
        MString target_name = target_plug.partialName(false, false, false, true);
        target_names.push_back(target_name);
    }
}

void get_name_indexs(vector<MString>& src_names, vector<MString>& dst_names, MIntArray& indices) {
    for (auto name : dst_names) {
        auto iter = std::find(src_names.begin(), src_names.end(), name);
        if (iter == src_names.end()) {
            indices.append(-1);;
        }
        else {
            int index = (int)(iter - src_names.begin());
            indices.append(index);
        }
    }
}

int target_next_index(MPlug plug) {
    for (int i = 0; i < 9999; i++) {
        MPlug elem = plug.elementByLogicalIndex(i);
        if (elem.partialName(false, false, false, true) == elem.partialName(false, false, false, false)) {
            return i;
        }
    }
    return -1;
}


void add_target(MString bs, MString name) {
    MObject bs_obj;
    str_to_depend_node(bs, bs_obj);
    MFnDependencyNode fn_bs_node(bs_obj);
    MPlug weight_plug = find_plug(bs, "weight");
    if (fn_bs_node.hasAttribute(name)) {
        return;
    }
    int index = target_next_index(weight_plug);
    MPlug plug = weight_plug.elementByLogicalIndex(index);
    plug.setFloat(0.0);
    MGlobal::executeCommand("aliasAttr " + name + " " + plug.name());
}

void load_target(MString polygon_name, Json::Value& data) {
    if (!data["targets"].isArray()) {
        return;
    }
    int target_length = data["targets"].size();
    if (target_length == 0) {
        return;
    }
    if (polygon_name.length() == 0) {
        return;
    }
    MString bs = find_history(polygon_name, "kBlendShape");
    if (bs.length() == 0) {
        MGlobal::executeCommand("blendShape -automatic " + polygon_name);
    }
    bs = find_history(polygon_name, "kBlendShape");
    vector<MString> json_target_names;
    vector<MString> bs_target_names;
    get_target_names(bs, bs_target_names);
    for (int target_id = 0; target_id < target_length; target_id++) {
        MString target_name = data["targets"][target_id]["name"].asCString();
        if (!has_name(bs_target_names, target_name)) {
            add_target(bs, target_name);
        }
        json_target_names.push_back(target_name);
    }
    bs_target_names.clear();
    get_target_names(bs, bs_target_names);
    MIntArray target_ids;
    get_name_indexs(bs_target_names, json_target_names, target_ids);
    MPlug weight_plug = find_plug(bs, "weight");
    for (int json_target_id = 0; json_target_id < target_length; json_target_id++) {
        int bs_target_id = target_ids[json_target_id];
        MIntArray ids;
        MPointArray points;
        json_to_m(ids, data["targets"][json_target_id]["ids"]);
        json_to_m(points, data["targets"][json_target_id]["points"]);
        set_bs_id_points(bs, bs_target_id, ids, points);
    }
}


void load_targets(MStringArray polygon_names, MString path) {
    Json::Value data;
    if (!load_json(data, path.asChar())) {
        return;
    }
    int length = polygon_names.length();
    for (int i = 0; i < length; i++) {
        load_target(polygon_names[i], data[i]);
    }
}



void get_bs_id_point_map(MString bs_name, int target_index, std::map<int, MPoint>& id_point_map) {
    id_point_map.clear();
    MIntArray ids;
    MPointArray points;
    get_bs_id_points(bs_name, target_index, ids, points);
    int length = ids.length();
    for (int i = 0; i < length; i++) {
        id_point_map[i] = points[i];
    }
}


void set_bs_id_point_map(MString bs_name, int target_index, std::map<int, MPoint>& id_point_map) {
    MIntArray ids;
    MPointArray points;
    for (auto id_point : id_point_map) {
        ids.append(id_point.first);
        points.append(id_point.second);
    }
    set_bs_id_points(bs_name, target_index, ids, points);
}

int get_vtx_count_by_bs(MString bs_name) {
    MStringArray polygon_names;
    MGlobal::executeCommand("blendShape -q -g " + bs_name, polygon_names);
    MDagPath dag_path;
    str_to_dag_path(polygon_names[0], dag_path);
    MFnMesh fn_mesh(dag_path);
    int count = fn_mesh.numVertices();
    return count;
}

void get_bs_points(MString bs_name, int target_index, MPointArray& all_points) {
    int count = get_vtx_count_by_bs(bs_name);
    std::cout << "count:" << count << "\r\n";
    MIntArray ids;
    MPointArray points;
    get_bs_id_points(bs_name, target_index, ids, points);
    all_points.clear();
    for (int i = 0; i < count; i++) {
        all_points.append(MPoint(0, 0, 0));
    }
    count = ids.length();
    for (int i = 0; i < count; i++) {
        all_points[ids[i]] = points[i];
    }

}


std::vector<MPointArray> _CACHE_POINTS;


void cache_target_points(MString bs_name, MIntArray target_indexes) {
    _CACHE_POINTS.clear();
    int target_length = target_indexes.length();
    _CACHE_POINTS.resize(target_length);
    for (int target_id = 0; target_id < target_length; target_id++) {
        get_bs_points(bs_name, target_indexes[target_id], _CACHE_POINTS[target_id]);
    }
}

void load_cache_target_points(MString bs_name, MIntArray target_indexes, MIntArray vtx_ids) {
    int target_length = target_indexes.length();
    if (target_length != _CACHE_POINTS.size()) {
        return;
    }
    for (int target_id = 0; target_id < target_length; target_id++) {
        int target_index = target_indexes[target_id];
        MPointArray all_points;
        get_bs_points(bs_name, target_index, all_points);
        int count = vtx_ids.length();
        for (int i = 0; i < count; i++) {
            all_points[vtx_ids[i]] = _CACHE_POINTS[target_id][vtx_ids[i]];
        }
        set_bs_points(bs_name, target_index, all_points);
    }
}

void invert_target_normal(MString polygon_name, MString orig_name, MString repair_polygon, MString target_polygon_name) {
    save_invert_shape_matrix(polygon_name, orig_name);

    MDagPath src_dag_path;
    str_to_dag_path(repair_polygon, src_dag_path);
    MFnMesh src_fn_mesh(src_dag_path);

    MDagPath dst_dag_path;
    str_to_dag_path(target_polygon_name, dst_dag_path);
    MFnMesh dst_fn_mesh(dst_dag_path);

    int count = src_fn_mesh.numVertices();
    for (int i = 0; i < count; i++) {
        MVector normal;
        
        src_fn_mesh.getVertexNormal(i, false, normal);
        normal *= invert_shape_matrix_cache[i];
        dst_fn_mesh.setVertexNormal(normal, i);
    }
}

FunCToPy5(edit_target, MString, int, MString, MString, MString)
FunCToPy4(cache_target, MString, int, MString, MString)
FunCToPy3(set_target, MString, int, MString)
FunCToPy2(init_target, MString, int)
FunCToPy4(mirror_targets, MString, MString, MIntArray, MIntArray)
FunCToPy4(edit_static_target, MString, int, MString, MString)
FunCToPy3(export_targets, MStringArray, MStringArray, MString)
FunCToPy2(load_targets, MStringArray, MString)
FunCToPy2(cache_target_points, MString, MIntArray)
FunCToPy3(load_cache_target_points, MString, MIntArray, MIntArray)
FunCToPy4(invert_target_normal, MString, MString, MString, MString)

PyDefList( 
    PyDef(init_target),
    PyDef(edit_target), 
    PyDef(cache_target), 
    PyDef(set_target),
    PyDef(edit_static_target),
    PyDef(mirror_targets),
    PyDef(load_targets),
    PyDef(export_targets),
    PyDef(cache_target_points),
    PyDef(load_cache_target_points),
    PyDef(invert_target_normal)
)

PyMod(bs_api)