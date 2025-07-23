# coding:utf-8
from ad_base import *
from pyfbsdk import *


def new_charactor(skeleton):
    name = "_Character"
    character = FBCharacter(skeleton + name)
    return character


def character_slots_link(pCharacter, slot, mbJoint):
    name = "_Character"
    character = find_by_name(pCharacter + name, cls="Characters")
    character.PropertyList.Find(slot + "Link").append(find_by_name(mbJoint))


def main():
    # clean character and control rig
    ldelete = find_by_name("MB_Control_Character", cls="Characters")
    if ldelete is not None:
        ldelete.FBDelete()

    ldelete = find_by_name("MB_Control_ControlRig", cls="ControlSets")
    if ldelete is not None:
        ldelete.FBDelete()

    # Rig Primary
    character = new_charactor("MB_Control")
    lslotList = ["Reference", "Hips", "Spine", "Head", "LeftShoulder", "RightShoulder", "Neck", "Spine1", "Spine2",
                 "Spine3", "Neck1", "LeftToeBase", "RightToeBase", "LeftFootIndex1", "RightFootIndex1",
                 "LeftHandThumb1", "LeftHandThumb2", "LeftHandThumb3", "LeftHandThumb4",
                 "RightHandThumb1", "RightHandThumb2", "RightHandThumb3", "RightHandThumb4",
                 "LeftHandIndex1", "LeftHandIndex2", "LeftHandIndex3", "LeftHandIndex4",
                 "RightHandIndex1", "RightHandIndex2", "RightHandIndex3", "RightHandIndex4",
                 "LeftHandMiddle1", "LeftHandMiddle2", "LeftHandMiddle3", "LeftHandMiddle4",
                 "RightHandMiddle1", "RightHandMiddle2", "RightHandMiddle3", "RightHandMiddle4",
                 "LeftHandRing1", "LeftHandRing2", "LeftHandRing3", "LeftHandRing4",
                 "RightHandRing1", "RightHandRing2", "RightHandRing3", "RightHandRing4",
                 "LeftHandPinky1", "LeftHandPinky2", "LeftHandPinky3", "LeftHandPinky4",
                 "RightHandPinky1", "RightHandPinky2", "RightHandPinky3", "RightHandPinky4",
                 "LeftInHandIndex", "LeftInHandMiddle", "LeftInHandRing", "LeftInHandPinky",
                 "RightInHandIndex", "RightInHandMiddle", "RightInHandRing", "RightInHandPinky"]
    ljointList = ["Roots", "Root_M", "Spine1_M", "Head_M", "Scapula_L", "Scapula_R", "Neck_M", "Spine2_M", "Spine3_M",
                  "Chest_M", "NeckPart1_M", "Toes_L", "Toes_R", "ToesEnd_L", "ToesEnd_R",
                  "ThumbFinger1_L", "ThumbFinger2_L", "ThumbFinger3_L", "ThumbFinger4_L",
                  "ThumbFinger1_R", "ThumbFinger2_R", "ThumbFinger3_R", "ThumbFinger4_R",
                  "IndexFinger1_L", "IndexFinger2_L", "IndexFinger3_L", "IndexFinger4_L",
                  "IndexFinger1_R", "IndexFinger2_R", "IndexFinger3_R", "IndexFinger4_R",
                  "MiddleFinger1_L", "MiddleFinger2_L", "MiddleFinger3_L", "MiddleFinger4_L",
                  "MiddleFinger1_R", "MiddleFinger2_R", "MiddleFinger3_R", "MiddleFinger4_R",
                  "RingFinger1_L", "RingFinger2_L", "RingFinger3_L", "RingFinger4_L",
                  "RingFinger1_R", "RingFinger2_R", "RingFinger3_R", "RingFinger4_R",
                  "PinkyFinger1_L", "PinkyFinger2_L", "PinkyFinger3_L", "PinkyFinger4_L",
                  "PinkyFinger1_R", "PinkyFinger2_R", "PinkyFinger3_R", "PinkyFinger4_R",
                  "IndexFinger0_L", "MiddleFinger0_L", "RingFinger0_L", "PinkyFinger0_L",
                  "IndexFinger0_R", "MiddleFinger0_R", "RingFinger0_R", "PinkyFinger0_R"]
    for slot, joint in zip(lslotList, ljointList):
        character_slots_link("MB_Control", slot, joint)

    # Rig MB_Control
    pre_text = "MB_Control_"
    lslotList = ["LeftUpLeg", "LeftLeg", "LeftFoot",
                 "RightUpLeg", "RightLeg", "RightFoot",
                 "LeftArm", "LeftForeArm", "LeftHand",
                 "RightArm", "RightForeArm", "RightHand"]
    ljointList = ["Hip_L", "Knee_L", "Ankle_L",
                  "Hip_R", "Knee_R", "Ankle_R",
                  "Shoulder_L", "Elbow_L", "Wrist_L",
                  "Shoulder_R", "Elbow_R", "Wrist_R",
]
    mbJointList = []
    for joint in ljointList:
        mbJointList.append(pre_text + joint)

    for slot, joint in zip(lslotList, mbJointList):
        character_slots_link("MB_Control", slot, joint)

    character.Selected = True
    character.SetCharacterizeOn(True)
    character.CreateControlRig(True)
    character.PropertyList.Find("Active Source").Data = True

    contrig = find_by_name("Control Rig", cls="ControlSets")
    contrig.Name = "MB_Control_ControlRig"
    find_by_name("HIK 2016 Solver", cls="ConstraintSolvers").Name = "MB_Control_HIK_Solver"

    FBSystem().Scene.Evaluate()
    find_by_name("MB_Control_Character", cls="Characters").PropertyList.Find("Left Knee Roll").Data = 0
    find_by_name("MB_Control_Character", cls="Characters").PropertyList.Find("Right Knee Roll").Data = 0


    FBSystem().Scene.Evaluate()
    # for i in find_by_name("MB_Control_Character", cls="Characters").PropertyList:
    #     print i.Name
