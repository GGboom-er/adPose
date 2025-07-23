using System.Collections;
using System.Collections.Generic;
using UnityEngine;
namespace LushDrive
{
    public class BaseTransfrom {
        public Vector3 position;
        public Vector4 rotation;
        public static BaseTransfrom operator+(BaseTransfrom A, BaseTransfrom B) {
            BaseTransfrom result = new BaseTransfrom();
            result.position = A.position + B.position;
            result.rotation = A.rotation + B.rotation;
            return result;
        }
        public static BaseTransfrom operator *(BaseTransfrom A, float B)
        {
            BaseTransfrom result = new BaseTransfrom();
            result.position = A.position * B;
            result.rotation = A.rotation * B;
            return result;
        }
    }

    [System.Serializable]
    public class BindPose: BaseTransfrom
    {
        public string name;
    }
    [System.Serializable]
    public class Target {
        public int target_id;
        public int mesh_id;
        public float value;
    }
    [System.Serializable]
    public class Additive: BaseTransfrom
    {
        public int joint_id;
    }
    [System.Serializable]
    public class DrivenPose {
        public string name;
        public Target[] targets;
        public Additive[] additives;
    }
    [System.Serializable]
    public class TimeValue {
        public float time;
        public float value;
    }
    [System.Serializable]
    public class AngleDirectionDrive {
        public int pose_id;
        public TimeValue[] direction_curve;
        public TimeValue[] angle_curve;
    }
    [System.Serializable]
    public class TwistDrive {
        public int pose_id;
        public TimeValue[] twist_curve;
    }
    [System.Serializable]
    public class LimbDrive
    {
        public string name;
        public Quaternion rotation;
        public AngleDirectionDrive[] angle_directions;
        public TwistDrive[] twists;

    }
    [System.Serializable]
    public class CombineDrive
    {
        public int[] driver_poses;
        public int pose_id;
    }

    [System.Serializable]
    public class InbetweenDrive
    {
        public int pose_id;
        public int driver_pose;
        public TimeValue[] inbetween_curve;
    }
    [System.Serializable]
    public class HalfFollowDriver
    {
        public string driver_a;
        public string driver_b;
        public Quaternion offset_a;
        public Quaternion offset_b;
        public string driven;
        public Quaternion rotation;
    }
    [System.Serializable]
    public class LushDriveData : ScriptableObject
    {
        public string[] polygons;
        public BindPose[] bind_poses;
        public DrivenPose[] driven_poses;
        public LimbDrive[] limb_drives;
        public CombineDrive[] combine_drives;
        public InbetweenDrive[] inbetween_drives;
        public HalfFollowDriver[] half_follow_drives;
    }
}
