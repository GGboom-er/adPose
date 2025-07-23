import sys
path = "D:/dev/tools/x3_P4/scripts/adPose2_FKSdk/adPose2/adpose_link"
if path not in sys.path:
    sys.path.insert(0, path)


import ad_pose_mb_bs_sdk
reload(ad_pose_mb_bs_sdk)
ad_pose_mb_bs_sdk.main()

