# the silliest seedqueue wall animations (waywall)
# this is intended for the lock some instances then play them reset style
# make sure you have the Freeze filter plugin
# make sure you setup WAYWALL_SOURCE and Screenshot the same as in resize_animation_waywall.py (even if you're not using resize animations)
# for this script you also need an additional waywall capture called Wall below Minecraft, Screenshot, and Background. Add a freeze filter named Freeze to Wall
# the locked instances should be cropped out of the Wall capture for best results.
# and then below the Wall capture should be an image capture of your wall background (.minecraft/resourcepacks/{wall pack}/assets/seedqueue/textures/gui/wall/background.png)
# now to configure this script, there is now a WALL_STATE_FILE that should have the behavior of this waywall config:

"""
locking = false
locked_insts = 0

local play_next = function()
    if waywall.state()["screen"] == "wall" then
        locking = false
        os.execute('echo "entering ' .. locked_insts .. '" > ~/.wall_state')
        waywall.sleep(17)
        waywall.press_key("Space")              -- ***your seedqueue Play Locked Instance key***
        return true
    end
    return false
end

local lock_inst = function()
    if waywall.state()["screen"] == "wall" then
        if not locking then
            locking = true
            locked_insts = 0
        end
        locked_insts = locked_insts + 1
    end
    return false
end

local reset = function()
    if locked_insts > 0 then
        locked_insts = locked_insts - 1
    end
    os.execute('echo "playing ' .. locked_insts .. '" > ~/.wall_state')
    waywall.sleep(17)
    waywall.press_key("F6")                     -- ***your ingame reset key***
    return true
end

-- and then bind these functions to your hotkeys in waywall config, e.g.:
config.actions = {
    ...
    ["Space"] = play_next,
    ["rmb"] = lock_inst,
    ["F6"] = reset,
}
"""

# the script is configured by default for the Madobrick Dummy Layout on 1080p. to modify this, refer to {wall pack}/assets/seedqueue/wall/custom_layout.json
# LOCKED_LEFT_X is the value of "locked" -> "x" * SCREEN_WIDTH, LOCKED_TOP_Y is "locked" -> "y" * SCREEN_HEIGHT.
# LOCKED_WIDTH is "locked" -> "width" * SCREEN_WIDTH / "columns" and LOCKED_HEIGHT is "locked" -> "height" * SCREEN_HEIGHT / "rows".

import obspython as S
import os
import random
import math

OBS_SCENE = "Scene"
WAYWALL_SOURCE = "Minecraft"
WALL_STATE_FILE = "/home/char/.wall_state"
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080

LOCKED_LEFT_X = 0.85 * SCREEN_WIDTH
LOCKED_WIDTH = 0.1172 * SCREEN_WIDTH
LOCKED_TOP_Y = 0.0555 * SCREEN_HEIGHT / 1
LOCKED_HEIGHT = 73   # 0.95 * SCREEN_HEIGHT / 14

# feel free to omdify this to your liking; input is 0 to 1, output is 0 to 1
def easing_func(t):
    # return (1 - 2 ** (-5 * t)) * (33/32)  # exponential ease out
    # return t
    return -t*t+2*t
    # return -1/2*math.cos(math.pi*t) + 1/2

LOCKED_CENTER_X = LOCKED_LEFT_X + LOCKED_WIDTH / 2
LOCKED_CENTER_Y = LOCKED_TOP_Y + LOCKED_HEIGHT / 2


def script_load(settings):
    global anim_type, anim_time, animating, delay, lastmtime, total_locked
    anim_type = ""
    anim_time = 2.0
    animating = False
    delay = 0
    lastmtime = 0
    total_locked = 0


def script_unload():
    pass


def hideSource(source, hidden=True):
    instance_scene = S.obs_get_scene_by_name(OBS_SCENE)
    sceneitem = S.obs_scene_find_source(instance_scene, source)
    if not sceneitem:
        return
    S.obs_sceneitem_set_visible(sceneitem, not hidden)
    S.obs_scene_release(instance_scene)


def parse_state(statetext):
    global total_locked
    try:
        state, locked_insts1 = statetext.split(" ")
        locked_insts = int(locked_insts1)
        if state == "entering":
            freeze_screenshot("Screenshot", True)
            freeze_screenshot("Wall", True)
            hideSource("Background", True)
            total_locked = locked_insts
            return "entering"
        elif state == "playing" and locked_insts > 0:
            freeze_screenshot("Screenshot", True)
            hideSource("Background", True)
            hideSource("Discard", True)
            return "next"
        elif state == "playing" and locked_insts == 0:
            freeze_screenshot("Screenshot", True)
            hideSource("Background", True)
            hideSource("Discard", True)
            return "leaving"
        else:
            print(f"idk what {statetext} means")
            return None
    except Exception as e:
        print(f"idk what {statetext} means 2")
        return None


def freeze_screenshot(scene, frozen=True):
    instance_scene = S.obs_get_scene_by_name(OBS_SCENE)
    sceneitem = S.obs_scene_find_source(instance_scene, scene)
    # S.obs_sceneitem_set_visible(sceneitem, frozen)
    if not sceneitem:
        return
    source = S.obs_sceneitem_get_source(sceneitem)
    filter = S.obs_source_get_filter_by_name(source, "Freeze")
    S.obs_source_set_enabled(filter, frozen)
    S.obs_source_release(filter)
    S.obs_scene_release(instance_scene)


def set_bounds_type(source, bounds_type):
    instance_scene = S.obs_get_scene_by_name(OBS_SCENE)
    sceneitem = S.obs_scene_find_source(instance_scene, source)
    if not sceneitem:
        return
    S.obs_sceneitem_set_bounds_type(sceneitem, bounds_type)
    S.obs_scene_release(instance_scene)

# silly projectile stuff
def projectile_3d_pos(t, xvel):
    # starting at (0, 0, -1) with -0.1 zvel
    zvel = -40
    x = xvel * t
    y = -20 * t * t + 50 * t
    z = -1 + zvel * t
    return (x, y, z)


def projectile_transform(t, xvel):
    x, y, z = projectile_3d_pos(t, xvel)
    # look a bit down
    # down_angle = 0.5
    # y, z = y * math.cos(down_angle) - z * math.sin(down_angle), y * math.sin(down_angle) + z * math.cos(down_angle)
    # project to 2D
    return x/z * SCREEN_WIDTH/2 + SCREEN_WIDTH/2, y/z * SCREEN_HEIGHT/2 + SCREEN_HEIGHT/2, z


def script_tick(seconds):
    # we have a visual size and a physical size
    global anim_type, anim_time, animating, delay, lastmtime, total_locked, xvel, rotspeed
    if os.path.getmtime(WALL_STATE_FILE) != lastmtime:
        lastmtime = os.path.getmtime(WALL_STATE_FILE)
        try:
            with open(WALL_STATE_FILE, "r") as f:
                state = f.read().strip()
                print("Read wall state:", state)
                anim_type = parse_state(state)
                if anim_type:
                    anim_time = 0.0
                    animating = True
                    delay = 1
                    xvel = random.uniform(-40, 40)
                    rotspeed = random.uniform(-500, 500)
                    set_bounds_type(WAYWALL_SOURCE, S.OBS_BOUNDS_STRETCH)
                    set_bounds_type("Screenshot", S.OBS_BOUNDS_STRETCH)
                    print(f"Starting {anim_type} animation")
        except Exception as e:
            print(f"Error reading resize state: {e}")
    if not animating:
        return
    if delay > 0:
        delay -= 1
        return

    anim_time += seconds
    rawt = anim_time / 0.5
    if rawt > 1:
        animating = False
        freeze_screenshot("Screenshot", False)
        if anim_type == "leaving":
            freeze_screenshot("Wall", False)
        moveSource(WAYWALL_SOURCE, SCREEN_WIDTH/2, SCREEN_HEIGHT/2, SCREEN_WIDTH, SCREEN_HEIGHT)
        moveSource("Screenshot", SCREEN_WIDTH/2, SCREEN_HEIGHT/2, 2, 2)
        set_bounds_type(WAYWALL_SOURCE, S.OBS_BOUNDS_SCALE_TO_HEIGHT)
        set_bounds_type("Screenshot", S.OBS_BOUNDS_SCALE_TO_HEIGHT)
        hideSource("Background", False)
        return
    t = easing_func(rawt)


    if anim_type == "entering":
        # waywall source
        x_start = LOCKED_CENTER_X
        x_end = SCREEN_WIDTH / 2
        y_start = LOCKED_CENTER_Y
        y_end = SCREEN_HEIGHT / 2
        x = int(x_start + (x_end - x_start) * t)
        y = int(y_start + (y_end - y_start) * t)
        bbwstart = LOCKED_WIDTH
        bbwend = SCREEN_WIDTH
        bbhstart = LOCKED_HEIGHT
        bbhend = SCREEN_HEIGHT
        bbw = int(bbwstart + (bbwend - bbwstart) * t)
        bbh = int(bbhstart + (bbhend - bbhstart) * t)
        # hide the source for the first 
        if anim_time < 0.2:
            moveSource(WAYWALL_SOURCE, -2, -2, 2, 2)
        else:
            moveSource(WAYWALL_SOURCE, x, y, bbw, bbh)

        # screenshot source (this will be a bit more complicated)
        y_start = LOCKED_TOP_Y + (LOCKED_HEIGHT * total_locked) / 2
        y_end = SCREEN_HEIGHT * total_locked / 2
        y = int(y_start + (y_end - y_start) * t)
        bbhstart = LOCKED_HEIGHT * total_locked
        bbhend = SCREEN_HEIGHT * total_locked
        bbh = int(bbhstart + (bbhend - bbhstart) * t)
        cropl = LOCKED_LEFT_X
        cropr = SCREEN_WIDTH - LOCKED_LEFT_X - LOCKED_WIDTH
        cropt = LOCKED_TOP_Y
        cropb = SCREEN_HEIGHT - LOCKED_TOP_Y - (LOCKED_HEIGHT * total_locked)
        moveSource("Screenshot", x, y, bbw, bbh, cropl, cropr, cropt, cropb)
    elif anim_type == "next":
        # waywall source
        x = SCREEN_WIDTH / 2
        y = 3 * SCREEN_HEIGHT / 2 - SCREEN_HEIGHT * t
        bbw = SCREEN_WIDTH
        bbh = SCREEN_HEIGHT
        moveSource(WAYWALL_SOURCE, x, y, bbw, bbh)
        # screenshot source (silly)
        x, y, z = projectile_transform(rawt, xvel)
        bbw = SCREEN_WIDTH / z
        bbh = SCREEN_HEIGHT / z
        # moveSource("Screenshot", x, y, bbw, bbh, rot=0)
        moveSource("Screenshot", x, y, bbw, bbh, rot=rawt * rotspeed)
        hideSource("Discard", False)
        moveSource("Discard", x, y, 250, 358)
    elif anim_type == "leaving":
        # waywall source
        moveSource(WAYWALL_SOURCE, -2, -2, 2, 2)
        # screenshot source (silly)
        x, y, z = projectile_transform(rawt, xvel)
        bbw = SCREEN_WIDTH / z
        bbh = SCREEN_HEIGHT / z
        moveSource("Screenshot", x, y, bbw, bbh, rot=rawt * rotspeed)
        hideSource("Discard", False)
        moveSource("Discard", x, y, 250, 358)


def script_description():
    return "<h2>Wall Animation</h2>"


def fixInstance():
    moveSource(WAYWALL_SOURCE, SCREEN_WIDTH/2, SCREEN_HEIGHT/2, SCREEN_WIDTH, SCREEN_HEIGHT)
    moveSource("Screenshot", SCREEN_WIDTH/2, SCREEN_HEIGHT/2, 2, 2)


def moveSource(source, x, y, bbw, bbh, cropl=0, cropr=0, cropt=0, cropb=0, rot=0):
    instance_scene = S.obs_get_scene_by_name(OBS_SCENE)
    source = S.obs_scene_find_source(instance_scene, source)
    if not source:
        return
    info = S.obs_transform_info()
    crop = S.obs_sceneitem_crop()
    S.obs_sceneitem_get_info(source, info)
    crop.left = int(cropl)
    crop.right = int(cropr)
    crop.top = int(cropt)
    crop.bottom = int(cropb)
    info.pos.x = int(x)
    info.pos.y = int(y)
    info.bounds.x = int(bbw)
    info.bounds.y = int(bbh)
    info.rot = float(rot)
    S.obs_sceneitem_set_crop(source, crop)
    S.obs_sceneitem_set_info(source, info)
    S.obs_scene_release(instance_scene)



