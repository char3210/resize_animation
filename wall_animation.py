import obspython as S
import os

OBS_SCENE = "Scene"
WAYWALL_SOURCE = "Minecraft"
WALL_STATE_FILE = "/home/char/.wall_state"
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080

LOCKED_LEFT_X = 0.85 * SCREEN_WIDTH
LOCKED_WIDTH = 0.1172 * SCREEN_WIDTH
LOCKED_TOP_Y = 60
LOCKED_HEIGHT = 73

# feel free to omdify this to your liking; input is 0 to 1, output is 0 to 1
def easing_func(t):
    # cubic easing out
    t = t - 1
    t = t * t * t + 1
    return t

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


def parse_state(statetext):
    global total_locked
    try:
        state, locked_insts1 = statetext.split(" ")
        locked_insts = int(locked_insts1)
        if state == "entering":
            freeze_screenshot("Screenshot", True)
            total_locked = locked_insts
            return "entering"
        elif state == "playing" and locked_insts > 0:
            freeze_screenshot("Screenshot", True)
            return "next"
        elif state == "playing" and locked_insts == 0:
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


def script_tick(seconds):
    # we have a visual size and a physical size
    global anim_type, anim_time, animating, delay, lastmtime, total_locked
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
    t = anim_time * 2.0
    if t > 1:
        animating = False
        freeze_screenshot("Screenshot", False)
        moveSource(WAYWALL_SOURCE, SCREEN_WIDTH/2, SCREEN_HEIGHT/2, SCREEN_WIDTH, SCREEN_HEIGHT)
        moveSource("Screenshot", SCREEN_WIDTH/2, SCREEN_HEIGHT/2, 2, 2)
        set_bounds_type(WAYWALL_SOURCE, S.OBS_BOUNDS_SCALE_TO_HEIGHT)
        set_bounds_type("Screenshot", S.OBS_BOUNDS_SCALE_TO_HEIGHT)
        return
    t = easing_func(t)


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
        x_scale_factor = SCREEN_WIDTH / LOCKED_WIDTH
        y_scale_factor = SCREEN_HEIGHT / LOCKED_HEIGHT
        x_start = SCREEN_WIDTH / 2
        x_end = (SCREEN_WIDTH / 2 - LOCKED_CENTER_X) * x_scale_factor + SCREEN_WIDTH / 2
        y_start = SCREEN_HEIGHT / 2
        y_end = (SCREEN_HEIGHT / 2 - LOCKED_CENTER_Y) * y_scale_factor + SCREEN_HEIGHT / 2
        x = int(x_start + (x_end - x_start) * t)
        y = int(y_start + (y_end - y_start) * t)
        bbwstart = SCREEN_WIDTH
        bbwend = SCREEN_WIDTH * x_scale_factor
        bbhstart = SCREEN_HEIGHT
        bbhend = SCREEN_HEIGHT * y_scale_factor
        bbw = int(bbwstart + (bbwend - bbwstart) * t)
        bbh = int(bbhstart + (bbhend - bbhstart) * t)
        moveSource("Screenshot", x, y, bbw, bbh)
    elif anim_type == "next":
        # waywall source
        x = int(SCREEN_WIDTH / 2)
        y = int(3 * SCREEN_HEIGHT / 2 - SCREEN_HEIGHT * t)
        bbw = SCREEN_WIDTH
        bbh = SCREEN_HEIGHT
        moveSource(WAYWALL_SOURCE, x, y, bbw, bbh)
        # screenshot source
        y = int(SCREEN_HEIGHT / 2 - SCREEN_HEIGHT * t)
        moveSource("Screenshot", x, y, bbw, bbh)
        pass
    elif anim_type == "leaving":
        # this is the same as entering, but in reverse, and for the waywall source
        x_scale_factor = SCREEN_WIDTH / LOCKED_WIDTH
        y_scale_factor = SCREEN_HEIGHT / LOCKED_HEIGHT
        x_start = (SCREEN_WIDTH / 2 - LOCKED_CENTER_X) * x_scale_factor + SCREEN_WIDTH / 2
        x_end = SCREEN_WIDTH / 2
        y_start = (SCREEN_HEIGHT / 2 - LOCKED_CENTER_Y) * y_scale_factor - SCREEN_HEIGHT * (total_locked - 1) + SCREEN_HEIGHT / 2
        y_end = SCREEN_HEIGHT / 2
        x = int(x_start + (x_end - x_start) * t)
        y = int(y_start + (y_end - y_start) * t)
        bbwstart = SCREEN_WIDTH * x_scale_factor
        bbwend = SCREEN_WIDTH
        bbhstart = SCREEN_HEIGHT * y_scale_factor
        bbhend = SCREEN_HEIGHT
        bbw = int(bbwstart + (bbwend - bbwstart) * t)
        bbh = int(bbhstart + (bbhend - bbhstart) * t)
        moveSource(WAYWALL_SOURCE, x, y, bbw, bbh)



def script_description():
    return "<h2>Wall Animation</h2>"


def fixInstance():
    moveSource(WAYWALL_SOURCE, SCREEN_WIDTH/2, SCREEN_HEIGHT/2, SCREEN_WIDTH, SCREEN_HEIGHT)
    moveSource("Screenshot", SCREEN_WIDTH/2, SCREEN_HEIGHT/2, 2, 2)


def moveSource(source, x, y, bbw, bbh, cropl=0, cropr=0, cropt=0, cropb=0):
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
    S.obs_sceneitem_set_crop(source, crop)
    S.obs_sceneitem_set_info(source, info)
    S.obs_scene_release(instance_scene)



