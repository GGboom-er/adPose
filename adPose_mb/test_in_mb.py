import sys
path = "D:/dev/tools/x3_P4/scripts/adPose2_FKSdk/adPose2/adPose_mb"
if path not in sys.path:
    sys.path.insert(0, path)


import ad_neck_untwist
reload(ad_neck_untwist)
ad_neck_untwist.main()


