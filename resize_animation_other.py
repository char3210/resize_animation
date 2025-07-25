# resize animation script for obs with jingle and resetti maybe
# you need to set up your obs scene in a particular way:
# - make sure the OBS scene with your game matches OBS_SCENE
# - make sure your minecraft capture matches MINECRAFT_SOURCE
# - edit the transform of your minecraft capture as follows:
#   - set Positional Alignment to "Center"
#   - set the position to the center of the screen (e.g. 960, 540 for 1920x1080)
#   - set Bounding Box Type to "Scale to height of bounds"
#   - set Alignment in Bounding Box to "Center"
#   - check "Crop to Bounding Box"

# lastly you can make your resizing smoother by installing the obs-freeze-filter plugin 
# and then create a copy of your minecraft capture (use Paste (Duplicate)) called Screenshot right below minecraft.
# then add a Freeze filter called Freeze to the Screenshot source. 
# you can verify the freeze is working by hiding and unhiding the filter. once you confirm it
# works, set the filter to disabled.


import obspython as S
import os

OBS_SCENE = "Scene"
MINECRAFT_SOURCE = "Minecraft"
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080


def script_load(settings):
    global prevw, prevh, visualw, visualh, gamew, gameh, anim_time, animating, lastsize
    global observer
    prevw = SCREEN_WIDTH
    prevh = SCREEN_HEIGHT
    visualw = SCREEN_WIDTH
    visualh = SCREEN_HEIGHT
    gamew = SCREEN_WIDTH
    gameh = SCREEN_HEIGHT
    animating = False
    anim_time = 2.0
    lastsize = SCREEN_WIDTH, SCREEN_HEIGHT

    fixInstance()

    print("Resize Animation loaded")


def script_unload():
    pass


def freeze_screenshot(sceneitemname, frozen=True):
    # instance_scene = S.obs_get_scene_by_name(OBS_SCENE)
    # sceneitem = S.obs_scene_find_source(instance_scene, sceneitemname)
    # # S.obs_sceneitem_set_visible(sceneitem, frozen)
    # if not sceneitem:
    #     return
    # source = S.obs_sceneitem_get_source(sceneitem)
    # filter = S.obs_source_get_filter_by_name(source, "Freeze")
    # # S.obs_source_set_enabled(filter, frozen)
    # if not filter:
    #     print(f"Filter 'Freeze' not found in source {sceneitemname}")
    #     S.obs_source_release(filter)
    #     S.obs_scene_release(instance_scene)
    #     return
    # filter_settings = S.obs_source_get_settings(filter)
    # print(S.obs_data_get_json_pretty(filter_settings))
    # print(f"Setting freeze filter to {'enabled' if frozen else 'disabled'} for source {sceneitemname}")
    # S.obs_data_set_bool(filter_settings, "frozen", frozen)
    # S.obs_source_update(filter, filter_settings)
    # S.obs_data_release(filter_settings)

    # S.obs_source_release(filter)
    # S.obs_scene_release(instance_scene)


def get_visual_size(seconds):
    global anim_time, prevw, prevh, gamew, gameh, animating
    anim_time += seconds
    t = anim_time * 4.0
    if t > 1:
        animating = False
        freeze_screenshot("Screenshot", False)
        return gamew, gameh
    
    # cubic easing out
    t = t - 1
    t = t * t * t + 1
    visualw = int(prevw + (gamew - prevw) * t)
    visualh = int(prevh + (gameh - prevh) * t)
    return visualw, visualh


def script_tick(seconds):
    # we have a visual size and a physical size
    global gamew, gameh, ssw, ssh, prevw, prevh, visualw, visualh, anim_time, delay, lastsize, animating
    size = get_source_size(MINECRAFT_SOURCE)
    if size[0] != 0 and size[1] != 0 and lastsize != size:
        lastsize = size
        print("Resizing to:", size[0], "x", size[1])
        prevw = visualw
        prevh = visualh
        ssw = gamew
        ssh = gameh
        gamew = size[0]
        gameh = size[1]
        anim_time = 0.0
        delay = 0
        animating = True
        freeze_screenshot("Screenshot", gamew/gameh < visualw/visualh) # freeze if it shrinks horizontally
    if not animating:
        return

    if delay > 0:
        delay -= 1
        return

    visualw, visualh = get_visual_size(seconds)
    resizeSource(MINECRAFT_SOURCE, visualw, visualh, 0, 0, 0, 0)

    if animating and gamew/gameh < visualw/visualh:
        resizeSource("Screenshot", visualw, visualh, 0, 0, 0, 0)
    else:
        pass
        # resizeSource("Screenshot", 2, 2, 0, 0, 0, 0) # effectively hide the screenshot source when not animating
        

def script_description():
    return "<h2>Resize Animation</h2>"


def fixInstance():
    resizeSource(MINECRAFT_SOURCE, SCREEN_WIDTH, SCREEN_HEIGHT, 0, 0, 0, 0)
    resizeSource("Screenshot", SCREEN_WIDTH, SCREEN_HEIGHT, 0, 0, 0, 0)


def get_source_size(sourcename):  # technically should be get_sceneitem_size(sceneitemname)
    instance_scene = S.obs_get_scene_by_name(OBS_SCENE)
    sceneitem = S.obs_scene_find_source(instance_scene, sourcename)
    if not sceneitem:
        print(f"Source {sourcename} not found in scene {OBS_SCENE}")
        return 0, 0
    source = S.obs_sceneitem_get_source(sceneitem)

    size = S.obs_source_get_width(source), S.obs_source_get_height(source)
    return size


def resizeSource(sourcename, bbw, bbh, cropl, cropr, cropt, cropb):
    instance_scene = S.obs_get_scene_by_name(OBS_SCENE)
    source = S.obs_scene_find_source(instance_scene, sourcename)
    if not source:
        return
    info = S.obs_transform_info()
    crop = S.obs_sceneitem_crop()
    S.obs_sceneitem_get_info(source, info)
    crop.left = cropl
    crop.right = cropr
    crop.top = cropt
    crop.bottom = cropb
    info.bounds.x = bbw
    info.bounds.y = bbh
    S.obs_sceneitem_set_crop(source, crop)
    S.obs_sceneitem_set_info(source, info)
    S.obs_scene_release(instance_scene)

