import obspython as S
import os
import threading
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# stop = threading.Event()
update = threading.Event()


class ResizeFileHandler(FileSystemEventHandler):
    global update
    def on_modified(self, event):
        if event.src_path == "/home/char/.resetti_state":
            print("meow! file was modified!")
            update.set()


# def listening_thread():
#     global stop
#     print("resizing script listening")

#     event_handler = ResizeFileHandler()
#     observer = Observer()
#     observer.schedule(event_handler, path="/path/to", recursive=False)
#     observer.start()

    # nm = 0

    # while stop.is_set() is False:
        # when /home/char/.resetti_state changes, run begin_resize(contents of the file)
        # current_mtime = os.path.getmtime("/home/char/.resetti_state")
        # if current_mtime != nm:
            # nm = current_mtime
    #     time.sleep(1/120)
    # observer.stop()
    # observer.join()


def script_load(settings):
    global prevw, prevh, visualw, visualh, gamew, gameh, anim_time, animating
    global observer
    prevw = 1920
    prevh = 1080
    visualw = 1920
    visualh = 1080
    gamew = 1920
    gameh = 1080
    animating = False
    anim_time = 2.0

    fixInstance()
    event_handler = ResizeFileHandler()
    observer = Observer()
    observer.schedule(event_handler, path="/home/char/.resetti_state", recursive=False)
    observer.start()

    # thread = threading.Thread(target=listening_thread, daemon=True)
    # thread.start()


def script_unload():
    # global stop
    # stop.set()
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
        neww = 1920
        newh = 1080
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
    instance_scene = S.obs_get_scene_by_name("Scene")
    sceneitem = S.obs_scene_find_source(instance_scene, "Screenshot")
    source = S.obs_sceneitem_get_source(sceneitem)
    filter = S.obs_source_get_filter_by_name(source, "Freeze")
    S.obs_source_set_enabled(filter, frozen)
    S.obs_source_release(filter)
    # S.obs_source_release(source)
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
            with open("/home/char/.resetti_state", "r") as f:
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
    cropx = (1920 - gamew) // 2

    if gameh <= 1080:
        bbh = visualh
        cropy = (1080 - gameh) // 2
    else:
        bbh = int(visualh * (1080 / gameh))
        cropy = 0
    resizeSource("Minecraft", bbw, bbh, cropx, cropx, cropy, cropy)

    ssbbw = visualw
    sscropx = (1920 - ssw) // 2
    if ssh <= 1080:
        ssbbh = visualh
        sscropy = (1080 - ssh) // 2
    else:
        ssbbh = int(visualh * (1080 / ssh))
        sscropy = 0
    resizeSource("Screenshot", ssbbw, ssbbh, sscropx, sscropx, sscropy, sscropy)
        

def script_description():
    return "<h2>Resize Animation</h2>"


def fixInstance():
    resizeSource("Minecraft", 1920, 1080, 0, 0, 0, 0)
    resizeSource("Screenshot", 1920, 1080, 0, 0, 0, 0)


def resizeSource(source, bbw, bbh, cropl, cropr, cropt, cropb):
    instance_scene = S.obs_get_scene_by_name("Scene")
    source = S.obs_scene_find_source(instance_scene, source)
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

