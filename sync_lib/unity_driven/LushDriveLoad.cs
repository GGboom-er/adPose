using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEditor;
using System.IO;

namespace LushDrive
{
    public class LushDriveEdit : Editor
    {
        static string get_selected_asset_path()
        {
            string[] guid_list = Selection.assetGUIDs;
            if (!(guid_list.Length == 1))
            {
                return "";
            }
            string guid = guid_list[0];
            string asset_path = AssetDatabase.GUIDToAssetPath(guid);
            return asset_path;
        }

        static string ReadText(string path) {
            string text="";
            if (!File.Exists(path)) {
                Debug.Log("path not exist");
                return text;
            }
            using (StreamReader sr = File.OpenText(path)) {
                text = sr.ReadToEnd();
                sr.Close();
            }
            return text;
        }

        [MenuItem("Lush/CreateJointDriveData")]
        static void LoadJointDriveData()
        {

            string json_path = get_selected_asset_path();
            string text = ReadText(json_path);
            if (text == "") {
                Debug.Log("text is null");
                return;
            }
            LushDriveData unity_data = ScriptableObject.CreateInstance<LushDriveData>();
            JsonUtility.FromJsonOverwrite(text, unity_data);
            Debug.Log("From Json Over Write");
            string asset_path = json_path.Substring(0, json_path.Length - 5) + "_LushDriveData.asset";
            AssetDatabase.CreateAsset(unity_data, asset_path);
        }

        [MenuItem("Lush/test")]
        static void test() {
            BindPose A = new BindPose();
            Additive C = new Additive();
            C.position = new Vector3(2, 2, 2);
            BaseTransfrom D = A + C;
            Debug.LogFormat("{0}，{1}， {2}", D.rotation.x, D.rotation.y, D.rotation.z);
        }
    }
}

