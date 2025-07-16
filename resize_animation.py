# resize animation script for obs with waywall
# this script assumes you are playing minecraft on the same resolution as your OBS canvas
# and you need to set up your obs scene in a particular way:
# - make sure the OBS scene with your game matches OBS_SCENE
# - make sure your waywall capture matches WAYWALL_SOURCE
# - edit the transform of your waywall capture as follows:
#   - set Positional Alignment to "Center"
#   - set the position to the center of the screen (e.g. 960, 540 for 1920x1080)
#   - set Bounding Box Type to "Scale to height of bounds"
#   - set Alignment in Bounding Box to "Center"
#   - check "Crop to Bounding Box"
# and you also need to configure your waywall to output the game resolution at RESOLUTION_FILE
# here's my waywall config (note: this adds 17ms of latency to your resizing. 
# you can remove the waywall.sleep but having the delay will make the animation smoother):

# local toggle_res = function(w, h, s)  -- use this in the same way you would use helpers.toggle_res
#     local actual = helpers.toggle_res(w, h, s)
#     return function()
#         local active_width, active_height = waywall.active_res()
#         if active_width == w and active_height == h then
#     	    os.execute('echo "' .. 0 .. 'x' .. 0 .. '" > ~/.resetti_state')
# 	    else 
#     	    os.execute('echo "' .. w .. 'x' .. h .. '" > ~/.resetti_state')
# 	    end
#         waywall.sleep(17)
#         return actual()
#     end
# end

# lastly you can make your resizing smoother by installing the obs-freeze-filter plugin 
# (you can install my fork which fixes a gamma bug)
# and then create a copy of your waywall capture (use Paste (Duplicate)) called Screenshot right below waywall.
# then add a Freeze filter called Freeze to the Screenshot source. 
# you can verify the freeze is working by hiding and unhiding the filter. once you confirm it
# works, set the filter to disabled.

# todo unhardcode scene and source and resolution, make obs-freeze optional

import obspython as S
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

OBS_SCENE = "Scene"
WAYWALL_SOURCE = "Minecraft"
RESOLUTION_FILE = "/home/char/.resetti_state"
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080

update = threading.Event()

class ResizeFileHandler(FileSystemEventHandler):
    global update
    def on_modified(self, event):
        if event.src_path == RESOLUTION_FILE:
            print("meow! file was modified!")
            update.set()


def script_load(settings):
    global prevw, prevh, visualw, visualh, gamew, gameh, anim_time, animating
    global observer
    prevw = SCREEN_WIDTH
    prevh = SCREEN_HEIGHT
    visualw = SCREEN_WIDTH
    visualh = SCREEN_HEIGHT
    gamew = SCREEN_WIDTH
    gameh = SCREEN_HEIGHT
    animating = False
    anim_time = 2.0

    fixInstance()
    event_handler = ResizeFileHandler()
    observer = Observer()
    observer.schedule(event_handler, path=RESOLUTION_FILE, recursive=False)
    observer.start()


def script_unload():
    observer.stop()
    observer.join()


def begin_resize(size):
    global prevw, prevh, visualw, visualh, gamew, gameh, ssw, ssh, anim_time, animating, delay
    try:
        neww, newh = size.split("x")
        neww = int(neww)
        newh = int(newh)
    except Exception as e:
        print(f"Error parsing size: {e}")
        return
    if neww == 0 and newh == 0:
        neww = SCREEN_WIDTH
        newh = SCREEN_HEIGHT
    print("Resizing to:", neww, "x", newh)
    prevw = visualw
    prevh = visualh
    ssw = gamew
    ssh = gameh
    gamew = neww
    gameh = newh
    anim_time = 0.0
    delay = 2
    animating = True
    freeze_screenshot(gamew/gameh < visualw/visualh) # freeze if it shrinks horizontally


def freeze_screenshot(frozen=True):
    instance_scene = S.obs_get_scene_by_name(OBS_SCENE)
    sceneitem = S.obs_scene_find_source(instance_scene, "Screenshot")
    if not sceneitem:
        return
    source = S.obs_sceneitem_get_source(sceneitem)
    filter = S.obs_source_get_filter_by_name(source, "Freeze")
    S.obs_source_set_enabled(filter, frozen)
    S.obs_source_release(filter)
    S.obs_scene_release(instance_scene)


def get_visual_size(seconds):
    global anim_time, prevw, prevh, gamew, gameh, animating
    anim_time += seconds
    t = anim_time * 4.0
    if t > 1:
        animating = False
        freeze_screenshot(False)
        return gamew, gameh
    
    # cubic easing out
    t = t - 1
    t = t * t * t + 1
    visualw = int(prevw + (gamew - prevw) * t)
    visualh = int(prevh + (gameh - prevh) * t)
    return visualw, visualh


def script_tick(seconds):
    # we have a visual size and a physical size
    global gamew, gameh, ssw, ssh, visualw, visualh, anim_time, animating, delay
    if update.is_set():
        update.clear()
        try:
            with open(RESOLUTION_FILE, "r") as f:
                size = f.read().strip()
                print("Read resize state:", size)
                if size:
                    begin_resize(size)
        except Exception as e:
            print(f"Error reading resize state: {e}")
    if not animating:
        return
    if delay > 0:
        delay -= 1
        return

    visualw, visualh = get_visual_size(seconds)
    bbw = visualw
    cropx = (SCREEN_WIDTH - gamew) // 2

    if gameh <= SCREEN_HEIGHT:
        bbh = visualh
        cropy = (SCREEN_HEIGHT - gameh) // 2
    else:
        bbh = int(visualh * (SCREEN_HEIGHT / gameh))
        cropy = 0
    resizeSource(WAYWALL_SOURCE, bbw, bbh, cropx, cropx, cropy, cropy)

    ssbbw = visualw
    sscropx = (SCREEN_WIDTH - ssw) // 2
    if ssh <= SCREEN_HEIGHT:
        ssbbh = visualh
        sscropy = (SCREEN_HEIGHT - ssh) // 2
    else:
        ssbbh = int(visualh * (SCREEN_HEIGHT / ssh))
        sscropy = 0
    resizeSource("Screenshot", ssbbw, ssbbh, sscropx, sscropx, sscropy, sscropy)
        

def script_description():
    return "<h2>Resize Animation</h2>"


def fixInstance():
    resizeSource(WAYWALL_SOURCE, SCREEN_WIDTH, SCREEN_HEIGHT, 0, 0, 0, 0)
    resizeSource("Screenshot", SCREEN_WIDTH, SCREEN_HEIGHT, 0, 0, 0, 0)


def resizeSource(source, bbw, bbh, cropl, cropr, cropt, cropb):
    instance_scene = S.obs_get_scene_by_name(OBS_SCENE)
    source = S.obs_scene_find_source(instance_scene, source)
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

