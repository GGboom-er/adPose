
using UnityEngine;
namespace LushDrive {

    public class LushDrive : MonoBehaviour
    {

        public bool driveSwitch = true;
        public LushDriveData drive_data;
        Transform[] driven_joints;
        Transform[] limb_joints;
        Transform[] half_follow_joints;
        SkinnedMeshRenderer[] polygons;

        Transform[] FindTransfromList(string[] name_list)
        {
            Transform[] transfrom_list = new Transform[name_list.Length];
            for (int i = 0; i < name_list.Length; i++)
            {
                transfrom_list[i] = transform.Find(name_list[i]);
                if (transfrom_list[i] is null) {
                    Debug.LogError("can not find " + name_list[i]);
                }
            }
            return transfrom_list;
        }

        void Start()
        {
            if (drive_data is null) {
                return;
            }
            string[] driven_joint_names = new string[drive_data.bind_poses.Length];
            for (int i = 0; i < drive_data.bind_poses.Length; i++)
            {
                driven_joint_names[i] = drive_data.bind_poses[i].name;

            }
            string[] limb_joint_names = new string[drive_data.limb_drives.Length];
            for (int i = 0; i < drive_data.limb_drives.Length; i++)
            {
                limb_joint_names[i] = drive_data.limb_drives[i].name;

            }
            driven_joints = FindTransfromList(driven_joint_names);
            limb_joints = FindTransfromList(limb_joint_names);
            Transform[] polygon_trans = FindTransfromList(drive_data.polygons);
            polygons = new SkinnedMeshRenderer[polygon_trans.Length];
            for (int i = 0; i < polygon_trans.Length; i++) {
                polygons[i] = polygon_trans[i].GetComponent<SkinnedMeshRenderer>();
            }

            string[] half_follow_joint_names = new string[drive_data.half_follow_drives.Length*3];
            for (int i = 0; i < drive_data.half_follow_drives.Length; i++)
            {
                half_follow_joint_names[i * 3 + 0] = drive_data.half_follow_drives[i].driver_a;
                half_follow_joint_names[i * 3 + 1] = drive_data.half_follow_drives[i].driver_b;
                half_follow_joint_names[i * 3 + 2] = drive_data.half_follow_drives[i].driven;
            }
            half_follow_joints = FindTransfromList(half_follow_joint_names);
        }

        static float dot_two_vector(Vector3 v1, Vector3 v2)
        {
            return v1.x * v2.x + v1.y * v2.y + v1.z * v2.z;

        }
        static float angle_two_vector(Vector3 v1, Vector3 v2)
        {
            return Mathf.Acos(dot_two_vector(v1, v2) / Mathf.Pow(dot_two_vector(v1, v1) * dot_two_vector(v2, v2), 0.5f));
        }

        static float curve_evaluation(float time, TimeValue[] curve)
        {
            if (time < curve[0].time)
            {
                return curve[0].value;
            }
            if (time > curve[curve.Length - 1].time)
            {
                return curve[curve.Length - 1].value;
            }
            for (int i = 1; i < curve.Length; i++)
            {
                if ((curve[i - 1].time <= time) && (time <= curve[i].time))
                {
                    float w = (time - curve[i - 1].time) / (curve[i].time - curve[i - 1].time);
                    return curve[i - 1].value + (curve[i].value - curve[i - 1].value) * w;
                }
            }
            return 0;
        }

        void LateUpdate()
        {
            if (drive_data is null)
            {
                return;
            }
            for (int i = 0; i < drive_data.driven_poses.Length; i++)
            {
                foreach (Target target in drive_data.driven_poses[i].targets)
                {
                    polygons[target.mesh_id].SetBlendShapeWeight(target.target_id, 0);
                }
            }
            for (int i = 0; i < driven_joints.Length; i++)
            {
                driven_joints[i].localPosition = drive_data.bind_poses[i].position;
                Vector4 rotation = drive_data.bind_poses[i].rotation;
                driven_joints[i].localRotation = new Quaternion(rotation.x, rotation.y, rotation.z, rotation.w);
            }
            for (int i = 0; i < drive_data.half_follow_drives.Length; i++)
            {
                half_follow_joints[i * 3 + 2].localRotation = drive_data.half_follow_drives[i].rotation;
            }

            if (!driveSwitch)
            {
                return;
            }
            // half follow drive
            for (int i = 0; i < drive_data.half_follow_drives.Length; i++) {
                Quaternion rotate_a = half_follow_joints[i * 3 + 0].rotation * drive_data.half_follow_drives[i].offset_a;
                Quaternion rotate_b = half_follow_joints[i * 3 + 1].rotation * drive_data.half_follow_drives[i].offset_b;
                half_follow_joints[i * 3 + 2].rotation = Quaternion.Lerp(rotate_a, rotate_b, 0.5f);
            }
            // pose additive drive
            float[] pose_weights = new float[drive_data.driven_poses.Length];
            for (int i = 0; i < pose_weights.Length; i++)
            {
                pose_weights[i] = 0;
            }

            for (int i = 0; i < drive_data.limb_drives.Length; i++)
            {
                Quaternion anim_rotate = limb_joints[i].localRotation;
                Quaternion bind_rotation = drive_data.limb_drives[i].rotation;
                Quaternion relative_rotate = Quaternion.Inverse(bind_rotation) * anim_rotate;

                if (drive_data.limb_drives[i].angle_directions.Length > 0)
                {
                    // angle direction drive
                    Vector3 base_x = new Vector3(1, 0, 0);
                    Vector3 rotate_x = relative_rotate * base_x;
                    float angle = angle_two_vector(base_x, rotate_x) / Mathf.PI * 180;
                    Vector3 base_y = new Vector3(0, -1, 0);
                    Vector3 rotate_y = new Vector3(0, rotate_x.y, rotate_x.z);
                    rotate_y.Normalize();
                    float direction = angle_two_vector(base_y, rotate_y) / Mathf.PI * 180;
                    if (direction is float.NaN)
                    {
                        direction = 0;
                    }
                    if (rotate_y.z > 0)
                    {
                        direction = 360 - direction;

                    }
                    foreach (AngleDirectionDrive ad_drive in drive_data.limb_drives[i].angle_directions)
                    {
                        float angle_value = curve_evaluation(angle, ad_drive.angle_curve);
                        float driection_value = curve_evaluation(direction, ad_drive.direction_curve);
                        pose_weights[ad_drive.pose_id] = angle_value * driection_value;
                    }
                }
                if (drive_data.limb_drives[i].twists.Length > 0)
                {
                    // twist drive
                    Vector4 twist_axis = new Vector4(1, 0, 0, 0);
                    Vector4 projection = twist_axis * Vector4.Dot(twist_axis, new Vector4(relative_rotate.x, relative_rotate.y, relative_rotate.z, 0));
                    Vector4 twist = new Vector4(projection.x, projection.y, projection.z, relative_rotate.w);
                    if (Vector4.Dot(twist, twist) < 0.000001)
                    {
                        twist = new Vector4(0, 0, 0, 1);
                    }
                    else
                    {
                        twist.Normalize();
                    }
                    float twist_angle = Mathf.Atan2(twist[0], twist[3]) / Mathf.PI * 360;
                    foreach (TwistDrive twist_drive in drive_data.limb_drives[i].twists) {
                        float twist_value = curve_evaluation(twist_angle, twist_drive.twist_curve);
                        pose_weights[twist_drive.pose_id] = twist_value;
                    }
                }
            }
            // comb drive
            foreach (CombineDrive comb_drive in drive_data.combine_drives)
            {
                // A, B 组合修型 C
                // C = min(A, B)
                // A = A - C
                // B = A - C
                float min_weight = 1;
                foreach (int driver_pose_id in comb_drive.driver_poses)
                {
                    if (min_weight > pose_weights[driver_pose_id])
                    {
                        min_weight = pose_weights[driver_pose_id];
                    }
                }
                foreach (int driver_pose_id in comb_drive.driver_poses)
                {
                    pose_weights[driver_pose_id] -= min_weight;
                }
                pose_weights[comb_drive.pose_id] = min_weight;
            }
            // inbetween drive
            foreach (InbetweenDrive ib_drive in drive_data.inbetween_drives) {
                float driver_value = pose_weights[ib_drive.driver_pose];
                float driven_value = curve_evaluation(driver_value, ib_drive.inbetween_curve);
                pose_weights[ib_drive.pose_id] = driven_value;
            }
            // output weights
            int ii = -1;
            foreach (var pose in drive_data.driven_poses) {
                ii += 1;
                if (pose.name.Contains("Wrist")) {
                    continue;
                }
                if (pose.name.Contains("twist"))
                {
                    continue;
                }
                Debug.LogFormat("{0}:{1}", pose.name, pose_weights[ii]);
     
            }
            
            // set blend shape and joint transfrom
            BaseTransfrom[] joint_transfroms = new BaseTransfrom[driven_joints.Length];
            for (int i = 0; i < driven_joints.Length; i++) {
                joint_transfroms[i] = drive_data.bind_poses[i];
            }
            for (int i = 0; i < pose_weights.Length; i++){
                if (pose_weights[i] < 0.001)
                {
                    continue;
                }
                foreach (Target target in drive_data.driven_poses[i].targets) {
                    float bs_weight = polygons[target.mesh_id].GetBlendShapeWeight(target.target_id);
                    bs_weight += pose_weights[i] * target.value * 100;
                    polygons[target.mesh_id].SetBlendShapeWeight(target.target_id, bs_weight);
                }
                foreach (Additive additive in drive_data.driven_poses[i].additives) {
                    joint_transfroms[additive.joint_id] += additive*pose_weights[i];
                }
            }

            for (int i = 0; i < driven_joints.Length; i++)
            {
                driven_joints[i].localPosition = joint_transfroms[i].position;
                Vector4 rotation = joint_transfroms[i].rotation.normalized;
                driven_joints[i].localRotation = new Quaternion(rotation.x, rotation.y, rotation.z, rotation.w);
            }
        }
    }

}

