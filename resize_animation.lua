-- resize animation script for obs with jingle on windows
-- you need to set up your obs scene in a particular way:
-- - make sure the OBS scene with your game matches OBS_SCENE (you can modify the script)
-- - make sure your minecraft capture matches MINECRAFT_SOURCE
-- - edit the transform of your minecraft capture as follows:
--   - set Positional Alignment to "Center"
--   - set the position to the center of the screen (e.g. 960, 540 for 1920x1080)
--   - set Bounding Box Type to "Scale to height of bounds"
--   - set Alignment in Bounding Box to "Center"
--   - check "Crop to Bounding Box"
-- - add this script to OBS > Tools > Scripts
-- whenever you modify this script, make sure to press the reload scripts button in OBS

-- EXPERIMENTAL FEATURE: you can make your resizing smoother
-- this requires your game to be in the center of your display that you're playing on (such as on Julti)
-- and also uses display capture so there's a risk of leaking the screen your minecraft is on
-- (insert waywall propaganda here it doesnt have this issue)
-- to do this:
-- - install my modified version of obs-freeze-filter plugin https://github.com/char3210/obs-freeze-filter/releases/tag/v1
-- - create a display capture called Screenshot right below minecraft.
-- - edit the transform to the same as the minecraft capture (instructions above)
-- - add a Freeze filter called Freeze to the Screenshot source. 
-- you can verify the freeze is working by checking the "Frozen" checkbox in the filter settings.
-- and then it should just work (tm)
-- if when resizing normal -> thin your desktop is in the background, try increasing BufferSize in the Freeze filter settings
-- a larger value of BufferSize makes the frozen background more delayed and uses more GPU memory i think so set it high enough
-- to not leak your desktop but not too high

local obs = obslua

local OBS_SCENE = "Scene"
local MINECRAFT_SOURCE = "Minecraft"
local SCREEN_WIDTH = 1920
local SCREEN_HEIGHT = 1080

-- Global variables
local prevw, prevh, visualw, visualh, gamew, gameh
local anim_time, animating
local lastsize_w, lastsize_h
local delay, ssw, ssh

function script_load(settings)
    prevw = SCREEN_WIDTH
    prevh = SCREEN_HEIGHT
    visualw = SCREEN_WIDTH
    visualh = SCREEN_HEIGHT
    gamew = SCREEN_WIDTH
    gameh = SCREEN_HEIGHT
    animating = false
    anim_time = 2.0
    lastsize_w = SCREEN_WIDTH
    lastsize_h = SCREEN_HEIGHT
    delay = 0
    ssw = 0
    ssh = 0

    fixInstance()

    print("Resize Animation loaded")
end

function script_unload()
    -- Cleanup if needed
end

function freeze_screenshot(sceneitemname, frozen)
    
    local instance_scene = obs.obs_get_scene_by_name(OBS_SCENE)
    local sceneitem = obs.obs_scene_find_source(instance_scene, sceneitemname)
    if not sceneitem then
        obs.obs_scene_release(instance_scene)
        return
    end
    
    local source = obs.obs_sceneitem_get_source(sceneitem)
    local filter = obs.obs_source_get_filter_by_name(source, "Freeze")
    if not filter then
        print("Filter 'Freeze' not found in source " .. sceneitemname)
        obs.obs_scene_release(instance_scene)
        return
    end
    
    local filter_settings = obs.obs_source_get_settings(filter)
    print("Setting freeze filter to " .. (frozen and "enabled" or "disabled") .. " for source " .. sceneitemname)
    obs.obs_data_set_bool(filter_settings, "frozen", frozen)
    obs.obs_source_update(filter, filter_settings)
    obs.obs_data_release(filter_settings)
    obs.obs_source_release(filter)
    obs.obs_scene_release(instance_scene)
    
end

function get_visual_size(seconds)
    anim_time = anim_time + seconds
    local t = anim_time * 4.0
    if t > 1 then
        animating = false
        freeze_screenshot("Screenshot", false)
        return gamew, gameh
    end
    
    -- cubic easing out
    t = t - 1
    t = t * t * t + 1
    local new_visualw = math.floor(prevw + (gamew - prevw) * t)
    local new_visualh = math.floor(prevh + (gameh - prevh) * t)
    return new_visualw, new_visualh
end

function script_tick(seconds)
    -- we have a visual size and a physical size
    local size_w, size_h = get_source_size(MINECRAFT_SOURCE)
    if size_w ~= 0 and size_h ~= 0 and (lastsize_w ~= size_w or lastsize_h ~= size_h) then
        lastsize_w = size_w
        lastsize_h = size_h
        print("Resizing to: " .. size_w .. " x " .. size_h)
        prevw = visualw
        prevh = visualh
        ssw = gamew
        ssh = gameh
        gamew = size_w
        gameh = size_h
        anim_time = 0.0
        delay = 0
        animating = true
        freeze_screenshot("Screenshot", gamew/gameh < visualw/visualh) -- freeze if it shrinks horizontally
    end

    if not animating then
        return
    end

    if delay > 0 then
        delay = delay - 1
        return
    end

    visualw, visualh = get_visual_size(seconds)
    resizeSource(MINECRAFT_SOURCE, visualw, visualh, 0, 0, 0, 0)

    if animating and gamew/gameh < visualw/visualh then
        local ssbbw = visualw
        local sscropx = math.floor((SCREEN_WIDTH - ssw) / 2)
        local ssbbh, sscropy
        if ssh <= SCREEN_HEIGHT then
            ssbbh = visualh
            sscropy = math.floor((SCREEN_HEIGHT - ssh) / 2)
        else
            ssbbh = math.floor(visualh * (SCREEN_HEIGHT / ssh))
            sscropy = 0
        end

        resizeSource("Screenshot", ssbbw, ssbbh, sscropx, sscropx, sscropy, sscropy)
    else
        resizeSource("Screenshot", 2, 2, 0, 0, 0, 0) -- effectively hide the screenshot source when not animating
    end
end

function script_description()
    return "<h2>Resize Animation</h2>"
end

function fixInstance()
    resizeSource(MINECRAFT_SOURCE, SCREEN_WIDTH, SCREEN_HEIGHT, 0, 0, 0, 0)
    resizeSource("Screenshot", SCREEN_WIDTH, SCREEN_HEIGHT, 0, 0, 0, 0)
end

function get_source_size(sourcename)  -- technically should be get_sceneitem_size(sceneitemname)
    local instance_scene = obs.obs_get_scene_by_name(OBS_SCENE)
    local sceneitem = obs.obs_scene_find_source(instance_scene, sourcename)
    if not sceneitem then
        print("Source " .. sourcename .. " not found in scene " .. OBS_SCENE)
        obs.obs_scene_release(instance_scene)
        return 0, 0
    end
    
    local source = obs.obs_sceneitem_get_source(sceneitem)
    local width = obs.obs_source_get_width(source)
    local height = obs.obs_source_get_height(source)
    obs.obs_scene_release(instance_scene)
    return width, height
end

function resizeSource(sourcename, bbw, bbh, cropl, cropr, cropt, cropb)
    local instance_scene = obs.obs_get_scene_by_name(OBS_SCENE)
    local source = obs.obs_scene_find_source(instance_scene, sourcename)
    if not source then
        obs.obs_scene_release(instance_scene)
        return
    end
    
    local info = obs.obs_transform_info()
    local crop = obs.obs_sceneitem_crop()
    obs.obs_sceneitem_get_info(source, info)
    
    crop.left = cropl
    crop.right = cropr
    crop.top = cropt
    crop.bottom = cropb
    info.bounds.x = bbw
    info.bounds.y = bbh
    
    obs.obs_sceneitem_set_crop(source, crop)
    obs.obs_sceneitem_set_info(source, info)
    obs.obs_scene_release(instance_scene)
end
