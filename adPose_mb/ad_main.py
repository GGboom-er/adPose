# import sys
# path = "T:/X3_RawData/X3_MayaTools/scripts/adPose2_FKSdk/adPose2/adPose_mb"
# if path not in sys.path:
#     sys.path.insert(0, path)

import mb_control_core, mb_hik_core, ad_core, ad_neck_untwist

reload(mb_control_core)
reload(mb_hik_core)
reload(ad_core)
reload(ad_neck_untwist)


def ad_main():
    mb_control_core.main()
    ad_core.main()
    mb_hik_core.main()
    ad_neck_untwist.main()
